"""Database exposure hardening (TDD §6.1). A new table without RLS or with grants fails here."""

import asyncpg
import pytest

pytestmark = pytest.mark.db

DATA_API_ROLES = ("anon", "authenticated")


async def app_tables(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    rows: list[asyncpg.Record] = await conn.fetch(
        """
        select c.oid, c.relname, c.relrowsecurity, c.relforcerowsecurity
        from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'app' and c.relkind in ('r', 'p')
        order by c.relname
        """
    )
    return rows


async def test_schema_app_has_tables(app_conn: asyncpg.Connection) -> None:
    names = {row["relname"] for row in await app_tables(app_conn)}
    assert {"alembic_version", "users"} <= names


async def test_nothing_of_ours_in_public(app_conn: asyncpg.Connection) -> None:
    owned = await app_conn.fetch(
        """
        select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public' and pg_get_userbyid(c.relowner) = current_user
        """
    )
    assert owned == []


async def test_every_app_table_forces_rls(app_conn: asyncpg.Connection) -> None:
    failures = [
        row["relname"]
        for row in await app_tables(app_conn)
        if not (row["relrowsecurity"] and row["relforcerowsecurity"])
    ]
    assert failures == [], f"tables without forced RLS: {failures}"


@pytest.mark.parametrize("role", DATA_API_ROLES)
async def test_data_api_roles_have_no_schema_access(
    app_conn: asyncpg.Connection, role: str
) -> None:
    for privilege in ("USAGE", "CREATE"):
        assert not await app_conn.fetchval(
            "select has_schema_privilege($1, 'app', $2)", role, privilege
        )


@pytest.mark.parametrize("role", DATA_API_ROLES)
async def test_data_api_roles_have_no_table_privileges(
    app_conn: asyncpg.Connection, role: str
) -> None:
    granted = [
        row["relname"]
        for row in await app_tables(app_conn)
        if await app_conn.fetchval(
            "select has_table_privilege($1, $2::oid, $3)",
            role,
            row["oid"],
            "SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER",
        )
    ]
    assert granted == [], f"{role} has privileges on: {granted}"


@pytest.mark.parametrize("role", DATA_API_ROLES)
async def test_data_api_roles_have_no_sequence_privileges(
    app_conn: asyncpg.Connection, role: str
) -> None:
    sequences = await app_conn.fetch(
        """
        select c.oid, c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'app' and c.relkind = 'S'
        """
    )
    granted = [
        row["relname"]
        for row in sequences
        if await app_conn.fetchval(
            "select has_sequence_privilege($1, $2::oid, 'USAGE,SELECT,UPDATE')", role, row["oid"]
        )
    ]
    assert granted == []


async def test_default_privileges_grant_nothing_to_others(app_conn: asyncpg.Connection) -> None:
    acls = await app_conn.fetch(
        "select defaclacl::text as acl from pg_default_acl"
        " where defaclnamespace = 'app'::regnamespace"
    )
    for row in acls:
        for entry in row["acl"].strip("{}").split(","):
            grantee = entry.split("=", 1)[0]
            assert grantee not in ("", "anon", "authenticated"), f"default privilege: {entry}"


async def test_policies_target_only_the_backend_role(app_conn: asyncpg.Connection) -> None:
    policies = await app_conn.fetch(
        "select tablename, policyname, roles::text[] as roles"
        " from pg_policies where schemaname = 'app'"
    )
    assert policies, "expected at least one policy"
    backend_role = await app_conn.fetchval("select current_user")
    wrong = [p["tablename"] for p in policies if list(p["roles"]) != [backend_role]]
    assert wrong == [], f"policies for other roles on: {wrong}"


async def test_every_table_has_a_backend_policy(app_conn: asyncpg.Connection) -> None:
    with_policy = {
        r["tablename"]
        for r in await app_conn.fetch("select tablename from pg_policies where schemaname = 'app'")
    }
    missing = [
        row["relname"] for row in await app_tables(app_conn) if row["relname"] not in with_policy
    ]
    assert missing == [], f"tables without a backend policy: {missing}"
