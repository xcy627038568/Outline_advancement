#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首批角色动态称谓种子脚本
用途：为高频核心角色建立按章节生效的称谓时间轴。
"""

from character_title_seed_data import BASE_CHARACTER_TITLE_DATA
from single_db_utils import ensure_schema, get_connection, upsert_character_title_timeline


def main() -> int:
    conn = get_connection()
    try:
        ensure_schema(conn)
        total = 0
        for name, entries in BASE_CHARACTER_TITLE_DATA.items():
            total += upsert_character_title_timeline(conn, name, entries)
        conn.commit()
        print(f"已写入角色动态称谓记录 {total} 条，覆盖 {len(BASE_CHARACTER_TITLE_DATA)} 个角色。")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
