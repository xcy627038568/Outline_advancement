#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V4 版本章节极简闭环脚本
用途：读取极简 JSON 台账，并将章节、角色、资产统一写入单一数据库。
"""

import sys
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
import argparse

from single_db_utils import (
    append_asset_history,
    append_character_history,
    DB_PATH,
    ensure_schema,
    get_connection,
    merge_chapter_payload,
    normalize_timeline_text,
    upsert_asset,
    upsert_character,
    upsert_character_title_timeline,
)

ROOT = Path(__file__).resolve().parent.parent

def extract_json_block(text: str) -> dict:
    match = re.search(r'```json\n(.*?)\n```', text, re.S)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception as e:
            raise ValueError(f"JSON 解析失败: {e}")
    raise ValueError("未找到 JSON 代码块")

def update_character_db(updates: dict, chapter_no: int):
    if not updates:
        return
    
    print("开始同步角色数据库更新...")
    conn = get_connection()
    ensure_schema(conn)
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
        print(f"  - 同步角色: {char_name}")
    conn.commit()
    conn.close()
    print(f"角色数据库同步完成。(共变动 {len(updates)} 个角色)")


def update_character_title_db(updates: dict):
    if not updates:
        return

    print("开始同步角色动态称谓...")
    conn = get_connection()
    ensure_schema(conn)
    changed = 0
    for char_name, entries in updates.items():
        changed += upsert_character_title_timeline(conn, char_name, entries or [])
        print(f"  - 同步动态称谓: {char_name}")
    conn.commit()
    conn.close()
    print(f"角色动态称谓同步完成。(共写入 {changed} 条)")


def update_assets_db(updates: dict, chapter_no: int):
    if not updates:
        return

    print("开始同步资产数据库更新...")
    conn = get_connection()
    ensure_schema(conn)
    updated_items = 0
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
                    value_kind = current_row["value_kind"] if "value_kind" in current_row.keys() else ""
                    if value_kind == "number" and current_row["current_value_num"] is not None:
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
            print(f"  - 资产同步 [{category}]: {item_key} = {final_value}")
            updated_items += 1
    conn.commit()
    conn.close()
    print(f"资产数据库同步完成。(共变动 {updated_items} 项)")


def backup_databases():
    backup_dir = ROOT / "local_generator" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_backup = backup_dir / f"novel_ledger_before_{timestamp}.db"
    shutil.copy2(DB_PATH, db_backup)
    print(f"主数据库快照已备份: {db_backup.name}")

def main():
    parser = argparse.ArgumentParser(description="V4 章节闭环洗地脚本")
    parser.add_argument("chapter_no", type=int, help="章节号")
    args = parser.parse_args()

    print(f"=== 开始执行第 {args.chapter_no:03d} 章闭环流程 ===")

    ledger_file = ROOT / "temp" / f"update_chapter_{args.chapter_no:03d}.md"
    if not ledger_file.exists():
        print(f"找不到台账文件: {ledger_file}", file=sys.stderr)
        return 1

    try:
        content = ledger_file.read_text(encoding="utf-8")
        chapter_data = extract_json_block(content)

        timeline = normalize_timeline_text(chapter_data.get("timeline", ""))
        summary = chapter_data.get("written_summary", "")
        next_hook = chapter_data.get("next_hook", "")
        assets_change = chapter_data.get("key_assets_change", "")
        character_updates = chapter_data.get("character_updates", {})
        character_title_updates = chapter_data.get("character_title_updates", {})
        assets_updates = chapter_data.get("assets_updates", {})

        # 在修改任何数据前，先备份
        backup_databases()

        # 执行角色同步
        if character_updates:
            update_character_db(character_updates, chapter_no=args.chapter_no)
        if character_title_updates:
            update_character_title_db(character_title_updates)

        # 执行资产同步
        if assets_updates:
            update_assets_db(assets_updates, chapter_no=args.chapter_no)

        conn = get_connection()
        ensure_schema(conn)
        cur = conn.cursor()

        cur.execute("SELECT * FROM chapters_nav WHERE chapter_no = ?", (args.chapter_no,))
        existing = cur.fetchone()

        incoming = {
            "chapter_no": args.chapter_no,
            "status": "written",
            "timeline_mark": timeline,
            "written_summary": summary,
            "next_hook": next_hook,
            "key_assets_change": assets_change,
        }
        merged = merge_chapter_payload(dict(existing) if existing else None, incoming)

        if existing:
            cur.execute(
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
                    args.chapter_no,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO chapters_nav (
                    chapter_no, stage_goal, chapter_target, written_summary,
                    next_hook, key_assets_change, status, timeline_mark
                ) VALUES (?, '', '', ?, ?, ?, ?, ?)
                """,
                (
                    args.chapter_no,
                    merged.get("written_summary", ""),
                    merged.get("next_hook", ""),
                    merged.get("key_assets_change", ""),
                    merged.get("status", "written"),
                    merged.get("timeline_mark", ""),
                ),
            )

        conn.commit()
        conn.close()

        # 归档临时台账
        history_dir = ROOT / "ledger" / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        archive_file = history_dir / ledger_file.name
        if archive_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_file = history_dir / f"{ledger_file.stem}_{timestamp}{ledger_file.suffix}"
        ledger_file.rename(archive_file)
        print(f"台账已归档至: {archive_file}")

        print("章节极简闭环完成。")
        return 0

    except Exception as e:
        print(f"闭环失败: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
