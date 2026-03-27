"""Database helpers — connection and upsert query builder."""

import psycopg
from config import DATABASE_URL


def get_connection() -> psycopg.Connection:
    """Return a new psycopg connection to the Poliscope database."""
    return psycopg.connect(DATABASE_URL)


def upsert_query(
    table: str,
    columns: list[str],
    conflict_column: str,
    has_updated_at: bool = False,
) -> str:
    """
    Generate an INSERT ... ON CONFLICT DO UPDATE query.

    Parameters
    ----------
    table : str
        Target table name.
    columns : list[str]
        Column names to insert (must NOT include 'id').
    conflict_column : str
        Column used for ON CONFLICT (e.g. 'official_id').
    has_updated_at : bool
        If True, adds `updated_at = NOW()` to the UPDATE SET clause.

    Returns
    -------
    str
        Parameterized SQL query using %(col)s placeholders.
    """
    placeholders = ", ".join(f"%({c})s" for c in columns)
    col_list = ", ".join(columns)

    # Columns to update on conflict (exclude the conflict column itself)
    update_cols = [c for c in columns if c != conflict_column]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)

    if has_updated_at:
        set_clause += ", updated_at = NOW()"

    return (
        f"INSERT INTO {table} ({col_list}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT ({conflict_column}) DO UPDATE SET {set_clause}"
    )
