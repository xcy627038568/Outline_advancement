#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from chapter_delete_utils import (
    DB_PATH,
    DELETE_BACKUP_DIR,
    build_delete_plan,
    format_plan_text,
    replay_ledgers,
)
import rebuild_novel_base_from_spec


ROOT = Path(__file__).resolve().parent.parent


def copy_to_backup(files: list[Path], backup_root: Path) -> list[Path]:
    copied = []
    for file_path in files:
        if not file_path.exists():
            continue
        target = backup_root / file_path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target)
        copied.append(target)
    return copied


def delete_original_files(files: list[Path]) -> int:
    deleted = 0
    for file_path in files:
        if not file_path.exists():
            continue
        file_path.unlink()
        deleted += 1
    return deleted


def validate_post_delete(cutoff: int, kept_count: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    try:
        written_after = conn.execute(
            "SELECT COUNT(*) FROM chapters_nav WHERE status = 'written' AND chapter_no >= ?",
            (cutoff,),
        ).fetchone()[0]
        kept_written = conn.execute(
            "SELECT COUNT(*) FROM chapters_nav WHERE status = 'written' AND chapter_no < ?",
            (cutoff,),
        ).fetchone()[0]
        character_rows = conn.execute(
            "SELECT COUNT(*) FROM character_history_log WHERE chapter_no >= ?",
            (cutoff,),
        ).fetchone()[0]
        asset_rows = conn.execute(
            "SELECT COUNT(*) FROM asset_history_log WHERE chapter_no >= ?",
            (cutoff,),
        ).fetchone()[0]
    finally:
        conn.close()

    if written_after != 0:
        raise RuntimeError(f"校验失败：第 {cutoff:03d} 章及之后仍有 {written_after} 条 written 章节。")
    if kept_written != kept_count:
        raise RuntimeError(f"校验失败：保留章节数应为 {kept_count}，实际为 {kept_written}。")
    if character_rows != 0:
        raise RuntimeError(f"校验失败：角色历史仍残留 {character_rows} 条。")
    if asset_rows != 0:
        raise RuntimeError(f"校验失败：资产历史仍残留 {asset_rows} 条。")

    return {
        "written_after_cutoff": written_after,
        "kept_written": kept_written,
        "deleted_character_history_rows": character_rows,
        "deleted_asset_history_rows": asset_rows,
    }


def restore_db(db_backup: Path) -> None:
    if db_backup.exists():
        shutil.copy2(db_backup, DB_PATH)


def main() -> int:
    parser = argparse.ArgumentParser(description="章节删除闭环脚本")
    parser.add_argument("--chapter_no", type=int, required=True, help="删除起始章节号")
    parser.add_argument(
        "--mode",
        choices=["last_only", "tail"],
        default="tail",
        help="last_only=只删最后一章；tail=从指定章向后截断",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="确认执行。若不带此参数，将只输出预检结果。",
    )
    args = parser.parse_args()

    try:
        plan = build_delete_plan(args.chapter_no, args.mode)
    except Exception as exc:
        print(f"删除预检失败: {exc}", file=sys.stderr)
        return 1

    print(format_plan_text(plan))
    if plan["missing_kept_ledgers"]:
        print("中止执行：保留章节存在缺失台账，无法安全重算。", file=sys.stderr)
        return 1

    if not args.execute:
        print("")
        print("当前为预检模式。确认无误后，请追加 --execute。")
        return 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = DELETE_BACKUP_DIR / f"delete_from_{plan['effective_cutoff']:03d}_{timestamp}"
    backup_root.mkdir(parents=True, exist_ok=True)
    db_backup = backup_root / "novel_ledger_before_delete.db"
    shutil.copy2(DB_PATH, db_backup)

    plan_file = backup_root / "delete_plan.json"
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    affected_paths = [Path(item) for item in plan["affected_files"]]
    kept_ledger_paths = [Path(item) for item in plan["kept_ledger_files"]]
    copy_to_backup(affected_paths, backup_root)

    try:
        print("")
        print("开始重建静态底库...")
        result = rebuild_novel_base_from_spec.main()
        if result != 0:
            raise RuntimeError(f"静态底库重建失败，返回码 {result}")

        if kept_ledger_paths:
            print("开始回放保留章节台账...")
            replay_ledgers(kept_ledger_paths)

        validation = validate_post_delete(plan["effective_cutoff"], len(plan["kept_written"]))
    except Exception as exc:
        restore_db(db_backup)
        print(f"删除失败，已自动恢复主库: {exc}", file=sys.stderr)
        return 1

    deleted_count = delete_original_files(affected_paths)

    report_lines = [
        "=== 删除闭环完成 ===",
        f"模式: {plan['mode']}",
        f"截断点: 第{plan['effective_cutoff']:03d}章",
        f"已删除已写章节: {', '.join(f'第{item:03d}章' for item in plan['affected_written'])}",
        f"保留已写章节数: {validation['kept_written']}",
        f"已清理原始文件数: {deleted_count}",
        f"主库备份: {db_backup}",
        f"删除归档目录: {backup_root}",
    ]
    report = "\n".join(report_lines)
    print("")
    print(report)
    (backup_root / "delete_report.txt").write_text(report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
