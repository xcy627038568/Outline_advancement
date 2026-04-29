#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import sys

from chapter_delete_utils import build_delete_plan, format_plan_text


def main() -> int:
    parser = argparse.ArgumentParser(description="章节删除预检脚本（只做 dry-run，不执行删除）")
    parser.add_argument("--chapter_no", type=int, required=True, help="删除起始章节号")
    parser.add_argument(
        "--mode",
        choices=["last_only", "tail"],
        default="tail",
        help="last_only=只删最后一章；tail=从指定章向后截断",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 输出预检结果",
    )
    args = parser.parse_args()

    try:
        plan = build_delete_plan(args.chapter_no, args.mode)
    except Exception as exc:
        print(f"预检失败: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(format_plan_text(plan))
        print("")
        print("当前为 dry-run，未执行任何删除。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
