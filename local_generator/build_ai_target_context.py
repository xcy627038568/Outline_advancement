import argparse
from pathlib import Path
import re

from single_db_utils import (
    ensure_schema,
    get_connection,
    get_effective_titles_for_characters,
    normalize_timeline_text,
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "temp" / "workflow_preview"
SPEC_DIR = ROOT / "SPEC" / "04_分卷细纲"


def find_file_by_pattern(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    for file_path in directory.glob("*.md"):
        if pattern in file_path.name:
            return file_path
    return None


def split_single_chapter_blocks(content: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n(?=\*\*第\d+章)", "\n" + content) if block.strip()]


def load_all_single_chapters(volume_dir: Path) -> dict[int, tuple[str, str]]:
    single_chapter_dir = volume_dir / "单章细纲"
    chapter_dict: dict[int, tuple[str, str]] = {}
    if not single_chapter_dir.exists():
        return chapter_dict

    for file_path in sorted(single_chapter_dir.glob("*.md")):
        content = file_path.read_text(encoding="utf-8")
        for block in split_single_chapter_blocks(content):
            match = re.match(r"\*\*第(\d+)章(?:：| )(.+)", block.splitlines()[0])
            if not match:
                continue
            chapter_dict[int(match.group(1))] = (match.group(2).strip(), block)
    return chapter_dict


def find_volume_dir_by_chapter(chapter_no: int) -> tuple[Path | None, dict[int, tuple[str, str]]]:
    for volume_dir in sorted(SPEC_DIR.iterdir()):
        if not volume_dir.is_dir():
            continue
        chapter_dict = load_all_single_chapters(volume_dir)
        if chapter_no in chapter_dict:
            return volume_dir, chapter_dict
    return None, {}


def iter_unit_blocks(volume_dir: Path) -> list[tuple[Path, str]]:
    unit_dir = volume_dir / "百章细纲"
    blocks: list[tuple[Path, str]] = []
    if not unit_dir.exists():
        return blocks
    for file_path in sorted(unit_dir.glob("*.md")):
        content = file_path.read_text(encoding="utf-8")
        for block in re.split(r"\n(?=【片段)", "\n" + content):
            block = block.strip()
            if block:
                blocks.append((file_path, block))
    return blocks


def parse_chapter_range(text: str) -> tuple[int, int] | None:
    match = re.search(r"第(\d+)章[–-]第(\d+)章", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def find_matching_unit_block(volume_dir: Path, chapter_no: int) -> tuple[Path | None, str]:
    best_match: tuple[Path | None, str, int] = (None, "未找到覆盖当前章节的单元细纲。", 10**9)
    for file_path, block in iter_unit_blocks(volume_dir):
        chapter_range = parse_chapter_range(block)
        if not chapter_range:
            continue
        start_no, end_no = chapter_range
        if start_no <= chapter_no <= end_no:
            span = end_no - start_no
            if span < best_match[2]:
                best_match = (file_path, block, span)
    return best_match[0], best_match[1]


def extract_field(block: str, label: str) -> str:
    match = re.search(rf"-\s*{re.escape(label)}[:：]\s*(.+)", block)
    return match.group(1).strip() if match else ""

def match_relevant_characters(chars, *texts: str) -> list[dict]:
    merged_text = "\n".join(text for text in texts if text)
    if not merged_text.strip():
        return []
    matched = []
    for char in chars:
        name = char["name"]
        if name and name in merged_text:
            matched.append(char)
    return matched


def infer_viewpoint_names(curr_chapter_content: str) -> list[str]:
    for line in curr_chapter_content.splitlines():
        match = re.match(r"-\s*视角[:：]\s*(.+)", line)
        if not match:
            continue
        return [item.strip() for item in re.split(r"[\\/、,，]", match.group(1)) if item.strip()]
    return []


def build_do_not_advance(next_block: str) -> str:
    if not next_block or next_block.startswith("无后续细纲"):
        return "无后续章节细纲，不额外设置禁止提前兑现项。"
    header = next_block.splitlines()[0].strip("* ")
    core_event = extract_field(next_block, "核心事件") or extract_field(next_block, "概要")
    if core_event:
        return f"止步于本章悬念，不提前写入下一章《{header}》的核心推进：{core_event}"
    return f"止步于本章悬念，不提前兑现下一章《{header}》中的冲突与结果。"


def build_target_context(chapter_no: int):
    volume_dir, chapter_dict = find_volume_dir_by_chapter(chapter_no)
    if not volume_dir:
        raise FileNotFoundError(f"未能在单章细纲中定位第 {chapter_no} 章。")

    volume_name = volume_dir.name
    volume_outline_file = find_file_by_pattern(volume_dir, "百章纲要")
    volume_outline = volume_outline_file.read_text(encoding="utf-8") if volume_outline_file else "未找到本卷纲要。"

    unit_file, unit_block = find_matching_unit_block(volume_dir, chapter_no)
    unit_summary = extract_field(unit_block, "概要")
    unit_climax = extract_field(unit_block, "小高潮")

    past_chapters = [chapter_dict[i][1] for i in range(chapter_no - 2, chapter_no) if i in chapter_dict]
    curr_chapter_content = chapter_dict.get(chapter_no, ("", "⚠️ 未找到当前章细纲。"))[1]
    future_chapters = [chapter_dict[i][1] for i in range(chapter_no + 1, chapter_no + 3) if i in chapter_dict]

    past_text = "\n\n".join(past_chapters) if past_chapters else "无前置细纲或已超出范围"
    future_text = "\n\n".join(future_chapters) if future_chapters else "无后续细纲或已超出范围"

    stop_point = extract_field(curr_chapter_content, "章末悬念") or extract_field(curr_chapter_content, "推动剧情点") or "必须在本章小高潮后收束，不跨入下一章事件。"
    do_not_advance = build_do_not_advance(future_chapters[0] if future_chapters else "")

    conn = get_connection()
    ensure_schema(conn)
    cur = conn.cursor()
    prev_no = chapter_no - 1
    prev_row = cur.execute(
        "SELECT timeline_mark, written_summary, next_hook, key_assets_change FROM chapters_nav WHERE chapter_no = ?",
        (prev_no,),
    ).fetchone()
    chars = cur.execute(
        """
        SELECT name, static_core
        FROM entities_registry
        WHERE entity_type = '角色' AND importance_level >= 4
        ORDER BY importance_level DESC, name
        """
    ).fetchall()
    relevant_chars = match_relevant_characters(
        chars,
        curr_chapter_content,
        prev_row["written_summary"] if prev_row and prev_row["written_summary"] else "",
        prev_row["next_hook"] if prev_row and prev_row["next_hook"] else "",
    )
    if not relevant_chars:
        viewpoint_names = infer_viewpoint_names(curr_chapter_content)
        relevant_chars = [char for char in chars if char["name"] in viewpoint_names]
    if not relevant_chars:
        relevant_chars = list(chars[:5])

    title_map = get_effective_titles_for_characters(conn, chapter_no, [char["name"] for char in relevant_chars])
    prev_timeline = normalize_timeline_text(prev_row["timeline_mark"]) if prev_row and prev_row["timeline_mark"] else "无"

    content = f"""# AI 单章战术突击靶点：第 {chapter_no} 章

> ⚠️ 本文件用于锁定当前章写作范围。只能写本章，不能提前兑现下一章。

---

## 0. 全局视野：百章纲要（{volume_name}）
{volume_outline[:500]}... (截取部分)

---

## 1. 当前单元细纲定位
- 单元来源：{unit_file.name if unit_file else '未定位到单元文件'}
- 单元摘要：{unit_summary or '未提取到概要'}
- 单元小高潮：{unit_climax or '未提取到小高潮'}

```markdown
{unit_block}
```

---

## 2. 当前 5 章精细视野
### 【已完成（供参考，绝对勿写）】
```markdown
{past_text}
```

### 【▶ 本章必写任务 ◀】
```markdown
{curr_chapter_content}
```

### 【未来视野（后续剧情，绝对勿写）】
```markdown
{future_text}
```

---

## 3. 章边界约束
- 本章止步点：{stop_point}
- 下一章禁止提前兑现项：{do_not_advance}

---

## 4. 上一章基线坑位
- 上一章时间线：{prev_timeline}
- 上一章实际剧情摘要：{prev_row['written_summary'] if prev_row and prev_row['written_summary'] else '无'}
- 上一章抛出的钩子：{prev_row['next_hook'] if prev_row and prev_row['next_hook'] else '无'}
- 上一章资产变化：{prev_row['key_assets_change'] if prev_row and prev_row['key_assets_change'] else '无'}

---

## 5. 核心参战角色坐标
"""
    for char in relevant_chars:
        content += f"- **{char['name']}**：{char['static_core']}\n"

    content += "\n---\n## 5.5 本章称谓约束\n"
    if title_map:
        for name, title_info in title_map.items():
            parts = []
            if title_info.get("narrative_label"):
                parts.append(f"旁白：{title_info['narrative_label']}")
            if title_info.get("formal_title"):
                parts.append(f"正式：{title_info['formal_title']}")
            if title_info.get("common_title"):
                parts.append(f"常用：{title_info['common_title']}")
            if title_info.get("subordinate_title"):
                parts.append(f"下属：{title_info['subordinate_title']}")
            forbidden_titles = title_info.get("forbidden_titles") or []
            if forbidden_titles:
                parts.append(f"禁用：{'、'.join(forbidden_titles)}")
            if not parts:
                parts.append("当前未配置动态称谓")
            content += f"- **{name}**：{'；'.join(parts)}\n"
    else:
        content += "- 当前章暂无动态称谓配置。\n"

    content += """
---
## 6. AI 执行检查单
- [ ] 我是否只写到了本章止步点？
- [ ] 我是否没有提前兑现下一章任务？
- [ ] 我是否落实了当前单元细纲的概要与小高潮？
"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"ai_target_context_第{chapter_no:03d}章.md"
    out_file.write_text(content, encoding="utf-8")
    conn.close()
    print(f"[OK] V4 战术靶点雷达已生成：{out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("chapter_no", type=int)
    args = parser.parse_args()
    build_target_context(args.chapter_no)
