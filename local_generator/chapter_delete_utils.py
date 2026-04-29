#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sqlite3
from pathlib import Path

from single_db_utils import (
    append_asset_history,
    append_character_history,
    ensure_schema,
    get_connection,
    merge_chapter_payload,
    normalize_timeline_text,
    upsert_asset,
    upsert_character,
    upsert_character_title_timeline,
)


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "novel_ledger.db"
CHAPTER_DIR = ROOT / "chapter"
LEDGER_HISTORY_DIR = ROOT / "ledger" / "history"
TEMP_DIR = ROOT / "temp"
HUMANIZER_DIR = ROOT / "temp" / "humanizer"
DELETE_BACKUP_DIR = ROOT / "local_generator" / "backups" / "delete_ops"


def chapter_prefix(chapter_no: int) -> str:
    return f"第{chapter_no:03d}章"


def extract_json_block(text: str) -> dict:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.S)
    if not match:
        raise ValueError("未找到 JSON 代码块")
    return json.loads(match.group(1))


def ledger_chapter_no(path: Path) -> int | None:
    match = re.search(r"update_chapter_(\d+)(?:_[0-9_]+)?\.md$", path.name)
    if not match:
        return None
    return int(match.group(1))


def chapter_file_map(chapter_no: int) -> dict[str, list[Path]]:
    prefix = chapter_prefix(chapter_no)
    return {
        "chapter_text": sorted(CHAPTER_DIR.glob(f"{prefix}*.md")),
        "ledger_history": sorted(LEDGER_HISTORY_DIR.glob(f"update_chapter_{chapter_no:03d}*.md")),
        "ledger_temp": sorted(TEMP_DIR.glob(f"update_chapter_{chapter_no:03d}*.md")),
        "humanizer_backup": sorted(HUMANIZER_DIR.glob(f"{prefix}*__before_humanizer_*.md")),
    }


