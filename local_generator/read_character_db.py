#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色设定读取脚本
用途：从统一数据库中提取指定角色的设定
"""

import argparse
import json
import sys
from pathlib import Path
from single_db_utils import (
    DB_PATH,
    ensure_schema,
    get_character_history_upto,
    get_connection,
    get_effective_character_title,
)

ROOT = Path(__file__).resolve().parent.parent


def extract_character_db(chapter_no: int) -> dict:
    if not DB_PATH.exists():
        print(f"❌ 找不到主数据库文件: {DB_PATH}", file=sys.stderr)
        return {}

    try:
        conn = get_connection()
        ensure_schema(conn)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(entities_registry)")
        columns = {row[1] for row in cur.fetchall()}

        select_fields = [
            "name",
            "entity_type",
            "importance_level",
            "static_core",
            "current_status",
        ]
        for optional in [
            "aliases_json",
            "role_type",
            "affiliation",
            "occupation",
            "personality",
            "appearance",
            "first_appearance",
            "status",
            "relationships_json",
        ]:
            if optional in columns:
                select_fields.append(optional)

        cur.execute(f"SELECT {', '.join(select_fields)} FROM entities_registry WHERE entity_type = '角色'")
        rows = [dict(row) for row in cur.fetchall()]

        db = {}
        for row in rows:
            name = row["name"]
            history_rows = get_character_history_upto(conn, name, max(chapter_no - 1, 0), limit=5) if chapter_no > 0 else []
            title_info = get_effective_character_title(conn, name, chapter_no) if chapter_no > 0 else {}
            history = [
                f"第{item['chapter_no']}章：{item['event_summary']}"
                for item in reversed(history_rows)
            ]
            db[name] = {
                "name": name,
                "aliases": json.loads(row.get("aliases_json") or "[]"),
                "role_type": row.get("role_type") or row.get("entity_type") or "",
                "affiliation": row.get("affiliation") or "",
                "occupation": row.get("occupation") or "",
                "personality": row.get("personality") or row.get("static_core") or "",
                "appearance": row.get("appearance") or "",
                "first_appearance": row.get("first_appearance") or "",
                "status": row.get("status") or row.get("current_status") or "",
                "relationships": json.loads(row.get("relationships_json") or "{}"),
                "history": history,
                "effective_title": title_info,
            }
        conn.close()
        return db
    except Exception as e:
        print(f"❌ 角色数据库读取失败: {e}", file=sys.stderr)
        return {}

def format_character_info(name: str, info: dict) -> str:
    title_info = info.get("effective_title") or {}
    forbidden_titles = title_info.get("forbidden_titles") or []
    aliases = [
        alias
        for alias in info.get("aliases", [])
        if alias and not any(forbidden in alias for forbidden in forbidden_titles)
    ]
    aliases = ", ".join(aliases)
    alias_str = f" ({aliases})" if aliases else ""
    
    output = []
    output.append(f"- **{name}**{alias_str} [{info.get('role_type', '')}] - {info.get('occupation', '')}")
    if title_info:
        output.append(f"  - **当前身份**: {title_info.get('identity_label', '')}")
        if title_info.get("narrative_label"):
            output.append(f"  - **旁白首选**: {title_info.get('narrative_label', '')}")
        if title_info.get("formal_title"):
            output.append(f"  - **正式称呼**: {title_info.get('formal_title', '')}")
        if title_info.get("common_title"):
            output.append(f"  - **常用称呼**: {title_info.get('common_title', '')}")
        if title_info.get("subordinate_title"):
            output.append(f"  - **下属称呼**: {title_info.get('subordinate_title', '')}")
        if forbidden_titles:
            output.append(f"  - **禁用称呼**: {', '.join(forbidden_titles)}")
        scene_rules = title_info.get("scene_rules") or {}
        if scene_rules:
            scene_text = " | ".join(f"{scene}: {rule}" for scene, rule in scene_rules.items())
            output.append(f"  - **场景规则**: {scene_text}")
    output.append(f"  - **性格**: {info.get('personality', '')}")
    output.append(f"  - **外貌**: {info.get('appearance', '')}")
    output.append(f"  - **状态**: {info.get('status', '')}")
    
    history = info.get("history", [])
    if history:
        # 取最近的3条历史记录
        recent_history = history[-3:] if len(history) > 3 else history
        output.append(f"  - **近期经历**: {' | '.join(recent_history)}")
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="读取角色数据库设定")
    parser.add_argument("--names", type=str, required=True, help="角色名列表，用逗号分隔，如 '朱高燧,老刘'")
    parser.add_argument("--chapter_no", type=int, help="当前章节号（用于将结果保存到文件方便预览）", default=0)
    args = parser.parse_args()

    names_to_query = [name.strip() for name in args.names.split(",") if name.strip()]
    if not names_to_query:
        print("未提供有效的角色名称。")
        return 0

    db = extract_character_db(args.chapter_no)
    if not db:
        return 1

    output_lines = []
    output_lines.append(f"=== 第 {args.chapter_no:03d} 章 角色设定对齐上下文 ({', '.join(names_to_query)}) ===\n")
    
    found_count = 0
    for query_name in names_to_query:
        # 精确匹配键名
        if query_name in db:
            output_lines.append(format_character_info(query_name, db[query_name]) + "\n")
            found_count += 1
            continue
            
        # 模糊匹配别名
        found_by_alias = False
        for key, info in db.items():
            aliases = info.get("aliases", [])
            if query_name in aliases:
                output_lines.append(format_character_info(key, info) + "\n")
                found_by_alias = True
                found_count += 1
                break
                
        if not found_by_alias:
            output_lines.append(f"- ⚠️ 数据库中未找到角色: **{query_name}**。如果是新角色，请在闭环时加入台账。\n")
            
    output_lines.append(f"=========================================\n共找到 {found_count} 个角色记录。")
    
    final_output = "\n".join(output_lines)
    print(final_output)

    # 如果传入了章节号，则将结果写入文件以便人类预览
    if args.chapter_no > 0:
        preview_dir = ROOT / "temp" / "workflow_preview"
        preview_dir.mkdir(parents=True, exist_ok=True)
        preview_file = preview_dir / f"character_context_第{args.chapter_no:03d}章.md"
        try:
            preview_file.write_text(final_output, encoding="utf-8")
            print(f"\n[系统提示] 角色上下文已保存至预览文件: {preview_file.name}")
        except Exception as e:
            print(f"\n[系统警告] 无法保存预览文件: {e}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
