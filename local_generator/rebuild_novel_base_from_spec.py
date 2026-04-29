#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sqlite3
from pathlib import Path

from character_title_seed_data import BASE_CHARACTER_TITLE_DATA
from single_db_utils import upsert_character_title_timeline


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "novel_ledger.db"
SPEC_ROOT = ROOT / "SPEC"

SPEC_DIRS = [
    SPEC_ROOT / "01_核心宪法",
    SPEC_ROOT / "02_写作手册",
    SPEC_ROOT / "03_静态词典",
    SPEC_ROOT / "05_实体档案",
]

CHAPTER_SPEC_ROOT = SPEC_ROOT / "04_分卷细纲"

SCHEMA_SQL = """
DROP TABLE IF EXISTS chapters_nav;
DROP TABLE IF EXISTS entities_registry;
DROP TABLE IF EXISTS entity_relationships;
DROP TABLE IF EXISTS locations_and_territories;
DROP TABLE IF EXISTS wealth_and_assets;
DROP TABLE IF EXISTS hooks_network;
DROP TABLE IF EXISTS world_facts;
DROP TABLE IF EXISTS character_history_log;
DROP TABLE IF EXISTS asset_history_log;
DROP TABLE IF EXISTS character_titles_timeline;
DROP TABLE IF EXISTS spec_chunks;

CREATE TABLE chapters_nav (
    chapter_no INTEGER PRIMARY KEY,
    history_date_label TEXT,
    timeline_mark TEXT,
    stage_goal TEXT,
    chapter_target TEXT,
    written_summary TEXT,
    next_hook TEXT,
    key_assets_change TEXT,
    status TEXT
);

CREATE TABLE entities_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    entity_type TEXT,
    importance_level INTEGER,
    static_core TEXT,
    current_status TEXT,
    core_memories TEXT,
    last_update_chapter INTEGER,
    aliases_json TEXT,
    role_type TEXT,
    affiliation TEXT,
    occupation TEXT,
    personality TEXT,
    appearance TEXT,
    first_appearance TEXT,
    status TEXT,
    relationships_json TEXT,
    history_json TEXT
);

CREATE TABLE entity_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity TEXT,
    target_entity TEXT,
    relation_type TEXT,
    intensity INTEGER,
    last_event_chapter INTEGER,
    core_conflict TEXT
);

CREATE TABLE locations_and_territories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_name TEXT UNIQUE,
    owner_entity TEXT,
    function_desc TEXT,
    current_status TEXT,
    established_chapter INTEGER
);

CREATE TABLE wealth_and_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_name TEXT UNIQUE,
    asset_type TEXT,
    current_value TEXT,
    last_update_chapter INTEGER,
    hidden_risk TEXT,
    asset_group TEXT,
    value_kind TEXT,
    current_value_num REAL,
    current_value_text TEXT,
    unit TEXT
);

CREATE TABLE hooks_network (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hook_code TEXT UNIQUE,
    description TEXT,
    planted_in_chapter INTEGER,
    status TEXT,
    resolution TEXT
);

CREATE TABLE world_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT,
    fact_key TEXT,
    fact_value TEXT,
    notes TEXT
);

CREATE TABLE character_history_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_name TEXT NOT NULL,
    chapter_no INTEGER NOT NULL,
    event_summary TEXT NOT NULL,
    visibility TEXT DEFAULT '',
    certainty TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE asset_history_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_name TEXT NOT NULL,
    asset_group TEXT DEFAULT '',
    chapter_no INTEGER NOT NULL,
    value_kind TEXT DEFAULT 'text',
    value_num REAL,
    value_text TEXT DEFAULT '',
    change_note TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE character_titles_timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_name TEXT NOT NULL,
    start_chapter INTEGER NOT NULL,
    end_chapter INTEGER,
    timeline_mark TEXT DEFAULT '',
    identity_label TEXT DEFAULT '',
    narrative_label TEXT DEFAULT '',
    formal_title TEXT DEFAULT '',
    common_title TEXT DEFAULT '',
    self_title TEXT DEFAULT '',
    subordinate_title TEXT DEFAULT '',
    hostile_title TEXT DEFAULT '',
    public_title TEXT DEFAULT '',
    forbidden_titles_json TEXT DEFAULT '[]',
    scene_rules_json TEXT DEFAULT '{}',
    source_note TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_character_titles_unique
ON character_titles_timeline (character_name, start_chapter);

CREATE TABLE spec_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    section TEXT,
    domain TEXT,
    chunk_key TEXT,
    content TEXT NOT NULL,
    tags TEXT
);
"""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def clean_text(text: str | None) -> str:
    if text is None:
        return ""
    return re.sub(r"\n{3,}", "\n\n", str(text)).strip()