def get_written_chapters(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute(
        """
        SELECT chapter_no
        FROM chapters_nav
        WHERE status = 'written'
        ORDER BY chapter_no
        """
    ).fetchall()
    return [int(row[0]) for row in rows]


def get_existing_history_ledgers() -> list[Path]:
    latest_by_chapter: dict[int, Path] = {}
    for path in LEDGER_HISTORY_DIR.glob("update_chapter_*.md"):
        chapter_no = ledger_chapter_no(path)
        if chapter_no is None:
            continue
        current = latest_by_chapter.get(chapter_no)
        if current is None or path.stat().st_mtime >= current.stat().st_mtime:
            latest_by_chapter[chapter_no] = path
    return sorted(latest_by_chapter.values(), key=lambda path: ledger_chapter_no(path) or 0)


def build_delete_plan(chapter_no: int, mode: str) -> dict:
    if mode not in {"last_only", "tail"}:
        raise ValueError("mode 仅支持 last_only 或 tail")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        written_chapters = get_written_chapters(conn)
        if not written_chapters:
            raise ValueError("当前没有已闭环章节可供删除。")

        latest_written = written_chapters[-1]
        if mode == "last_only" and chapter_no != latest_written:
            raise ValueError(
                f"last_only 模式只能删除当前最后一章。当前最后一章是第 {latest_written:03d} 章。"
            )

        affected_written = [item for item in written_chapters if item >= chapter_no]
        if not affected_written:
            raise ValueError(f"第 {chapter_no:03d} 章及之后没有已闭环章节。")

        if mode == "last_only":
            affected_written = [latest_written]

        kept_written = [item for item in written_chapters if item < affected_written[0]]
        ledger_files_all = get_existing_history_ledgers()
        ledger_chapters_all = [ledger_chapter_no(path) for path in ledger_files_all if ledger_chapter_no(path) is not None]
        kept_ledger_files = [
            path for path in ledger_files_all
            if (ledger_chapter_no(path) or 0) < affected_written[0]
        ]
        missing_kept_ledgers = sorted(set(kept_written) - set(ledger_chapters_all))

        affected_files = []
        affected_file_counts = {
            "chapter_text": 0,
            "ledger_history": 0,
            "ledger_temp": 0,
            "humanizer_backup": 0,
        }
        for current_chapter in affected_written:
            current_map = chapter_file_map(current_chapter)
            for kind, paths in current_map.items():
                affected_file_counts[kind] += len(paths)
                affected_files.extend(paths)

        char_rows = conn.execute(
            """
            SELECT character_name, COUNT(*) AS cnt
            FROM character_history_log
            WHERE chapter_no >= ?
            GROUP BY character_name
            ORDER BY character_name
            """,
            (affected_written[0],),
        ).fetchall()
        asset_rows = conn.execute(
            """
            SELECT asset_name, COUNT(*) AS cnt
            FROM asset_history_log
            WHERE chapter_no >= ?
            GROUP BY asset_name
            ORDER BY asset_name
            """,
            (affected_written[0],),
        ).fetchall()

        return {
            "mode": mode,
            "target_chapter": chapter_no,
            "effective_cutoff": affected_written[0],
            "latest_written": latest_written,
            "written_chapters": written_chapters,
            "affected_written": affected_written,
            "kept_written": kept_written,
            "kept_ledger_files": [str(path) for path in kept_ledger_files],
            "missing_kept_ledgers": missing_kept_ledgers,
            "affected_files": [str(path) for path in sorted(set(affected_files))],
            "affected_file_counts": affected_file_counts,
            "affected_character_history": [
                {"name": row["character_name"], "count": row["cnt"]} for row in char_rows
            ],
            "affected_asset_history": [
                {"name": row["asset_name"], "count": row["cnt"]} for row in asset_rows
            ],
        }
    finally:
        conn.close()


def format_plan_text(plan: dict) -> str:
    lines = [
        "=== 删除流程预检 ===",
        f"模式: {plan['mode']}",
        f"请求章节: 第{plan['target_chapter']:03d}章",
        f"实际截断点: 第{plan['effective_cutoff']:03d}章",
        f"当前最后已写章: 第{plan['latest_written']:03d}章",
        f"将删除已写章节: {', '.join(f'第{item:03d}章' for item in plan['affected_written'])}",
        f"保留已写章节: {', '.join(f'第{item:03d}章' for item in plan['kept_written']) or '无'}",
        "",
        "文件影响统计:",
    ]
    for key, value in plan["affected_file_counts"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            f"将删除文件总数: {len(plan['affected_files'])}",
            f"保留台账数: {len(plan['kept_ledger_files'])}",
        ]
    )

    if plan["missing_kept_ledgers"]:
        lines.append(
            "缺失保留台账: "
            + ", ".join(f"第{item:03d}章" for item in plan["missing_kept_ledgers"])
        )

    if plan["affected_character_history"]:
        lines.append("")
        lines.append("受影响角色历史:")
        for item in plan["affected_character_history"]:
            lines.append(f"- {item['name']}: {item['count']} 条")

    if plan["affected_asset_history"]:
        lines.append("")
        lines.append("受影响资产历史:")
        for item in plan["affected_asset_history"]:
            lines.append(f"- {item['name']}: {item['count']} 条")

    return "\n".join(lines)


def load_ledger_payload(ledger_path: Path) -> tuple[int, dict]:
    chapter_no = ledger_chapter_no(ledger_path)
    if chapter_no is None:
        raise ValueError(f"无法从文件名识别章节号: {ledger_path}")
    payload = extract_json_block(ledger_path.read_text(encoding="utf-8"))
    return chapter_no, payload


def _apply_character_updates(conn: sqlite3.Connection, updates: dict, chapter_no: int) -> None:
    if not updates:
        return
    for char_name, char_data in updates.items():
        upsert_character(conn, char_name, char_data, chapter_no=chapter_no)
        for history_item in char_data.get("history", []) or []:
            if isinstance(history_item, dict):
                append_character_history(
                    conn,
                    char_name,
                    chapter_no,
                    history_item.get("event") or history_item.get("summary") or "",
                    visibility=history_item.get("visibility", ""),
                    certainty=history_item.get("certainty", ""),
                )
            else:
                append_character_history(conn, char_name, chapter_no, str(history_item))


def _apply_character_title_updates(conn: sqlite3.Connection, updates: dict) -> None:
    if not updates:
        return
    for char_name, entries in updates.items():
        upsert_character_title_timeline(conn, char_name, entries or [])


