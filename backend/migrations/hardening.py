"""Database exposure hardening used by every migration (TDD §6.1, layers 2 and 3).

Every table in schema `app` must call `secure_table()` in the migration that creates it.
`test_db_hardening.py` fails CI for any table that doesn't.
"""

from alembic import op


def secure_table(table: str) -> None:
    """Force RLS with a single allow-all policy for the backend role (the table owner)."""
    op.execute(f"ALTER TABLE app.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE app.{table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY backend_all ON app.{table} AS PERMISSIVE FOR ALL "
        "TO CURRENT_USER USING (true) WITH CHECK (true)"
    )


REASSERT_REVOKES = """
DO $$
DECLARE r text;
BEGIN
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('REVOKE ALL ON SCHEMA app FROM %I', r);
      EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA app FROM %I', r);
      EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA app FROM %I', r);
      EXECUTE format('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA app FROM %I', r);
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA app REVOKE ALL ON TABLES FROM %I', r);
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA app REVOKE ALL ON SEQUENCES FROM %I', r);
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA app REVOKE ALL ON FUNCTIONS FROM %I', r);
    END IF;
  END LOOP;
  REVOKE ALL ON SCHEMA app FROM PUBLIC;
  REVOKE ALL ON ALL TABLES IN SCHEMA app FROM PUBLIC;
  REVOKE ALL ON ALL SEQUENCES IN SCHEMA app FROM PUBLIC;
  REVOKE ALL ON ALL FUNCTIONS IN SCHEMA app FROM PUBLIC;
  ALTER DEFAULT PRIVILEGES IN SCHEMA app REVOKE ALL ON TABLES FROM PUBLIC;
  ALTER DEFAULT PRIVILEGES IN SCHEMA app REVOKE ALL ON SEQUENCES FROM PUBLIC;
  ALTER DEFAULT PRIVILEGES IN SCHEMA app REVOKE ALL ON FUNCTIONS FROM PUBLIC;
END $$;
"""
