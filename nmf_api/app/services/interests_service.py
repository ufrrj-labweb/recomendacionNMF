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

DEFAULT_CLASS_INTERESTS_SQL = """
SELECT interest_id
FROM class_interest
WHERE class_id = %s
"""

DEFAULT_USERS_BY_INTERESTS_SQL = """
SELECT DISTINCT entity_user_id
FROM user_cs_interests_list
WHERE interests_list_id = ANY(%s)
"""

DEFAULT_CLASS_BRIEF_SQL = """
SELECT titulo, descricao
FROM extension_class
WHERE id = %s
"""

DEFAULT_DEDUPE_INSERT_SQL = """
INSERT INTO notifications_sent (class_id, user_id)
SELECT %s, unnest(%s::int[])
ON CONFLICT (class_id, user_id) DO NOTHING
RETURNING user_id
"""

DEFAULT_CLASS_INTERESTS_INSERT_SQL = """
INSERT INTO class_interest (class_id, interest_id)
SELECT %s, unnest(%s::int[])
ON CONFLICT DO NOTHING
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


def fetch_interest_ids_by_class_id(class_id: int) -> list[int]:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise HTTPException(
            status_code=400,
            detail="Configura DATABASE_URL para buscar intereses de la oferta",
        )

    query = os.getenv("CLASS_INTERESTS_SQL", DEFAULT_CLASS_INTERESTS_SQL)

    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (class_id,))
                rows = cur.fetchall()
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar intereses de la oferta: {exc}",
        ) from exc

    return [int(row[0]) for row in rows]


def fetch_user_ids_by_interest_ids(interest_ids: list[int]) -> list[int]:
    if not interest_ids:
        return []

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise HTTPException(
            status_code=400,
            detail="Configura DATABASE_URL para buscar usuarios por intereses",
        )

    query = os.getenv("USERS_BY_INTERESTS_SQL", DEFAULT_USERS_BY_INTERESTS_SQL)

    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (interest_ids,))
                rows = cur.fetchall()
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar usuarios por intereses: {exc}",
        ) from exc

    return [int(row[0]) for row in rows]


def fetch_class_brief(class_id: int) -> tuple[str | None, str | None]:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise HTTPException(
            status_code=400,
            detail="Configura DATABASE_URL para buscar oferta",
        )

    query = os.getenv("CLASS_BRIEF_SQL", DEFAULT_CLASS_BRIEF_SQL)

    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (class_id,))
                row = cur.fetchone()
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar oferta: {exc}",
        ) from exc

    if not row:
        return None, None

    title = row[0] if row[0] else None
    description = row[1] if row[1] else None
    return title, description


def filter_new_user_ids(class_id: int, user_ids: list[int]) -> list[int]:
    if not user_ids:
        return []

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise HTTPException(
            status_code=400,
            detail="Configura DATABASE_URL para dedupe de notificaciones",
        )

    query = os.getenv("NOTIFICATIONS_DEDUPE_SQL", DEFAULT_DEDUPE_INSERT_SQL)

    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (class_id, user_ids))
                rows = cur.fetchall()
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al deduplicar notificaciones: {exc}",
        ) from exc

    return [int(row[0]) for row in rows]


def insert_class_interests(class_id: int, interest_ids: list[int]) -> None:
    if not interest_ids:
        return

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise HTTPException(
            status_code=400,
            detail="Configura DATABASE_URL para guardar intereses de la oferta",
        )

    query = os.getenv("CLASS_INTERESTS_INSERT_SQL", DEFAULT_CLASS_INTERESTS_INSERT_SQL)

    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (class_id, interest_ids))
            conn.commit()
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar intereses de la oferta: {exc}",
        ) from exc
