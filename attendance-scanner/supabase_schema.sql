-- ============================================================
-- AttendScan - Supabase Database Schema
-- Run this ONCE in your Supabase project SQL editor
-- Dashboard -> SQL Editor -> New Query -> Paste -> Run
-- ============================================================

-- Teachers table
create table if not exists teachers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text unique not null,
  password_hash text not null,
  college_name text,
  created_at timestamptz default now()
);

-- Students table
create table if not exists students (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid references teachers(id) on delete cascade,
  name text not null,
  roll_no text not null,
  id_no text,
  year text not null,  -- '1st', '2nd', '3rd'
  photo_url text,
  card_reference_text text,  -- raw OCR text for debugging
  created_at timestamptz default now()
);

-- Timetable table
create table if not exists timetable (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid references teachers(id) on delete cascade,
  year text not null,
  course text not null,
  day_of_week text not null,  -- 'Monday', 'Tuesday', etc.
  start_time time not null,
  end_time time not null
);

-- Attendance sessions table
create table if not exists attendance_sessions (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid references teachers(id) on delete cascade,
  year text not null,
  course text not null,
  session_date date not null,
  start_time timestamptz default now(),
  end_time timestamptz,
  total_students int default 0,
  present_count int default 0
);

-- Attendance records table
create table if not exists attendance_records (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references attendance_sessions(id) on delete cascade,
  student_id uuid references students(id),
  roll_no text not null,
  status text not null,    -- 'present' | 'absent' | 'present_manual'
  matched_on text,         -- 'roll_no' | 'id_no' | 'name' | 'manual'
  scanned_at timestamptz
);

-- ============================================================
-- Row Level Security (RLS) Policies
-- ============================================================
-- NOTE: The backend uses service_role key which bypasses RLS.
-- These policies are here if you ever want to add frontend Supabase access.

-- Enable RLS on all tables
alter table teachers enable row level security;
alter table students enable row level security;
alter table timetable enable row level security;
alter table attendance_sessions enable row level security;
alter table attendance_records enable row level security;

-- For service_role (backend): all access is allowed automatically
-- For anon/authenticated frontend use, add policies here if needed

-- ============================================================
-- Indexes for performance
-- ============================================================
create index if not exists idx_students_teacher_year on students(teacher_id, year);
create index if not exists idx_timetable_teacher_day on timetable(teacher_id, day_of_week);
create index if not exists idx_sessions_teacher on attendance_sessions(teacher_id, session_date desc);
create index if not exists idx_records_session on attendance_records(session_id);

-- Done! Your database is ready for AttendScan.
