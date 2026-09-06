"""
OCR Pipeline for Student ID Card Scanning.
- Primary OCR: browser-side via tesseract.js (no system install needed)
- Fallback: server-side pytesseract (only if installed)
- This file is used for: sharpness scoring, field extraction, fuzzy matching
"""
import re
from difflib import SequenceMatcher

# Optional imports — only needed for server-side /scan/frames endpoint
try:
    import cv2
    import numpy as np
    from PIL import Image
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False


def sharpness_score(image_bytes: bytes) -> float:
    """Compute Laplacian variance as sharpness metric. Higher = sharper."""
    if not CV2_AVAILABLE:
        return 0.0
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return 0.0
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        return float(lap.var())
    except Exception:
        return 0.0


def pick_best_frame(frames: list) -> bytes:
    """Return the frame with the highest sharpness score."""
    if not frames:
        return b""
    scores = [(sharpness_score(f), f) for f in frames]
    scores.sort(key=lambda x: x[0], reverse=True)
    return scores[0][1]


def preprocess_image(image_bytes: bytes):
    """Convert to grayscale, denoise, adaptive threshold for better OCR."""
    if not CV2_AVAILABLE:
        return None
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Cannot decode image")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    scale = 2
    gray = cv2.resize(gray, (gray.shape[1] * scale, gray.shape[0] * scale), interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return thresh


def run_ocr(image_bytes: bytes) -> str:
    """Run pytesseract on image bytes, return full extracted text."""
    if not CV2_AVAILABLE or not PYTESSERACT_AVAILABLE:
        return ""  # OCR done in browser; this is only a fallback
    try:
        processed = preprocess_image(image_bytes)
        pil_img = Image.fromarray(processed)

        config = "--psm 6 --oem 3"
        text = pytesseract.image_to_string(pil_img, config=config)
        return text.strip()
    except Exception as e:
        return ""


def extract_fields(text: str) -> dict:
    """
    From raw OCR text extract roll_no, id_no, name.
    Uses label-based search for structured fields, heuristic for name.
    """
    result = {"roll_no": None, "id_no": None, "name": None}
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Roll No: look for "Roll No", "Roll Number", "Roll:" followed by value
    roll_pattern = re.compile(
        r'(?:Roll\s*(?:No|Number|\.)?[:\s]+)([A-Z0-9\-/]+)',
        re.IGNORECASE
    )
    roll_match = roll_pattern.search(text)
    if roll_match:
        result["roll_no"] = roll_match.group(1).strip()

    # ID No: look for "ID No", "ID Number", "Enrollment No", "Enroll No"
    id_pattern = re.compile(
        r'(?:(?:ID|Enrollment|Enroll)\s*(?:No|Number|\.)?[:\s]+)([A-Z0-9\-/]+)',
        re.IGNORECASE
    )
    id_match = id_pattern.search(text)
    if id_match:
        result["id_no"] = id_match.group(1).strip()

    # Name heuristic: find the most prominent capitalized line
    # Exclude: college name (usually first line), lines with digits only, known label lines
    skip_keywords = {"roll", "id", "no", "number", "year", "class", "div", "batch",
                     "enroll", "enrollment", "college", "institute", "university",
                     "department", "course", "branch", "sem", "semester"}
    name_candidates = []
    for i, line in enumerate(lines):
        # Skip very short lines or lines that are mostly numbers
        if len(line) < 3:
            continue
        if re.match(r'^[\d\s\-/:]+$', line):
            continue
        # Skip lines that start with a known label keyword
        lower = line.lower()
        if any(lower.startswith(kw) for kw in skip_keywords):
            continue
        # Skip lines that contain common label patterns
        if re.search(r'(roll|enroll|id no|year|class|div|batch)', lower):
            continue
        # Prefer title case or all-caps lines (likely a name)
        words = line.split()
        if all(w[0].isupper() for w in words if w):
            # Give higher score to lines that are 2-4 words (typical name)
            score = 2 if 2 <= len(words) <= 4 else 1
            # First line is likely college name — skip it
            if i == 0:
                score = 0
            name_candidates.append((score, len(line), line))

    if name_candidates:
        name_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        result["name"] = name_candidates[0][2]

    return result


def normalize_name(name: str) -> str:
    """Lowercase, collapse whitespace, remove punctuation for comparison."""
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def fuzzy_name_match(ocr_name: str, db_name: str, threshold: float = 0.70) -> bool:
    """Return True if normalized names match with ratio >= threshold."""
    n1 = normalize_name(ocr_name)
    n2 = normalize_name(db_name)
    if not n1 or not n2:
        return False
    ratio = SequenceMatcher(None, n1, n2).ratio()
    return ratio >= threshold


def normalize_id(val: str) -> str:
    """Normalize ID/roll number: uppercase, remove spaces, dashes for comparison."""
    if not val:
        return ""
    return re.sub(r'[\s\-/]', '', val).upper()


def match_student(fields: dict, roster: list) -> tuple:
    """
    Match OCR fields against student roster.
    Priority: roll_no → id_no → name
    Returns (matched_student_dict, matched_on_field) or (None, None)
    """
    ocr_roll = normalize_id(fields.get("roll_no") or "")
    ocr_id = normalize_id(fields.get("id_no") or "")
    ocr_name = fields.get("name") or ""

    # 1. Roll No match (primary signal)
    if ocr_roll:
        for student in roster:
            db_roll = normalize_id(student.get("roll_no") or "")
            if db_roll and ocr_roll == db_roll:
                return student, "roll_no"

    # 2. ID No match (primary signal)
    if ocr_id:
        for student in roster:
            db_id = normalize_id(student.get("id_no") or "")
            if db_id and ocr_id == db_id:
                return student, "id_no"

    # 3. Name fuzzy match (fallback)
    if ocr_name:
        for student in roster:
            db_name = student.get("name") or ""
            if fuzzy_name_match(ocr_name, db_name):
                return student, "name"

    return None, None
