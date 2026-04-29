#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sqlite3
from pathlib import Path

from single_db_utils import (
    DB_PATH,
    ROOT,
    chapter_payload_has_content,
    ensure_schema,
    get_connection,
    merge_chapter_payload,
    upsert_asset,
    upsert_character,
)


LOCAL_DB_PATH = ROOT / "local_generator" / "novel_ledger.db"
CHARACTER_JSON_PATH = ROOT / "local_generator" / "character_db.json"
ASSETS_JSON_PATH = ROOT / "local_generator" / "assets_db.json"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def merge_written_chapters(root_conn: sqlite3.Connection) -> int:
    if not LOCAL_DB_PATH.exists():
        return 0

    local_conn = sqlite3.connect(LOCAL_DB_PATH)
    local_conn.row_factory = sqlite3.Row
    root_conn.row_factory = sqlite3.Row
    local_cur = local_conn.cursor()
    root_cur = root_conn.cursor()

    local_columns = {row[1] for row in local_cur.execute("PRAGMA table_info(chapters_nav)").fetchall()}
    select_fields = [
        "chapter_no",
        "history_date_label",
        "written_summary",
        "next_hook",
        "key_assets_change",
        "status",
    ]
    if "timeline_mark" in local_columns:
        select_fields.append("timeline_mark")

    merged_count = 0
    for local_row in local_cur.execute(
        f"SELECT {', '.join(select_fields)} FROM chapters_nav WHERE status = 'written' ORDER BY chapter_no"
    ).fetchall():
        incoming = dict(local_row)
        timeline = incoming.get("timeline_mark") or incoming.get("history_date_label") or ""
        incoming["timeline_mark"] = timeline

        root_cur.execute("SELECT * FROM chapters_nav WHERE chapter_no = ?", (incoming["chapter_no"],))
        existing = root_cur.fetchone()
        merged = merge_chapter_payload(dict(existing) if existing else None, incoming)
        if not chapter_payload_has_content(merged):
            continue

        if existing:
            root_cur.execute(
                """
                UPDATE chapters_nav
                SET timeline_mark = ?, written_summary = ?, next_hook = ?,
                    key_assets_change = ?, status = ?
                WHERE chapter_no = ?
                """,
                (
                    merged.get("timeline_mark", ""),
                    merged.get("written_summary", ""),
                    merged.get("next_hook", ""),
                    merged.get("key_assets_change", ""),
                    merged.get("status", ""),
                    incoming["chapter_no"],
                ),
            )
        else:
            root_cur.execute(
                """
                INSERT INTO chapters_nav (
                    chapter_no, stage_goal, chapter_target, written_summary,
                    next_hook, key_assets_change, status, timeline_mark
                ) VALUES (?, '', '', ?, ?, ?, ?, ?)
                """,
                (
                    incoming["chapter_no"],
                    merged.get("written_summary", ""),
                    merged.get("next_hook", ""),
                    merged.get("key_assets_change", ""),
                    merged.get("status", ""),
                    merged.get("timeline_mark", ""),
                ),
            )
        merged_count += 1

    root_conn.commit()
    local_conn.close()
    return merged_count


def migrate_characters(root_conn: sqlite3.Connection) -> int:
    data = load_json(CHARACTER_JSON_PATH, {})
    for name, char_data in data.items():
        upsert_character(root_conn, name, char_data)
    root_conn.commit()
    return len(data)


def migrate_assets(root_conn: sqlite3.Connection) -> int:
    data = load_json(ASSETS_JSON_PATH, {})
    count = 0
    for asset_group, items in data.items():
        for asset_name, value in items.items():
            upsert_asset(root_conn, asset_group, asset_name, value)
            count += 1
    root_conn.commit()
    return count


def normalize_timeline_fields(root_conn: sqlite3.Connection) -> int:
    cur = root_conn.cursor()
    rows = cur.execute(
        """
        SELECT chapter_no, history_date_label, timeline_mark
        FROM chapters_nav
        WHERE COALESCE(history_date_label, '') != '' OR COALESCE(timeline_mark, '') != ''
        """
    ).fetchall()
    updated = 0
    for chapter_no, history_date_label, timeline_mark in rows:
        value = timeline_mark or history_date_label or ""
        if value and value != (timeline_mark or ""):
            cur.execute(
                "UPDATE chapters_nav SET timeline_mark = ? WHERE chapter_no = ?",
                (value, chapter_no),
            )
            updated += 1
    root_conn.commit()
    return updated


def main() -> int:
    conn = get_connection()
    ensure_schema(conn)

    merged_chapters = merge_written_chapters(conn)
    migrated_characters = migrate_characters(conn)
    migrated_assets = migrate_assets(conn)
    normalized_timelines = normalize_timeline_fields(conn)
    conn.close()

    print(f"✅ 章节并库完成：{merged_chapters} 条")
    print(f"✅ 角色并库完成：{migrated_characters} 个")
    print(f"✅ 资产并库完成：{migrated_assets} 项")
    print(f"✅ 时间字段归一完成：{normalized_timelines} 条")
    print(f"📍 当前唯一主库：{DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
