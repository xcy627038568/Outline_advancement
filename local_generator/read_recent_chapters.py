#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前情摘要读取脚本
用途：只读取数据库中的上一章摘要、钩子与时间线，避免旧正文污染重写流程。
"""

import argparse
import sys
from pathlib import Path
from single_db_utils import DB_PATH, get_connection, normalize_timeline_text

ROOT = Path(__file__).resolve().parent.parent

def get_chapter_metadata(chapter_no: int) -> dict:
    if not DB_PATH.exists():
        return {}
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # 检查表结构
        cur.execute("PRAGMA table_info(chapters_nav)")
        columns = [info[1] for info in cur.fetchall()]
        
        if "timeline_mark" in columns:
            cur.execute(
                """
                SELECT COALESCE(timeline_mark, history_date_label) AS timeline_mark,
                       written_summary, key_assets_change, next_hook
                FROM chapters_nav
                WHERE chapter_no = ?
                """,
                (chapter_no,),
            )
        else:
            cur.execute("SELECT written_summary, key_assets_change, next_hook FROM chapters_nav WHERE chapter_no = ?", (chapter_no,))
            
        row = cur.fetchone()
        conn.close()
        
        if row:
            data = dict(row)
            data["timeline_mark"] = normalize_timeline_text(data.get("timeline_mark", ""))
            return data
        return {}
    except Exception as e:
        print(f"[系统警告] 读取 SQLite 元数据失败: {e}", file=sys.stderr)
        return {}

def main():
    parser = argparse.ArgumentParser(description="读取上一章前情与时间线")
    parser.add_argument("--chapter_no", type=int, required=True, help="要查询的上一章章节号（例如当前写23章，这里传22）")
    args = parser.parse_args()

    meta = get_chapter_metadata(args.chapter_no)
    output = []
    output.append(f"=== 上一章 (第 {args.chapter_no:03d} 章) 前情摘要 ===")
    
    timeline = meta.get("timeline_mark", "")
    if timeline:
        output.append(f"【时间线记录】：{timeline}")
    else:
        output.append("【时间线记录】：(未记录)")
        
    assets = meta.get("key_assets_change", "")
    if assets:
        output.append(f"【关键资产变化】：{assets}")
        
    hook = meta.get("next_hook", "")
    if hook:
        output.append(f"【遗留悬念(Hook)】：{hook}")

    summary = meta.get("written_summary", "")
    if summary:
        output.append(f"【上一章摘要】：{summary}")
    else:
        output.append("【上一章摘要】：(未记录)")

    output.append("\n【读取策略说明】：已禁用正文尾段读取，当前只使用数据库中的时间线、摘要、钩子与资产变化。")
    output.append("=========================================")
    
    print("\n".join(output))
    return 0

if __name__ == "__main__":
    sys.exit(main())