def clean_inline(text: str | None) -> str:
    return re.sub(r"\s+", " ", clean_text(text))


def split_markdown_sections(content: str) -> list[tuple[str, str]]:
    lines = content.splitlines()
    sections: list[tuple[str, str]] = []
    current_title = "全文"
    buffer: list[str] = []
    for line in lines:
        if re.match(r"^##+\s+", line):
            if clean_text("\n".join(buffer)):
                sections.append((current_title, clean_text("\n".join(buffer))))
            current_title = re.sub(r"^##+\s+", "", line).strip()
            buffer = []
            continue
        buffer.append(line)
    if clean_text("\n".join(buffer)):
        sections.append((current_title, clean_text("\n".join(buffer))))
    return sections


def insert_spec_chunks(conn: sqlite3.Connection) -> int:
    rows = []
    for directory in SPEC_DIRS:
        for path in sorted(directory.rglob("*.md")):
            rel = path.relative_to(ROOT).as_posix()
            domain = path.parent.name
            for idx, (section, content) in enumerate(split_markdown_sections(read_text(path)), start=1):
                rows.append(
                    (
                        rel,
                        section,
                        domain,
                        f"{path.stem}:{idx}",
                        content,
                        "|".join([path.parent.name, path.stem, section]),
                    )
                )
    conn.executemany(
        """
        INSERT INTO spec_chunks (source_file, section, domain, chunk_key, content, tags)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def insert_world_facts(conn: sqlite3.Connection) -> int:
    targets = [
        SPEC_ROOT / "01_核心宪法" / "01_故事世界观与全局大纲.md",
        SPEC_ROOT / "03_静态词典" / "人物称呼与场合速查表.md",
        SPEC_ROOT / "03_静态词典" / "地理与航线速查表.md",
        SPEC_ROOT / "03_静态词典" / "物价与商业标尺.md",
    ]
    rows = []
    for path in targets:
        for section, content in split_markdown_sections(read_text(path)):
            rows.append((path.parent.name, section, content, path.name))
    conn.executemany(
        "INSERT INTO world_facts (domain, fact_key, fact_value, notes) VALUES (?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def strip_enclosed_alias(name_text: str) -> tuple[str, list[str]]:
    aliases = re.findall(r"[（(]([^()（）]+)[)）]", name_text)
    name = re.sub(r"[（(][^()（）]+[)）]", "", name_text).strip()
    return name, [clean_inline(item) for item in aliases if clean_inline(item)]


def parse_character_sections(path: Path) -> list[dict]:
    content = read_text(path)
    lines = content.splitlines()
    section_title = ""
    current: dict | None = None
    records: list[dict] = []

    for raw_line in lines:
        line = raw_line.rstrip()
        sec_match = re.match(r"^##\s+(.+)", line)
        if sec_match:
            section_title = sec_match.group(1).strip()
            continue

        char_match = re.match(r"^###\s+(?:\d+\.\d+\s+)?(.+)", line)
        if char_match:
            if current:
                records.append(current)
            raw_name = char_match.group(1).strip()
            name, aliases = strip_enclosed_alias(raw_name)
            current = {
                "name": name,
                "aliases": aliases,
                "affiliation": section_title,
                "fields": {},
            }
            continue

        bullet_match = re.match(r"^- \*\*(.+?)\*\*[：:]\s*(.+)", line)
        if current and bullet_match:
            key = clean_inline(bullet_match.group(1))
            value = clean_inline(bullet_match.group(2))
            current["fields"][key] = value

    if current:
        records.append(current)
    return records


def importance_from_affiliation(affiliation: str, name: str) -> int:
    text = f"{affiliation} {name}"
    if any(token in text for token in ["主角", "核心皇室", "燕王府核心皇室"]):
        return 5
    if any(token in text for token in ["核心班底", "文官阵营", "婚配", "子女谱系"]):
        return 4
    if any(token in text for token in ["外围配角", "功能性历史人物"]):
        return 3
    return 3


def merge_character_fields(fields: dict, keys: list[str]) -> str:
    values = [fields.get(key, "") for key in keys if fields.get(key)]
    return "；".join(values)


def insert_characters(conn: sqlite3.Connection) -> int:
    sources = [
        SPEC_ROOT / "05_实体档案" / "核心角色与王府班底.md",
        SPEC_ROOT / "05_实体档案" / "文官阵营与外围配角.md",
        SPEC_ROOT / "05_实体档案" / "角色婚配与子女谱系.md",
    ]
    rows = []
    seen = set()
    for path in sources:
        for item in parse_character_sections(path):
            name = item["name"]
            if name in seen:
                continue
            seen.add(name)
            fields = item["fields"]
            relationships = {}
            for key in ["对主角态度", "与主角关系", "与正妃关系", "生母"]:
                if fields.get(key):
                    relationships[key] = fields[key]

            static_core = merge_character_fields(
                fields,
                ["核心人设", "底层动机", "核心特征", "底色", "性格底色", "核心立场"],
            )
            personality = merge_character_fields(
                fields,
                ["核心特征", "底色", "性格底色", "行事风格", "核心立场"],
            )
            occupation = merge_character_fields(fields, ["身份", "角色定位", "定位", "核心功能", "功能定位", "出身"])
            status = "静态设定已导入"
            rows.append(
                (
                    name,
                    "角色",
                    importance_from_affiliation(item["affiliation"], name),
                    static_core,
                    "",
                    "",
                    0,
                    json.dumps(item["aliases"], ensure_ascii=False),
                    fields.get("角色定位") or fields.get("身份") or "角色",
                    item["affiliation"],
                    occupation,
                    personality,
                    "",
                    "",
                    status,
                    json.dumps(relationships, ensure_ascii=False),
                    "[]",
                )
            )

    child_rows = parse_children_from_family_table()
    for row in child_rows:
        if row[0] in seen:
            continue
        seen.add(row[0])
        rows.append(row)

    conn.executemany(
        """
        INSERT INTO entities_registry (
            name, entity_type, importance_level, static_core, current_status,
            core_memories, last_update_chapter, aliases_json, role_type,
            affiliation, occupation, personality, appearance, first_appearance,
            status, relationships_json, history_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def parse_children_from_family_table() -> list[tuple]:
    path = SPEC_ROOT / "05_实体档案" / "角色婚配与子女谱系.md"
    rows = []
    in_table = False
    for line in read_text(path).splitlines():
        if line.startswith("| 排序 |"):
            in_table = True
            continue
        if in_table and line.startswith("|------|"):
            continue
        if in_table and line.startswith("|"):
            cells = [clean_inline(cell) for cell in line.strip().strip("|").split("|")]
            if len(cells) < 5:
                continue
            _, name, mother, personality, future_role = cells[:5]
            rows.append(
                (
                    name,
                    "角色",
                    4,
                    future_role,
                    "",
                    "",
                    0,
                    "[]",
                    "宗室子女",
                    "五、子女谱系（静态培养规划）",
                    f"生母：{mother}",
                    personality,
                    "",
                    "",
                    "静态设定已导入",
                    json.dumps({"生母": mother, "父亲": "朱高燧"}, ensure_ascii=False),
                    "[]",
                )
            )
            continue
        if in_table and line.strip() == "":
            break
    return rows


def add_relationship(relations: list[tuple], source: str, target: str, relation_type: str, intensity: int, conflict: str) -> None:
    relations.append((source, target, relation_type, intensity, 0, conflict))


def insert_relationships(conn: sqlite3.Connection) -> int:
    relations: list[tuple] = []
    add_relationship(relations, "朱棣", "朱高燧", "父子", 5, "父权控制与猜忌并存")
    add_relationship(relations, "徐皇后", "朱高燧", "母子", 5, "内院庇护与情感支柱")
    add_relationship(relations, "朱高炽", "朱高燧", "兄弟盟友", 5, "后勤与朝堂利益深度绑定")
    add_relationship(relations, "朱高煦", "朱高燧", "兄弟竞争", 5, "兵权与继承威胁")
    add_relationship(relations, "姚广孝", "朱高燧", "警惕试探", 5, "识破商业绑架政治的异数")
    add_relationship(relations, "王忠", "朱高燧", "主仆心腹", 4, "依附主角上升")
    add_relationship(relations, "宋老三", "朱高燧", "技术依附", 4, "被现代技术折服后签下死契")
    add_relationship(relations, "六子", "朱高燧", "班底培养", 4, "渴望立功并向执行层成长")
    add_relationship(relations, "陈奉", "朱高燧", "财务依附", 4, "被新式账法折服")
    add_relationship(relations, "钱福海", "朱高燧", "利益绑定", 4, "外部商路白手套")
    add_relationship(relations, "张武", "朱高燧", "军方接口", 4, "救护物资建立军方信任")
    add_relationship(relations, "顾清漪", "朱高燧", "夫妻", 5, "稳住赵王府体面与后宅秩序")
    add_relationship(relations, "温采蘩", "朱高燧", "夫妻", 4, "书坊与舆论线后宅接口")
    add_relationship(relations, "苏云舸", "朱高燧", "夫妻", 4, "海贸与港口线伙伴")

    children = [
        ("朱瞻垣", "顾清漪"),
        ("朱明婉", "顾清漪"),
        ("朱瞻坤", "温采蘩"),
        ("朱瞻埏", "苏云舸"),
        ("朱明珂", "苏云舸"),
    ]
    for child, mother in children:
        add_relationship(relations, "朱高燧", child, "父子女", 5, "产业承接与宗室延续")
        add_relationship(relations, mother, child, "母子女", 5, "后宅培养与资源分配")

    conn.executemany(
        """
        INSERT INTO entity_relationships (
            source_entity, target_entity, relation_type, intensity, last_event_chapter, core_conflict
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        relations,
    )
    return len(relations)


def parse_markdown_table(content: str, title: str) -> list[list[str]]:
    lines = content.splitlines()
    rows: list[list[str]] = []
    collecting = False
    for line in lines:
        if line.strip().startswith(title):
            collecting = True
            continue
        if not collecting:
            continue
        if not line.startswith("|"):
            if rows:
                break
            continue
        if line.startswith("|------") or line.startswith("|----------"):
            continue
        cells = [clean_inline(cell) for cell in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows[1:] if rows and rows[0][0] in {"点位", "项目", "起点", "类型"} else rows


def insert_locations(conn: sqlite3.Connection) -> int:
    path = SPEC_ROOT / "03_静态词典" / "地理与航线速查表.md"
    content = read_text(path)
    rows = []

    for cells in parse_markdown_table(content, "## 二、北平城内关键点位"):
        if len(cells) < 4:
            continue
        name, function_desc, relation, scenes = cells[:4]
        rows.append((name, "", f"{function_desc}；与主角关系：{relation}；常用剧情：{scenes}", "静态设定", 0))

    for cells in parse_markdown_table(content, "## 四、主要城际路线"):
        if len(cells) < 5:
            continue
        start, end, way, normal_time, cargo = cells[:5]
        location_name = f"{start}-{end}路线"
        desc = f"方式：{way}；常规时间：{normal_time}；常见货类：{cargo}"
        rows.append((location_name, "", desc, "静态设定", 0))

    port_matches = re.findall(
        r"###\s+5\.\d+\s+(.+?)\n\n- 作用[:：](.+?)\n- 常见货[:：](.+?)\n- 写作关键词[:：](.+?)(?:\n|$)",
        content,
        flags=re.S,
    )
    for name, function_desc, goods, keywords in port_matches:
        rows.append(
            (
                clean_inline(name),
                "",
                f"作用：{clean_inline(function_desc)}；常见货：{clean_inline(goods)}；关键词：{clean_inline(keywords)}",
                "静态设定",
                0,
            )
        )

    conn.executemany(
        """
        INSERT INTO locations_and_territories (
            location_name, owner_entity, function_desc, current_status, established_chapter
        ) VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def insert_asset_skeleton(conn: sqlite3.Connection) -> int:
    assets = [
        ("现银", "资金", "0", 0, "", "funds", "number", 0, "", "两"),
        ("备用现银", "资金", "0", 0, "", "funds", "number", 0, "", "两"),
        ("猪油储备", "原材料", "0", 0, "", "raw_materials", "number", 0, "", "斤"),
        ("草木灰储备", "原材料", "0", 0, "", "raw_materials", "number", 0, "", "斤"),
        ("粗盐储备", "原材料", "0", 0, "", "raw_materials", "number", 0, "", "斤"),
        ("香皂库存", "成品", "0", 0, "", "products", "number", 0, "", "块"),
        ("烈酒库存", "成品", "0", 0, "", "products", "number", 0, "", "斤"),
        ("伤药库存", "成品", "0", 0, "", "products", "number", 0, "", "份"),
        ("偏院可用人手", "人力", "待建立", 0, "", "personnel", "text", None, "待建立", ""),
        ("工匠人数", "人力", "0", 0, "", "personnel", "number", 0, "", "人"),
        ("特许经营权", "关键资产", "未建立", 0, "", "key_items", "text", None, "未建立", ""),
        ("四海商票系统", "关键资产", "未启用", 0, "", "key_items", "text", None, "未启用", ""),
    ]
    conn.executemany(
        """
        INSERT INTO wealth_and_assets (
            asset_name, asset_type, current_value, last_update_chapter, hidden_risk,
            asset_group, value_kind, current_value_num, current_value_text, unit
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        assets,
    )
    return len(assets)


def extract_field(block: str, label: str) -> str:
    match = re.search(rf"-\s*{re.escape(label)}[:：]\s*(.+)", block)
    return clean_inline(match.group(1)) if match else ""


def split_blocks(content: str, marker: str) -> list[str]:
    return [block.strip() for block in re.split(rf"\n(?={re.escape(marker)})", "\n" + content) if block.strip()]


def build_chapter_nav_rows() -> list[tuple]:
    chapter_map: dict[int, dict] = {}

    for volume_dir in sorted(CHAPTER_SPEC_ROOT.iterdir()):
        if not volume_dir.is_dir():
            continue

        unit_dir = volume_dir / "百章细纲"
        if unit_dir.exists():
            for file_path in sorted(unit_dir.glob("*.md")):
                for block in split_blocks(read_text(file_path), "【片段"):
                    range_match = re.search(r"第(\d+)章[–-]第(\d+)章", block)
                    if not range_match:
                        continue
                    start_no = int(range_match.group(1))
                    end_no = int(range_match.group(2))
                    function = extract_field(block, "剧情功能")
                    summary = extract_field(block, "概要")
                    climax = extract_field(block, "小高潮")
                    for chapter_no in range(start_no, end_no + 1):
                        chapter_map[chapter_no] = {
                            "stage_goal": function or "待写",
                            "chapter_target": "；".join([part for part in [summary, climax] if part]),
                        }

        outline_files = sorted(volume_dir.glob("*卷百章纲要.md"))
        for file_path in outline_files:
            for block in split_blocks(read_text(file_path), "【单元"):
                range_match = re.search(r"第(\d+)章[–-]第(\d+)章", block)
                if not range_match:
                    continue
                start_no = int(range_match.group(1))
                end_no = int(range_match.group(2))
                stage = extract_field(block, "单元定位")
                summary = extract_field(block, "单元概要")
                climax = extract_field(block, "阶段高潮")
                for chapter_no in range(start_no, end_no + 1):
                    if chapter_no in chapter_map:
                        continue
                    chapter_map[chapter_no] = {
                        "stage_goal": stage or "待写",
                        "chapter_target": "；".join([part for part in [summary, climax] if part]),
                    }

        single_dir = volume_dir / "单章细纲"
        if single_dir.exists():
            for file_path in sorted(single_dir.glob("*.md")):
                for block in split_blocks(read_text(file_path), "**第"):
                    first_line = block.splitlines()[0]
                    match = re.match(r"\*\*第(\d+)章(?:：| )(.+)", first_line)
                    if not match:
                        continue
                    chapter_no = int(match.group(1))
                    core_event = extract_field(block, "核心事件")
                    push = extract_field(block, "推动剧情点")
                    suspense = extract_field(block, "章末悬念")
                    chapter_map[chapter_no] = {
                        "stage_goal": push or extract_field(block, "关键对话/心理") or "待写",
                        "chapter_target": "；".join([part for part in [core_event, suspense] if part]),
                    }

    rows = []
    for chapter_no in sorted(chapter_map):
        payload = chapter_map[chapter_no]
        rows.append(
            (
                chapter_no,
                "",
                "",
                payload["stage_goal"],
                payload["chapter_target"],
                None,
                None,
                None,
                "pending",
            )
        )
    return rows


def insert_chapter_nav(conn: sqlite3.Connection) -> int:
    rows = build_chapter_nav_rows()
    conn.executemany(
        """
        INSERT INTO chapters_nav (
            chapter_no, history_date_label, timeline_mark, stage_goal, chapter_target,
            written_summary, next_hook, key_assets_change, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def summarize_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        "chapters_nav",
        "entities_registry",
        "entity_relationships",
        "locations_and_territories",
        "wealth_and_assets",
        "character_titles_timeline",
        "world_facts",
        "spec_chunks",
    ]
    counts = {}
    cur = conn.cursor()
    for table in tables:
        counts[table] = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return counts


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_SQL)
        chunk_count = insert_spec_chunks(conn)
        fact_count = insert_world_facts(conn)
        char_count = insert_characters(conn)
        relation_count = insert_relationships(conn)
        location_count = insert_locations(conn)
        asset_count = insert_asset_skeleton(conn)
        chapter_count = insert_chapter_nav(conn)
        title_count = 0
        for name, entries in BASE_CHARACTER_TITLE_DATA.items():
            title_count += upsert_character_title_timeline(conn, name, entries)
        conn.commit()

        counts = summarize_counts(conn)
        print("已完成主库全量重建。")
        print(f"主库路径: {DB_PATH}")
        print(
            "导入统计: "
            f"spec_chunks={chunk_count}, world_facts={fact_count}, "
            f"entities={char_count}, relationships={relation_count}, "
            f"locations={location_count}, assets={asset_count}, "
            f"chapters={chapter_count}, character_titles={title_count}"
        )
        print("表内计数:")
        for table, count in counts.items():
            print(f"- {table}: {count}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
