from __future__ import annotations

import os

import psycopg
from fastapi import HTTPException

DEFAULT_USER_INTERESTS_SQL = """
SELECT i.tag_id
FROM user_cs_interests_list u
JOIN interests i ON i.id = u.interests_list_id
WHERE u.entity_user_id = %s
"""


def fetch_user_tag_ids(user_id: int) -> list[int]:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise HTTPException(
            status_code=400,
            detail="Configura DATABASE_URL para buscar intereses del usuario",
        )

    query = os.getenv("USER_INTERESTS_SQL", DEFAULT_USER_INTERESTS_SQL)

    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (user_id,))
                rows = cur.fetchall()
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar intereses: {exc}",
        ) from exc

    return [int(row[0]) for row in rows]
