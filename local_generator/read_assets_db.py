#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产与资源读取脚本
用途：从统一数据库中提取大燕商行的当前资产负债情况
"""

import argparse
import sys
from pathlib import Path
from single_db_utils import DB_PATH, ensure_schema, get_connection, get_latest_asset_snapshot_upto

ROOT = Path(__file__).resolve().parent.parent

def get_assets_db(chapter_no: int) -> dict:
    if not DB_PATH.exists():
        print(f"❌ 找不到主数据库文件: {DB_PATH}", file=sys.stderr)
        return {}
    try:
        conn = get_connection()
        ensure_schema(conn)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(wealth_and_assets)")
        columns = {row[1] for row in cur.fetchall()}
        if "asset_group" not in columns:
            conn.close()
            return {}

        cur.execute(
            """
            SELECT asset_group, asset_name, value_kind, current_value_num, current_value_text, current_value
            FROM wealth_and_assets
            WHERE asset_group IS NOT NULL AND asset_group != ''
            ORDER BY asset_group, asset_name
            """
        )
        base_rows = [dict(row) for row in cur.fetchall()]
        row_map = {row["asset_name"]: row for row in base_rows}

        if chapter_no > 0:
            snapshot_map = get_latest_asset_snapshot_upto(conn, chapter_no - 1)
            for asset_name, snapshot_row in snapshot_map.items():
                row_map[asset_name] = {
                    **row_map.get(asset_name, {}),
                    **snapshot_row,
                }

        rows = list(row_map.values())
        conn.close()

        db = {}
        for row in rows:
            group = row["asset_group"]
            db.setdefault(group, {})
            value_num = row.get("value_num", row.get("current_value_num"))
            value_text = row.get("value_text", row.get("current_value_text"))
            value_kind = row.get("value_kind")
            current_value = row.get("current_value", "")
            if value_kind == "number" and value_num is not None:
                value = int(value_num) if float(value_num).is_integer() else value_num
            else:
                value = value_text or current_value
            db[group][row["asset_name"]] = value
        return db
    except Exception as e:
        print(f"❌ 资产数据库读取失败: {e}", file=sys.stderr)
        return {}

def format_assets_info(db: dict) -> str:
    output = []
    
    # 资金
    funds = db.get("funds", {})
    if funds:
        output.append("【当前资金】")
        for k, v in funds.items():
            output.append(f"  - {k}: {v}")
            
    # 原材料
    raw = db.get("raw_materials", {})
    if raw:
        output.append("【原材料储备】")
        for k, v in raw.items():
            output.append(f"  - {k}: {v}")
            
    # 成品
    products = db.get("products", {})
    if products:
        output.append("【成品库存】")
        for k, v in products.items():
            output.append(f"  - {k}: {v}")
            
    # 人员
    personnel = db.get("personnel", {})
    if personnel:
        output.append("【人力资源】")
        for k, v in personnel.items():
            output.append(f"  - {k}: {v}")
            
    # 关键契约与物品
    key_items = db.get("key_items", {})
    if key_items:
        output.append("【核心契约与特殊资产】")
        for k, v in key_items.items():
            output.append(f"  - {k}: {v}")

    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="读取资产数据库")
    parser.add_argument("--chapter_no", type=int, help="当前章节号（用于将结果保存到文件方便预览）", default=0)
    args = parser.parse_args()

    db = get_assets_db(args.chapter_no)
    if not db:
        return 1

    final_output = f"=== 第 {args.chapter_no:03d} 章 大燕商行资产负债表 ===\n\n"
    final_output += format_assets_info(db)
    final_output += "\n\n========================================="
    
    print(final_output)

    # 如果传入了章节号，则将结果写入文件以便人类预览
    if args.chapter_no > 0:
        preview_dir = ROOT / "temp" / "workflow_preview"
        preview_dir.mkdir(parents=True, exist_ok=True)
        preview_file = preview_dir / f"assets_context_第{args.chapter_no:03d}章.md"
        try:
            preview_file.write_text(final_output, encoding="utf-8")
            print(f"\n[系统提示] 资产上下文已保存至预览文件: {preview_file.name}")
        except Exception as e:
            print(f"\n[系统警告] 无法保存预览文件: {e}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