def _apply_assets_updates(conn: sqlite3.Connection, updates: dict, chapter_no: int) -> None:
    if not updates:
        return
    for category, items in updates.items():
        for item_key, change_val in items.items():
            note = ""
            mode = "auto"
            stored_value = change_val
            if isinstance(change_val, dict):
                note = change_val.get("note", "")
                mode = change_val.get("mode", "auto")
                stored_value = change_val.get("value")

            current_row = conn.execute(
                """
                SELECT value_kind, current_value_num, current_value_text, current_value
                FROM wealth_and_assets
                WHERE asset_name = ?
                """,
                (item_key,),
            ).fetchone()

            is_numeric_change = isinstance(stored_value, (int, float))
            treat_as_delta = is_numeric_change and mode != "absolute"
            if treat_as_delta:
                current_num = 0.0
                if current_row:
                    if current_row["value_kind"] == "number" and current_row["current_value_num"] is not None:
                        current_num = float(current_row["current_value_num"])
                    else:
                        try:
                            current_num = float(current_row["current_value"])
                        except (TypeError, ValueError):
                            current_num = 0.0
                final_value = current_num + float(stored_value)
                if final_value.is_integer():
                    final_value = int(final_value)
                delta_note = f"delta={stored_value:+g}"
                note = f"{note} | {delta_note}".strip(" |") if note else delta_note
            else:
                final_value = stored_value

            upsert_asset(conn, category, item_key, final_value, chapter_no=chapter_no)
            append_asset_history(conn, category, item_key, final_value, chapter_no, change_note=note)


def apply_ledger_payload(conn: sqlite3.Connection, chapter_no: int, payload: dict) -> None:
    ensure_schema(conn)

    timeline = normalize_timeline_text(payload.get("timeline", ""))
    summary = payload.get("written_summary", "")
    next_hook = payload.get("next_hook", "")
    assets_change = payload.get("key_assets_change", "")
    character_updates = payload.get("character_updates", {})
    character_title_updates = payload.get("character_title_updates", {})
    assets_updates = payload.get("assets_updates", {})

    _apply_character_updates(conn, character_updates, chapter_no)
    _apply_character_title_updates(conn, character_title_updates)
    _apply_assets_updates(conn, assets_updates, chapter_no)

    existing = conn.execute(
        "SELECT * FROM chapters_nav WHERE chapter_no = ?",
        (chapter_no,),
    ).fetchone()

    incoming = {
        "chapter_no": chapter_no,
        "status": "written",
        "timeline_mark": timeline,
        "written_summary": summary,
        "next_hook": next_hook,
        "key_assets_change": assets_change,
    }
    merged = merge_chapter_payload(dict(existing) if existing else None, incoming)

    if existing:
        conn.execute(
            """
            UPDATE chapters_nav
            SET status = ?,
                timeline_mark = ?,
                written_summary = ?,
                next_hook = ?,
                key_assets_change = ?
            WHERE chapter_no = ?
            """,
            (
                merged.get("status", "written"),
                merged.get("timeline_mark", ""),
                merged.get("written_summary", ""),
                merged.get("next_hook", ""),
                merged.get("key_assets_change", ""),
                chapter_no,
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO chapters_nav (
                chapter_no, stage_goal, chapter_target, written_summary,
                next_hook, key_assets_change, status, timeline_mark
            ) VALUES (?, '', '', ?, ?, ?, ?, ?)
            """,
            (
                chapter_no,
                merged.get("written_summary", ""),
                merged.get("next_hook", ""),
                merged.get("key_assets_change", ""),
                merged.get("status", "written"),
                merged.get("timeline_mark", ""),
            ),
        )


def replay_ledgers(ledger_paths: list[Path]) -> None:
    if not ledger_paths:
        return
    conn = get_connection()
    try:
        ensure_schema(conn)
        for ledger_path in sorted(ledger_paths, key=lambda item: ledger_chapter_no(item) or 0):
            chapter_no, payload = load_ledger_payload(ledger_path)
            apply_ledger_payload(conn, chapter_no, payload)
        conn.commit()
    finally:
        conn.close()
