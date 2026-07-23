-- SchoolHQ initial schema + Row-Level Security policies
--
-- This file is the enforcement half of multi-tenancy. The application
-- (app/middleware/tenant.py) sets three session variables per request:
--   app.current_school_id, app.current_role, app.current_user_id
-- Every policy below reads those variables to decide what a query can
-- see or write. If application code has a bug, Postgres still refuses
-- to leak another school's rows -- that's the whole point.
--
-- Run this against a fresh database before starting the app:
--   psql "$DATABASE_URL" -f init.sql

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- for gen_random_uuid()

-- =========================================================================
-- CORE TABLES
-- =========================================================================

CREATE TABLE schools (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(200) NOT NULL,
    county        VARCHAR(100),
    curriculum    VARCHAR(20) NOT NULL DEFAULT 'CBC',
    settings      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE classrooms (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id     UUID NOT NULL REFERENCES schools(id),
    name          VARCHAR(100) NOT NULL,
    grade_level   VARCHAR(50)
);

CREATE TABLE users (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id         UUID REFERENCES schools(id),  -- nullable: super_admin has no single school
    full_name         VARCHAR(150) NOT NULL,
    email             VARCHAR(150) NOT NULL UNIQUE,
    hashed_password   VARCHAR(255) NOT NULL,
    role              VARCHAR(30) NOT NULL,  -- super_admin | director | bursar | teacher | admin_staff
    is_active         BOOLEAN NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE teacher_classroom_assignments (
    user_id       UUID NOT NULL REFERENCES users(id),
    classroom_id  UUID NOT NULL REFERENCES classrooms(id),
    PRIMARY KEY (user_id, classroom_id)
);

CREATE TABLE students (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id         UUID NOT NULL REFERENCES schools(id),
    classroom_id      UUID REFERENCES classrooms(id),
    full_name         VARCHAR(150) NOT NULL,
    admission_number  VARCHAR(50) NOT NULL,
    is_active         BOOLEAN NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE guardians (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id           UUID NOT NULL REFERENCES schools(id),
    full_name           VARCHAR(150) NOT NULL,
    phone_number        VARCHAR(20) NOT NULL,  -- E.164, e.g. +2547...
    relationship_label  VARCHAR(50)
);

CREATE TABLE student_guardians (
    student_id          UUID NOT NULL REFERENCES students(id),
    guardian_id         UUID NOT NULL REFERENCES guardians(id),
    is_primary_contact  BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (student_id, guardian_id)
);

-- =========================================================================
-- FINANCE MODULE
-- =========================================================================

CREATE TABLE fee_structures (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id     UUID NOT NULL REFERENCES schools(id),
    grade_level   VARCHAR(50),
    category      VARCHAR(30) NOT NULL,  -- tuition | uniform | feeding_programme | transport | other
    term          VARCHAR(20) NOT NULL,
    amount        NUMERIC(12,2) NOT NULL
);

CREATE TABLE invoices (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id     UUID NOT NULL REFERENCES schools(id),
    student_id    UUID NOT NULL REFERENCES students(id),
    category      VARCHAR(30) NOT NULL,
    term          VARCHAR(20) NOT NULL,
    amount_due    NUMERIC(12,2) NOT NULL,
    amount_paid   NUMERIC(12,2) NOT NULL DEFAULT 0,
    status        VARCHAR(20) NOT NULL DEFAULT 'unpaid',  -- unpaid | partially_paid | paid | overdue
    due_date      DATE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE transactions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id             UUID NOT NULL REFERENCES schools(id),
    mpesa_receipt_number  VARCHAR(50) NOT NULL UNIQUE,
    phone_number          VARCHAR(20) NOT NULL,
    amount                NUMERIC(12,2) NOT NULL,
    paid_at               TIMESTAMPTZ NOT NULL,
    raw_payload           JSONB,
    matched               BOOLEAN NOT NULL DEFAULT false,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE payment_matches (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id        UUID NOT NULL REFERENCES schools(id),
    transaction_id   UUID NOT NULL REFERENCES transactions(id),
    invoice_id       UUID NOT NULL REFERENCES invoices(id),
    amount_applied   NUMERIC(12,2) NOT NULL,
    matched_by       VARCHAR(20) NOT NULL DEFAULT 'auto',  -- auto | manual
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================================
-- ACADEMICS MODULE
-- =========================================================================

CREATE TABLE learning_areas (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id     UUID NOT NULL REFERENCES schools(id),
    name          VARCHAR(100) NOT NULL
);

CREATE TABLE rubric_entries (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id          UUID NOT NULL REFERENCES schools(id),
    student_id         UUID NOT NULL REFERENCES students(id),
    learning_area_id   UUID NOT NULL REFERENCES learning_areas(id),
    term               VARCHAR(20) NOT NULL,
    strand             VARCHAR(150),
    level              VARCHAR(30) NOT NULL,  -- exceeding_expectation | meeting_expectation | ...
    recorded_by        UUID NOT NULL REFERENCES users(id),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE report_cards (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       UUID NOT NULL REFERENCES schools(id),
    student_id      UUID NOT NULL REFERENCES students(id),
    term            VARCHAR(20) NOT NULL,
    compiled_data   JSONB NOT NULL,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================================
-- COMMS MODULE
-- =========================================================================

CREATE TABLE message_templates (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id     UUID NOT NULL REFERENCES schools(id),
    name          VARCHAR(100) NOT NULL,
    body          TEXT NOT NULL
);

CREATE TABLE message_log (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id        UUID NOT NULL REFERENCES schools(id),
    guardian_id      UUID NOT NULL REFERENCES guardians(id),
    body             TEXT NOT NULL,
    trigger_reason   VARCHAR(100),
    status           VARCHAR(20) NOT NULL DEFAULT 'queued',  -- queued | sent | delivered | failed
    sent_at          TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================================
-- ROW-LEVEL SECURITY
-- =========================================================================
-- Pattern: every tenant-scoped table gets RLS enabled, plus a policy that
-- requires school_id to match the session's app.current_school_id. The
-- super_admin role bypasses this (see the OR clause) for cross-school
-- platform operations -- keep that role tightly held, it's the master key.

DO $$
DECLARE
    t text;
BEGIN
    FOR t IN
        SELECT unnest(ARRAY[
            'classrooms', 'students', 'guardians',
            'fee_structures', 'invoices', 'transactions', 'payment_matches',
            'learning_areas', 'rubric_entries', 'report_cards',
            'message_templates', 'message_log'
        ])
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', t);
        EXECUTE format(
            'CREATE POLICY tenant_isolation_%1$s ON %1$s
                USING (
                    current_setting(''app.current_role'', true) = ''super_admin''
                    OR school_id = NULLIF(current_setting(''app.current_school_id'', true), '''')::uuid
                )
                WITH CHECK (
                    current_setting(''app.current_role'', true) = ''super_admin''
                    OR school_id = NULLIF(current_setting(''app.current_school_id'', true), '''')::uuid
                );',
            t
        );
    END LOOP;
END $$;

-- users and schools need their own policies since they don't fit the
-- generic loop above (schools has no school_id column on itself; users
-- can have a null school_id for super_admin accounts).

ALTER TABLE schools ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_schools ON schools
    USING (
        current_setting('app.current_role', true) = 'super_admin'
        OR id = NULLIF(current_setting('app.current_school_id', true), '')::uuid
    );

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_users ON users
    USING (
        current_setting('app.current_role', true) = 'super_admin'
        OR school_id = NULLIF(current_setting('app.current_school_id', true), '')::uuid
    );

-- =========================================================================
-- EXTRA SCOPING: teachers only see rubric_entries for THEIR classes
-- =========================================================================
-- This is defense-in-depth on top of the app-layer query filtering you'll
-- also want in routes/academics.py -- don't rely on only one layer.

-- IMPORTANT: this is created AS RESTRICTIVE, not the default permissive.
-- Postgres combines multiple PERMISSIVE policies with OR, which would let
-- satisfying either school-scope OR class-scope be enough -- not what we
-- want. A RESTRICTIVE policy is AND-ed against the permissive result, so
-- a teacher must satisfy BOTH tenant_isolation_rubric_entries (school
-- match) AND this class-scope check to see a row.
CREATE POLICY teacher_class_scope_rubric_entries ON rubric_entries
    AS RESTRICTIVE
    USING (
        current_setting('app.current_role', true) != 'teacher'
        OR student_id IN (
            SELECT s.id FROM students s
            JOIN teacher_classroom_assignments tca ON tca.classroom_id = s.classroom_id
            WHERE tca.user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
    );

-- Verify this actually behaves as intended before relying on it: log in
-- as a teacher assigned to only one class and confirm rubric_entries for
-- other classes in the SAME school are invisible, not just other schools'
-- data. That's the specific case this RESTRICTIVE policy exists for.
