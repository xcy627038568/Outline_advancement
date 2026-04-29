#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import re
from pathlib import Path

from single_db_utils import get_connection, get_columns, parse_json_text


ROOT = Path(__file__).absolute().parent.parent
CHAPTER_DIR = ROOT / "chapter"
OUTLINE_ROOT = ROOT / "SPEC" / "04_分卷细纲"
TEMP_DIR = ROOT / "temp"
OUTPUT_DIR = ROOT / "temp" / "reference_pack"
CHAPTER_START = 1
CHAPTER_END = 22

KNOWN_ISSUES = {
    20: [
        "凤姐在街头一眼看穿朱棣是假疯，与后文需要她主动散播‘燕王真疯’的功能冲突。",
        "结尾直接把五万两资金与军工计划绑死，推进速度过快，提前吞掉后续章空间。",
        "凤姐既像老江湖又像被牵着走的工具人，话术和判断力前后不稳。",
    ],
    21: [
        "偏院前文被写成燕王府最深处的铁桶地盘，但暗探潜入过于轻松，安保强弱失衡。",
        "朱高燧对父权试探的判断过早过满，悬疑感被直接讲破。",
        "‘上牌桌资格’等近现代表达偏重，容易把历史语感拉出戏。",
    ],
    22: [
        "过早锁定‘老王头=袁珙’，把后续识破与确认戏份提前写完。",
        "结尾直接决定主动拿账本和银子去敲内务大总管，已提前写到第23至24章任务区。",
        "主角内心分析过于完整，压缩了试探博弈本应保留的灰度空间。",
    ],
}

DO_NOT_ADVANCE = {
    20: "不得在本章确认朱棣已被凤姐看穿，更不得提前把资金直接转入军工采购闭环。",
    21: "不得把父权试探写成结论性定案，只能写成内查启动与主角察觉压力。",
    22: "不得正式锁死老王头就是袁珙，不得提前写到主角主动摊牌或拿账本上门。",
}

INFO_EXPOSURE_ROWS = [
    ("朱棣对偏院生意异动已进入怀疑阶段", "朱棣、主角", "中层", 21),
    ("袁珙已以低姿态方式接近偏院", "袁珙、主角", "表层", 22),
    ("凤姐已知香皂不是海外现成舶来货", "凤姐、主角阵营", "中层", 20),
    ("孔方已知道主角在做高价香皂生意并负责台前谈判", "孔方、主角", "深层", 20),
    ("老刘已掌握偏院工坊、护卫网与外部合作的执行层细节", "老刘、主角", "深层", 19),
    ("青鸾知道主角在偏院暗中做皂、藏锋自保", "青鸾、主角", "中层", 4),
    ("赵一刀知道废油可变现为暴利香皂", "赵一刀、主角、老刘", "中层", 18),
    ("赵一刀已与主角形成技术+原料合作关系", "赵一刀、主角、老刘", "中层", 19),
    ("教坊司已成为外部高端销路核心客户", "凤姐、主角、孔方", "中层", 20),
    ("偏院已收拢底层护卫形成初步利益共同体", "主角、老刘、底层护卫", "中层", 9),
    ("朱能等燕军视角已知道香皂具有去污与潜在军需价值", "朱能、主角", "表层", 8),
]

CHAPTER_EXPOSURE_MAP: dict[int, list[str]] = {}
for info, _knowers, _depth, chapter_no in INFO_EXPOSURE_ROWS:
    CHAPTER_EXPOSURE_MAP.setdefault(chapter_no, []).append(info)

ROLE_SNAPSHOT_ROWS = [
    {
        "name": "朱高燧",
        "public_persona": "偏院里忽然强硬起来、懂赚钱也护短的三殿下。",
        "real_goal": "先保命与藏锋，再把肥皂经营线转成可用的政治筹码与后续战争准备。",
        "current_risk": "资金增长过快，已引来父权与情报线注意；旧正文存在越章抢跑风险。",
        "watched_by": "朱棣、袁珙、凤姐、赵一刀。",
    },
    {
        "name": "朱棣",
        "public_persona": "对外仍维持装疯卖傻的表层状态。",
        "real_goal": "压低朝廷警觉，同时筛查王府内部一切异常变量。",
        "current_risk": "既要维持疯态，又不能放任偏院异动失控。",
        "watched_by": "朝廷密使、王府内外眼线。",
    },
    {
        "name": "袁珙",
        "public_persona": "到第022章旧正文里以杂役身份低姿态潜近偏院。",
        "real_goal": "替朱棣摸清主角是否有野心、是否会坏大局。",
        "current_risk": "若被写成过早看透或被主角彻底认出，会直接吞掉后续试探空间。",
        "watched_by": "朱棣直接调用。",
    },
    {
        "name": "孔方",
        "public_persona": "台前账房与谈判人，能算账也能圆话。",
        "real_goal": "依附主角求活并借生意翻身。",
        "current_risk": "知道经营机密较多，但仍属可控合作心腹。",
        "watched_by": "主角、老刘。",
    },
    {
        "name": "青鸾",
        "public_persona": "忠心又胆小的贴身丫鬟。",
        "real_goal": "跟紧主角活下去，执行偏院内务与工坊杂活。",
        "current_risk": "知道偏院工坊存在，若落入外人手里容易成为突破口。",
        "watched_by": "主角保护范围内，外部默认边缘人物。",
    },
    {
        "name": "老刘",
        "public_persona": "偏院护卫头子兼脏活执行者。",
        "real_goal": "稳住偏院安全和外部合作链条，替主角挡刀。",
        "current_risk": "执行层知道得多，任何安保失手都会连带暴露主角底牌。",
        "watched_by": "主角、屠宰场和外部接头人也会观察他。",
    },
    {
        "name": "赵一刀",
        "public_persona": "城南屠宰场老板，贪狠并存。",
        "real_goal": "借废油和场地吃进香皂利润。",
        "current_risk": "掌握原料端，随时可能因贪心反咬或泄密。",
        "watched_by": "主角、老刘。",
    },
    {
        "name": "凤娇娇",
        "public_persona": "教坊司头面人物，强势精明。",
        "real_goal": "垄断香皂货源，保住欢场头牌位置。",
        "current_risk": "卷进燕王府势力涟漪，认知边界一旦写过头会破坏后续政治层级。",
        "watched_by": "主角阵营也在反向观察她的价值与风险。",
    },
]

ERROR_SAMPLE_SECTIONS = {
    "越章抢跑": [
        ("第020章", "“把这些银子，变成刺向朝廷咽喉的利剑”", "本章应停在大额契约成立，不该把后续军工用途直接写死。"),
        ("第022章", "“很可能就是……袁珙”", "本章最多到疑似内查，不该正式锁死来者身份。"),
        ("第022章", "“明天，他将带着那份精心伪造的阴阳账本……”", "已经提前兑现第23-24章主动应对动作。"),
    ],
    "现代黑话": [
        ("第021章", "“上牌桌的资格”", "现代语感过强，破坏历史权谋文语域。"),
        ("第020章", "“资金流动”", "抽象财经用语过现代，宜改成银钱进出或现银动静。"),
        ("第019章", "“争霸天下”直白灌顶", "把阶段性求生经营硬拉到终局口号，语气失真。"),
    ],
    "上帝视角总结": [
        ("第020章", "“饥饿营销的胜利……彻底站稳了脚跟”", "像作者给读者做结案陈词，不像当场叙事。"),
        ("第021章", "“第一回合的试探……成功骗过了……”", "把本应留白的博弈结果直接官宣。"),
        ("第022章", "“一场关于权力、财富与生死的心理博弈……”", "总结式收尾，把悬念写成预告片。"),
    ],
    "前后逻辑自撞": [
        ("第020章", "凤姐先看穿朱棣假疯，后文又需要她去帮忙扩散真疯印象", "同一角色认知和功能自撞。"),
        ("第021章", "偏院先被写成铁桶地盘，后又让暗探如入无人之境", "安保强度设定前后不一。"),
        ("第022章", "主角一边只是察觉有异，一边又几乎全知全能推完对方身份与后招", "信息边界失衡。"),
    ],
}


def clean_text(value) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def chapter_slug(chapter_no: int) -> str:
    return f"第{chapter_no:03d}章"


def chapter_range_slug() -> str:
    return f"{CHAPTER_START:03d}-{CHAPTER_END:03d}"


def chapter_scope_slug() -> str:
    return f"截至{CHAPTER_END:03d}章"


def build_target_files() -> dict[str, Path]:
    return {
        "chapter_facts": TEMP_DIR / f"章节事实卡_{chapter_range_slug()}.md",
        "unit_cards": TEMP_DIR / f"单元连续性卡_{chapter_range_slug()}.md",
        "character_snapshot": TEMP_DIR / f"角色状态快照_{chapter_scope_slug()}.md",
        "asset_snapshot": TEMP_DIR / f"资产经营状态快照_{chapter_scope_slug()}.md",
        "exposed_info": TEMP_DIR / f"已曝光信息表_{chapter_scope_slug()}.md",
        "error_samples": TEMP_DIR / "旧正文错误样本表.md",
        "outline_audit": TEMP_DIR / f"细纲来源审计_{chapter_range_slug()}.md",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成章节参考包")
    parser.add_argument("--start", type=int, default=CHAPTER_START, help="起始章节号")
    parser.add_argument("--end", type=int, default=CHAPTER_END, help="结束章节号")
    return parser.parse_args()


def escape_cell(value) -> str:
    return clean_text(value).replace("|", "\\|")


def split_outline_blocks(content: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n(?=\*\*第\d+章)", "\n" + content) if block.strip()]


def outline_relpath(path: Path) -> str:
    try:
        return path.relative_to(OUTLINE_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_single_outline_map() -> dict[int, dict]:
    result = {}
    for path in sorted(OUTLINE_ROOT.glob("*/单章细纲/*.md")):
        content = read_text(path)
        for block in split_outline_blocks(content):
            lines = [line.rstrip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            match = re.match(r"\*\*第(\d+)章[：: ](.+?)\*\*$", lines[0].strip())
            if not match:
                continue
            chapter_no = int(match.group(1))
            entry = {
                "chapter_no": chapter_no,
                "outline_title": clean_text(match.group(2)),
                "source_file": outline_relpath(path),
            }
            for line in lines[1:]:
                bullet = re.match(r"-\s*([^：:]+)[：:]\s*(.+)", line)
                if bullet:
                    entry[clean_text(bullet.group(1))] = clean_text(bullet.group(2))
            result[chapter_no] = entry
    return result


def parse_unit_outline_map() -> dict[int, dict]:
    result = {}
    for path in sorted(OUTLINE_ROOT.glob("*/百章细纲/*.md")):
        content = read_text(path)
        blocks = [block.strip() for block in re.split(r"\n(?=【片段)", "\n" + content) if block.strip()]
        for block in blocks:
            lines = [line.rstrip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            match = re.match(r"【([^】]+)：第(\d+)章[–—-]第(\d+)章】", lines[0].strip())
            if not match:
                continue
            segment_name = clean_text(match.group(1))
            start_no = int(match.group(2))
            end_no = int(match.group(3))
            entry = {
                "segment_name": segment_name,
                "range_text": f"{start_no}-{end_no}",
                "source_file": outline_relpath(path),
            }
            for line in lines[1:]:
                bullet = re.match(r"-\s*([^：:]+)[：:]\s*(.+)", line)
                if bullet:
                    entry[clean_text(bullet.group(1))] = clean_text(bullet.group(2))
            for chapter_no in range(start_no, end_no + 1):
                result[chapter_no] = entry
    return result


def get_available_select_clause(columns: set[str], aliases: list[tuple[str, str]]) -> str:
    select_fields = []
    for source_name, alias_name in aliases:
        if source_name in columns:
            select_fields.append(f"{source_name} AS {alias_name}")
        else:
            select_fields.append(f"'' AS {alias_name}")
    return ", ".join(select_fields)


def load_chapter_rows() -> dict[int, dict]:
    conn = get_connection()
    columns = get_columns(conn, "chapters_nav")
    select_clause = get_available_select_clause(
        columns,
        [
            ("chapter_no", "chapter_no"),
            ("timeline_mark", "timeline_mark"),
            ("history_date_label", "history_date_label"),
            ("written_summary", "written_summary"),
            ("next_hook", "next_hook"),
            ("key_assets_change", "key_assets_change"),
            ("stage_goal", "stage_goal"),
            ("chapter_target", "chapter_target"),
            ("status", "status"),
        ],
    )
    rows = conn.execute(
        f"""
        SELECT {select_clause}
        FROM chapters_nav
        WHERE chapter_no BETWEEN ? AND ?
        ORDER BY chapter_no
        """,
        (CHAPTER_START, CHAPTER_END),
    ).fetchall()
    conn.close()

    result = {}
    for row in rows:
        data = dict(row)
        timeline_mark = clean_text(data.get("timeline_mark") or data.get("history_date_label"))
        data["timeline_mark"] = timeline_mark
        result[int(data["chapter_no"])] = data
    return result


def load_chapter_files() -> dict[int, dict]:
    result = {}
    for chapter_no in range(CHAPTER_START, CHAPTER_END + 1):
        pattern = f"{chapter_slug(chapter_no)}*.md"
        matched = sorted(CHAPTER_DIR.glob(pattern))
        if not matched:
            result[chapter_no] = {"exists": False}
            continue

        path = matched[0]
        text = read_text(path)
        lines = text.splitlines()
        title_line = lines[0].strip() if lines else ""
        title = re.sub(r"^#\s*", "", title_line)
        title = re.sub(rf"^{chapter_slug(chapter_no)}\s*", "", title).strip()

        date_line = ""
        paragraphs = []
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith("【") and stripped.endswith("】") and not date_line:
                date_line = stripped
                continue
            if stripped:
                paragraphs.append(stripped)

        body_text = "\n".join(paragraphs)
        first_para = clean_text(paragraphs[0]) if paragraphs else ""
        last_para = clean_text(paragraphs[-1]) if paragraphs else ""
        result[chapter_no] = {
            "exists": True,
            "path": str(path),
            "title": title,
            "date_line": date_line,
            "char_count": len(re.sub(r"\s+", "", body_text)),
            "first_para": first_para[:120],
            "last_para": last_para[:120],
        }
    return result


def load_characters() -> list[dict]:
    conn = get_connection()
    columns = get_columns(conn, "entities_registry")
    rows = conn.execute("SELECT * FROM entities_registry ORDER BY importance_level DESC, name ASC").fetchall()
    conn.close()

    result = []
    for row in rows:
        data = dict(row)
        if clean_text(data.get("entity_type")) and clean_text(data.get("entity_type")) != "角色":
            continue
        entry = {
            "name": clean_text(data.get("name")),
            "importance_level": data.get("importance_level") or "",
            "role_type": clean_text(data.get("role_type")) if "role_type" in columns else "",
            "affiliation": clean_text(data.get("affiliation")) if "affiliation" in columns else "",
            "occupation": clean_text(data.get("occupation")) if "occupation" in columns else "",
            "current_status": clean_text(data.get("current_status")),
            "static_core": clean_text(data.get("static_core")),
            "last_update_chapter": data.get("last_update_chapter") or "",
            "aliases": parse_json_text(data.get("aliases_json"), []) if "aliases_json" in columns else [],
            "relationships": parse_json_text(data.get("relationships_json"), {}) if "relationships_json" in columns else {},
        }
        if entry["name"]:
            result.append(entry)
    return result


def load_assets() -> list[dict]:
    conn = get_connection()
    columns = get_columns(conn, "wealth_and_assets")
    rows = conn.execute("SELECT * FROM wealth_and_assets ORDER BY asset_type ASC, asset_name ASC").fetchall()
    conn.close()

    result = []
    for row in rows:
        data = dict(row)
        entry = {
            "asset_name": clean_text(data.get("asset_name")),
            "asset_type": clean_text(data.get("asset_type")),
            "asset_group": clean_text(data.get("asset_group")) if "asset_group" in columns else "",
            "current_value": clean_text(data.get("current_value")),
            "current_value_num": data.get("current_value_num") if "current_value_num" in columns else "",
            "current_value_text": clean_text(data.get("current_value_text")) if "current_value_text" in columns else "",
            "value_kind": clean_text(data.get("value_kind")) if "value_kind" in columns else "",
            "unit": clean_text(data.get("unit")) if "unit" in columns else "",
            "hidden_risk": clean_text(data.get("hidden_risk")),
            "last_update_chapter": data.get("last_update_chapter") or "",
        }
        if entry["asset_name"]:
            result.append(entry)
    return result


def build_chapter_fact_rows(single_map: dict, unit_map: dict, chapter_rows: dict, chapter_files: dict) -> list[dict]:
    result = []
    for chapter_no in range(CHAPTER_START, CHAPTER_END + 1):
        single = single_map.get(chapter_no, {})
        unit = unit_map.get(chapter_no, {})
        row = chapter_rows.get(chapter_no, {})
        file_data = chapter_files.get(chapter_no, {"exists": False})
        fact = {
            "chapter_no": chapter_no,
            "chapter_key": chapter_slug(chapter_no),
            "outline_title": clean_text(single.get("outline_title")),
            "source_file": clean_text(single.get("source_file")),
            "unit_source_file": clean_text(unit.get("source_file")),
            "正文标题": clean_text(file_data.get("title")),
            "时间标签": clean_text(file_data.get("date_line") or row.get("timeline_mark")),
            "剧情功能": clean_text(unit.get("剧情功能")),
            "单元范围": clean_text(unit.get("range_text")),
            "核心事件": clean_text(single.get("核心事件") or unit.get("概要") or row.get("chapter_target")),
            "推动剧情点": clean_text(single.get("推动剧情点") or row.get("stage_goal")),
            "章末悬念": clean_text(single.get("章末悬念") or row.get("next_hook")),
            "数据库摘要": clean_text(row.get("written_summary")),
            "资产变化": clean_text(row.get("key_assets_change")),
            "正文首段锚点": clean_text(file_data.get("first_para")),
            "正文尾段锚点": clean_text(file_data.get("last_para")),
            "正文状态": "已落稿" if file_data.get("exists") else "缺正文",
            "字数估算": file_data.get("char_count") or 0,
            "已知风险": KNOWN_ISSUES.get(chapter_no, []),
            "outline_missing": not bool(single),
        }
        result.append(fact)
    return result


def extract_location(time_label: str) -> str:
    label = clean_text(time_label).strip("【】")
    if not label:
        return ""
    comma_parts = re.split(r"[，,]", label)
    if len(comma_parts) > 1:
        return clean_text(comma_parts[-1])
    if "·" in label:
        return clean_text(label.split("·")[-1])
    return ""


def limit_text(value: str, size: int = 70) -> str:
    text = clean_text(value)
    return text if len(text) <= size else text[: size - 1] + "…"


def sentence_text(value: str, size: int = 70) -> str:
    text = limit_text(value, size).rstrip("。！？；，、 ")
    return text


def build_character_update_text(fact: dict) -> str:
    pieces = []
    core = clean_text(fact.get("核心事件"))
    push = clean_text(fact.get("推动剧情点"))
    hook = clean_text(fact.get("章末悬念"))
    if core:
        pieces.append(f"角色关系变动锚点：{sentence_text(core, 48)}。")
    if push:
        pieces.append(f"本章推进结果：{sentence_text(push, 40)}。")
    if hook and hook != push:
        pieces.append(f"章末压力落点：{sentence_text(hook, 40)}。")
    return "".join(pieces) or "以本章核心事件推动主角、心腹与对手关系变化。"


def build_revealed_information_text(fact: dict) -> str:
    chapter_no = fact["chapter_no"]
    exposure_items = CHAPTER_EXPOSURE_MAP.get(chapter_no, [])
    if exposure_items:
        return "；".join(exposure_items)
    core = clean_text(fact.get("核心事件"))
    push = clean_text(fact.get("推动剧情点"))
    hook = clean_text(fact.get("章末悬念"))
    parts = []
    if core:
        parts.append(f"读者本章可确认：{sentence_text(core, 48)}")
    if push:
        parts.append(f"阶段作用：{sentence_text(push, 36)}")
    elif hook:
        parts.append(f"尾钩暴露点：{sentence_text(hook, 36)}")
    return "；".join(parts) if parts else "待补"


def build_rewrite_risks(fact: dict) -> str:
    risks = list(fact.get("已知风险") or [])
    if not risks:
        return "避免抄旧正文原句；避免现代黑话；避免总结式收尾。"
    trimmed = risks[:2]
    if len(risks) > 2:
        trimmed.append("其余风险见错误样本表对照回避。")
    return "；".join(trimmed)


def build_keep_levels(fact: dict, next_core: str) -> dict:
    must_keep = [fact["核心事件"] or fact["数据库摘要"] or "待补"]
    if fact["章末悬念"]:
        must_keep.append(f"结尾必须保留钩子：{fact['章末悬念']}")
    cause_effect = (
        f"因上一章尾钩与本章压力汇流，主角转入“{limit_text(fact['核心事件'], 42)}”；"
        f"结果形成“{limit_text(fact['章末悬念'] or fact['推动剧情点'], 42)}”的新承接。"
    )
    level_a = "；".join(must_keep)
    level_b = cause_effect
    level_c = "丢弃现代黑话、作者总结句、上帝视角心理判词和越章兑现内容。"
    if fact["已知风险"]:
        level_c = "；".join(fact["已知风险"][:2]) + "；其余作者说明式废话可直接丢弃。"
    if next_core:
        level_b += f" 下一章才应兑现：{limit_text(next_core, 42)}。"
    return {"A": level_a, "B": level_b, "C": level_c}


def build_unit_core_conflict(group: list[dict]) -> str:
    chapter_function = clean_text(group[0].get("chapter_function"))
    if "皇权试探" in chapter_function:
        return "父权内查已经启动，主角既要护住生意账面与真实用途，也要把自己钉死在“贪财但无异心”的安全人设里。"
    if "第一桶金" in chapter_function:
        return "京城销路已经打开，主角要把香皂从偏院小作坊推成稳定生意，同时压住货源、洗钱、跟踪和外部合作反噬。"
    if "开局" in chapter_function or "铺垫" in chapter_function:
        return "偏院开局极险，主角必须一边搭起作坊与护卫利益网，一边把朝廷暗线和王府巡查挡在门外。"
    return "本组章节围绕经营推进与风险升级同步展开，主角必须扩张收益，同时守住信息与节奏边界。"


def build_unit_progression(group: list[dict]) -> str:
    return " / ".join(
        f"{item['chapter_no']:03d}《{item['title']}》:{limit_text(item['core_event'], 18)}"
        for item in group
    )


def build_unit_midpoint_turn(group: list[dict]) -> str:
    midpoint = group[len(group) // 2]
    turn_anchor = midpoint["end_hook"] or midpoint["push_point"] or midpoint["core_event"] or "待补"
    return f"第{midpoint['chapter_no']:03d}章形成段中转折：{limit_text(turn_anchor, 40)}"


def build_chapter_structured_rows(chapter_facts: list[dict]) -> list[dict]:
    rows = []
    fact_map = {item["chapter_no"]: item for item in chapter_facts}
    for fact in chapter_facts:
        next_fact = fact_map.get(fact["chapter_no"] + 1, {})
        next_core = clean_text(next_fact.get("核心事件"))
        keep_levels = build_keep_levels(fact, next_core)
        rows.append(
            {
                "chapter_no": fact["chapter_no"],
                "title": fact["正文标题"] or fact["outline_title"] or "待补标题",
                "timeline_mark": fact["时间标签"] or "待补",
                "location": extract_location(fact["时间标签"]),
                "chapter_function": fact["剧情功能"] or "待补",
                "core_event": fact["核心事件"] or "待补",
                "push_point": fact["推动剧情点"] or "待补",
                "must_keep_events": keep_levels["A"],
                "cause_effect_chain": keep_levels["B"],
                "character_updates": build_character_update_text(fact),
                "assets_updates": fact["资产变化"] or "无明确数值更新，按经营线压力保留产能/原料/银钱变化方向。",
                "revealed_information": build_revealed_information_text(fact),
                "end_hook": fact["章末悬念"] or "待补",
                "rewrite_risks": build_rewrite_risks(fact),
                "do_not_advance": DO_NOT_ADVANCE.get(
                    fact["chapter_no"],
                    f"下一章才应展开：{next_core}" if next_core else "不得越章抢跑后续任务。",
                ),
                "retain_value": keep_levels,
            }
        )
    return rows


def chunk_facts_by_five(structured_rows: list[dict]) -> list[list[dict]]:
    return [structured_rows[idx : idx + 5] for idx in range(0, len(structured_rows), 5)]


def build_asset_state_rows(chapter_facts: list[dict], assets: list[dict]) -> list[dict]:
    asset_map = {item["asset_name"]: item for item in assets}
    silver = asset_map.get("silver_taels", {}).get("current_value", "待核")
    waste_oil = asset_map.get("waste_oil_jin", {}).get("current_value", "待核")
    return [
        {
            "item": "现银规模",
            "current_state": f"账面现银约 {silver} 两，已从偏院穷境跃迁到可撬动外部合作。",
            "first_lock": "第020章",
            "latest_confirm": "第022章",
            "notes": "五万两定金已成核心压力源，后续重写必须承接它引发的父权内查。",
        },
        {
            "item": "废油来源",
            "current_state": f"偏院自采已不够用，外部主来源锁到赵一刀屠宰场，当前快照约 {waste_oil} 斤。",
            "first_lock": "第018章",
            "latest_confirm": "第022章",
            "notes": "要保留‘原料端被外部合作控制’这一经营风险。",
        },
        {
            "item": "产能上限",
            "current_state": "偏院单点产能不足，需借屠宰场做粗加工，目标至少支撑教坊司月供五百块。",
            "first_lock": "第019章",
            "latest_confirm": "第022章",
            "notes": "不能把产能写成无限增长，否则经营线会穿帮。",
        },
        {
            "item": "契约对象",
            "current_state": "核心外部契约有两条：赵一刀原料/粗加工链，凤娇娇独家高端销路链。",
            "first_lock": "第019-020章",
            "latest_confirm": "第022章",
            "notes": "两条线都必须回写到后续生意与风险结构里。",
        },
        {
            "item": "定金性质",
            "current_state": "教坊司独家供货定金五万两，本质是预付买断与垄断押金，不是无条件白送。",
            "first_lock": "第020章",
            "latest_confirm": "第020章",
            "notes": "后续若供货失约或改口，必须考虑契约反噬。",
        },
        {
            "item": "假账/阴阳账本",
            "current_state": "旧正文第022章已提前写出伪账思路，但更稳妥的事实层应只保留‘主角准备伪装账面用途’。",
            "first_lock": "第022章",
            "latest_confirm": "第022章",
            "notes": "重写时只能写准备与试探，不能一步写完整套账本落地。",
        },
        {
            "item": "是否已开始军工采购",
            "current_state": f"{chapter_scope_slug()}不应算正式启动，只能算主角内心已意识到银子未来可转成战争准备。",
            "first_lock": "高风险抢跑点见第020章",
            "latest_confirm": "第022章",
            "notes": "凡是硝石、硫磺、火药采购闭环都属于后续章任务，当前章不能写穿。",
        },
    ]


def render_target_chapter_facts(structured_rows: list[dict]) -> str:
    lines = [
        f"# 章节事实卡 {chapter_range_slug()}",
        "",
        "## 冻结原则",
        "- 章节任务源：`SPEC/04_分卷细纲`。",
        "- 状态源：`novel_ledger.db`、角色表、资产表。",
        "- 旧正文只作为补充核对源，不作为唯一事实源。",
        "",
    ]
    for row in structured_rows:
        lines.extend(
            [
                f"## 第{row['chapter_no']:03d}章",
                f"- chapter_no: {row['chapter_no']:03d}",
                f"- title: {row['title']}",
                f"- timeline_mark: {row['timeline_mark']}",
                f"- location: {row['location'] or '待补'}",
                f"- chapter_function: {row['chapter_function']}",
                f"- must_keep_events: {row['must_keep_events']}",
                f"- cause_effect_chain: {row['cause_effect_chain']}",
                f"- character_updates: {row['character_updates']}",
                f"- assets_updates: {row['assets_updates']}",
                f"- revealed_information: {row['revealed_information']}",
                f"- end_hook: {row['end_hook']}",
                f"- rewrite_risks: {row['rewrite_risks']}",
                f"- do_not_advance: {row['do_not_advance']}",
                f"- retain_value_A: {row['retain_value']['A']}",
                f"- retain_value_B: {row['retain_value']['B']}",
                f"- retain_value_C: {row['retain_value']['C']}",
                "",
            ]
        )
    return "\n".join(lines)


def render_target_unit_cards(structured_rows: list[dict]) -> str:
    groups = chunk_facts_by_five(structured_rows)
    lines = [
        f"# 单元连续性卡 {chapter_range_slug()}",
        "",
        "按每 5 章一组切分，保留清正文后的主筋骨。",
        "",
    ]
    for group in groups:
        start_no = group[0]["chapter_no"]
        end_no = group[-1]["chapter_no"]
        lines.extend(
            [
                f"## {start_no:03d}-{end_no:03d}",
                f"- unit_range: {start_no:03d}-{end_no:03d}",
                f"- unit_core_conflict: {build_unit_core_conflict(group)}",
                f"- chapters_progression: {build_unit_progression(group)}",
                f"- midpoint_turn: {build_unit_midpoint_turn(group)}",
                f"- current_pressure: {group[-1]['end_hook']}",
                f"- next_required_payoff: {group[-1]['do_not_advance']}",
                "",
            ]
        )
    return "\n".join(lines)


def render_target_character_snapshot() -> str:
    lines = [
        f"# 角色状态快照 {chapter_scope_slug()}",
        "",
        "只记当前状态，不回写完整小传。",
        "",
    ]
    for row in ROLE_SNAPSHOT_ROWS:
        lines.extend(
            [
                f"## {row['name']}",
                f"- 外在人设/表面对外状态: {row['public_persona']}",
                f"- 真实目标/实际怀疑对象: {row['real_goal']}",
                f"- 当前风险/已采取动作: {row['current_risk']}",
                f"- 已被谁盯上: {row['watched_by']}",
                "",
            ]
        )
    return "\n".join(lines)


def render_target_asset_snapshot(chapter_facts: list[dict], assets: list[dict]) -> str:
    rows = build_asset_state_rows(chapter_facts, assets)
    lines = [
        f"# 资产经营状态快照 {chapter_scope_slug()}",
        "",
        "| 项目 | 当前状态 | 首次锁定章节 | 最近确认章节 | 备注 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_cell(row["item"]),
                    escape_cell(row["current_state"]),
                    escape_cell(row["first_lock"]),
                    escape_cell(row["latest_confirm"]),
                    escape_cell(row["notes"]),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def render_target_exposed_info() -> str:
    lines = [
        f"# 已曝光信息表 {chapter_scope_slug()}",
        "",
        "| 信息内容 | 知情人 | 知道深度 | 首次曝光章 |",
        "| --- | --- | --- | --- |",
    ]
    for info, knowers, depth, chapter_no in INFO_EXPOSURE_ROWS:
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_cell(info),
                    escape_cell(knowers),
                    escape_cell(depth),
                    escape_cell(f"第{chapter_no:03d}章"),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def render_target_outline_audit(chapter_facts: list[dict]) -> str:
    outlined = [item["chapter_no"] for item in chapter_facts if not item["outline_missing"]]
    missing = [item["chapter_no"] for item in chapter_facts if item["outline_missing"]]
    single_sources = sorted({item["source_file"] for item in chapter_facts if item.get("source_file")})
    unit_sources = sorted({item["unit_source_file"] for item in chapter_facts if item.get("unit_source_file")})
    lines = [
        f"# 细纲来源审计 {chapter_range_slug()}",
        "",
        f"- 有效覆盖章节数：{len(outlined)}",
        f"- 未覆盖章节数：{len(missing)}",
        f"- 单章细纲来源文件数：{len(single_sources)}",
        f"- 单元细纲来源文件数：{len(unit_sources)}",
        f"- 已匹配章节：{', '.join(f'{item:03d}' for item in outlined) if outlined else '无'}",
        f"- 未匹配章节：{', '.join(f'{item:03d}' for item in missing) if missing else '无'}",
        "",
        "## 来源规则",
        "- 本审计按细纲正文块中的真实章节号建立映射，不按文件名前缀推断章号。",
        "- 扫描范围为 `SPEC/04_分卷细纲` 下全部卷目录，而非只锁定 `第一卷`。",
        "- 卷目录、片段编号、文件序号仅作为定位路径，不作为章节事实本身。",
        "",
        "## 单章细纲来源文件",
    ]
    for source in single_sources:
        lines.append(f"- {source}")
    lines.extend(
        [
            "",
            "## 单元细纲来源文件",
        ]
    )
    for source in unit_sources:
        lines.append(f"- {source}")
    lines.extend(
        [
            "",
            "## 逐章来源",
        ]
    )
    for fact in chapter_facts:
        lines.append(
            f"- 第{fact['chapter_no']:03d}章：单章细纲=`{fact.get('source_file') or '无'}`；单元细纲=`{fact.get('unit_source_file') or '无'}`"
        )
    lines.extend(
        [
            "",
            "## 使用说明",
            "- 本表只报告细纲来源与覆盖情况，不改动任何细纲源文件。",
            "- 若章节未匹配单章细纲，后续写作或复盘应显式回退到单元细纲与事实卡联合约束。",
            "",
        ]
    )
    return "\n".join(lines)


def render_target_error_samples() -> str:
    lines = [
        "# 旧正文错误样本表",
        "",
        "本表只截取最小错误片段用于避坑，不保存旧正文原句作为重写参考重点。",
        "",
    ]
    for title, items in ERROR_SAMPLE_SECTIONS.items():
        lines.append(f"## {title}")
        for chapter_label, sample, note in items:
            lines.append(f"- {chapter_label}：`{sample}` -> {note}")
        lines.append("")
    lines.extend(
        [
            "## 使用规则",
            "- 重写时只把这些例子当负面样本，不回抄原句。",
            "- 如遇章节功能与语感冲突，优先保功能，不保旧表达。",
            "- 任何涉及下一章任务的内容，先查 `章节事实卡` 的 `do_not_advance` 字段。",
            "",
        ]
    )
    return "\n".join(lines)


def render_readme(chapter_facts: list[dict], characters: list[dict], assets: list[dict]) -> str:
    drafted = sum(1 for item in chapter_facts if item["正文状态"] == "已落稿")
    outlined = sum(1 for item in chapter_facts if not item["outline_missing"])
    return "\n".join(
        [
            "# 正文清理前参考包",
            "",
            "本目录用于在大规模清理 `chapter/` 正文前保留可重建的剧情骨架与状态快照。",
            "",
            "## 覆盖范围",
            f"- 章节范围：第{CHAPTER_START:03d}章至第{CHAPTER_END:03d}章",
            f"- 已有正文：{drafted} 章",
            f"- 已有单章细纲：{outlined} 章",
            f"- 细纲扫描根目录：`SPEC/04_分卷细纲`",
            f"- 角色快照：{len(characters)} 条",
            f"- 资产快照：{len(assets)} 条",
            "",
            "## 文件说明",
            "- `01_章节事实卡.md`：逐章保留时间、事件、悬念、摘要、尾钩和正文锚点。",
            "- `02_单元承接卡.md`：按单元梳理主线任务、阶段功能与跨章承接。",
            "- `03_角色状态快照.md`：清理正文前可直接回读的人物底色与最近状态。",
            "- `04_资产经营快照.md`：资金、原料、成品、人员等经营状态快照。",
            "- `05_已曝光信息表.md`：按章记录读者已知信息和后续必须承接的暗线。",
            "- `06_错误样本表.md`：已发现的正文风险点与重写避坑说明。",
            f"- `temp/细纲来源审计_{chapter_range_slug()}.md`：标记参考包实际使用的单章细纲与单元细纲来源路径。",
            "- `reference_index.json`：机器可读索引，便于后续脚本或人工检索。",
            "",
        ]
    )


def render_chapter_fact_cards(chapter_facts: list[dict]) -> str:
    lines = ["# 章节事实卡", ""]
    for fact in chapter_facts:
        lines.extend(
            [
                f"## {fact['chapter_key']} {fact['正文标题'] or fact['outline_title'] or '待补标题'}",
                f"- 时间标签：{fact['时间标签'] or '待补'}",
                f"- 单元范围：{fact['单元范围'] or '待补'}",
                f"- 剧情功能：{fact['剧情功能'] or '待补'}",
                f"- 细纲核心事件：{fact['核心事件'] or '待补'}",
                f"- 细纲推动点：{fact['推动剧情点'] or '待补'}",
                f"- 章末悬念：{fact['章末悬念'] or '待补'}",
                f"- 单章细纲来源：{fact['source_file'] or '待补'}",
                f"- 单元细纲来源：{fact['unit_source_file'] or '待补'}",
                f"- 数据库摘要：{fact['数据库摘要'] or '待补'}",
                f"- 资产变化：{fact['资产变化'] or '无'}",
                f"- 正文状态：{fact['正文状态']} / 约 {fact['字数估算']} 字",
                f"- 正文首段锚点：{fact['正文首段锚点'] or '无'}",
                f"- 正文尾段锚点：{fact['正文尾段锚点'] or '无'}",
                f"- 单章细纲缺口：{'是' if fact['outline_missing'] else '否'}",
            ]
        )
        if fact["已知风险"]:
            lines.append("- 已知风险：")
            for issue in fact["已知风险"]:
                lines.append(f"  - {issue}")
        lines.append("")
    return "\n".join(lines)


def render_unit_continuity_cards(chapter_facts: list[dict], unit_map: dict) -> str:
    grouped = {}
    for fact in chapter_facts:
        unit_key = fact["单元范围"] or "未匹配单元"
        grouped.setdefault(unit_key, []).append(fact)

    lines = ["# 单元承接卡", ""]
    for unit_key, facts in grouped.items():
        anchor = unit_map.get(facts[0]["chapter_no"], {})
        lines.extend(
            [
                f"## 单元 {unit_key}",
                f"- 片段编号：{anchor.get('segment_name', '待补')}",
                f"- 剧情功能：{anchor.get('剧情功能', '待补')}",
                f"- 单元概要：{anchor.get('概要', '待补')}",
                f"- 单元小高潮：{anchor.get('小高潮', '待补')}",
                f"- 当前覆盖章节：{facts[0]['chapter_key']} 至 {facts[-1]['chapter_key']}",
                "- 跨章承接：",
            ]
        )
        for fact in facts:
            lines.append(
                f"  - {fact['chapter_key']}：{fact['核心事件'] or '待补'}；尾钩：{fact['章末悬念'] or '待补'}"
            )
        lines.append("")
    return "\n".join(lines)


def render_character_snapshot(characters: list[dict]) -> str:
    lines = [
        "# 角色状态快照",
        "",
        "| 角色 | 重要度 | 身份 | 阵营 | 当前状态 | 静态底色 | 最近更新章 | 别名 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in characters:
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_cell(item["name"]),
                    escape_cell(item["importance_level"]),
                    escape_cell(item["role_type"] or item["occupation"]),
                    escape_cell(item["affiliation"]),
                    escape_cell(item["current_status"]),
                    escape_cell(item["static_core"]),
                    escape_cell(item["last_update_chapter"]),
                    escape_cell("、".join(item["aliases"])),
                ]
            )
            + " |"
        )
    lines.extend(["", "## 关系备注", ""])
    for item in characters:
        if item["relationships"]:
            relation_text = "；".join(f"{k}:{v}" for k, v in item["relationships"].items())
            lines.append(f"- {item['name']}：{relation_text}")
    lines.append("")
    return "\n".join(lines)


def render_asset_snapshot(assets: list[dict]) -> str:
    lines = [
        "# 资产经营快照",
        "",
        "| 资产 | 类型 | 分组 | 当前值 | 数值栏 | 文本栏 | 单位 | 最近更新章 | 风险 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in assets:
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_cell(item["asset_name"]),
                    escape_cell(item["asset_type"]),
                    escape_cell(item["asset_group"]),
                    escape_cell(item["current_value"]),
                    escape_cell(item["current_value_num"]),
                    escape_cell(item["current_value_text"]),
                    escape_cell(item["unit"]),
                    escape_cell(item["last_update_chapter"]),
                    escape_cell(item["hidden_risk"]),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def render_exposed_information() -> str:
    lines = [
        "# 已曝光信息表",
        "",
        "| 信息内容 | 知情人 | 知道深度 | 首次曝光章 |",
        "| --- | --- | --- | --- |",
    ]
    for info, knowers, depth, chapter_no in INFO_EXPOSURE_ROWS:
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_cell(info),
                    escape_cell(knowers),
                    escape_cell(depth),
                    escape_cell(f"第{chapter_no:03d}章"),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def render_error_samples() -> str:
    lines = [
        "# 错误样本表",
        "",
        "## 已确认问题",
        "",
    ]
    for chapter_no, issues in sorted(KNOWN_ISSUES.items()):
        lines.append(f"### {chapter_slug(chapter_no)}")
        for issue in issues:
            lines.append(f"- {issue}")
        lines.append("")
    lines.extend(
        [
            "## 重写防回潮约束",
            "",
            "- 只写本章该承担的信息量，不得把下章确认、摊牌、主动出击提前写完。",
            "- 历史语感优先，避免“上牌桌资格”“终极试探”“资金流”等现代抽象话术硬塞进角色内心。",
            "- 试探戏保留灰度，不要让配角和主角在同章内把彼此底牌完全看穿。",
            "- 安保、情报、父子权力结构要前后一致，不能一会儿铁桶一会儿筛子。",
            "- 优先保留动作、对话、结果，减少作者说明式解释。",
            "",
        ]
    )
    return "\n".join(lines)


def build_reference_index(chapter_facts: list[dict], characters: list[dict], assets: list[dict]) -> dict:
    return {
        "scope": {
            "chapter_start": CHAPTER_START,
            "chapter_end": CHAPTER_END,
            "chapter_range": chapter_range_slug(),
        },
        "chapters": chapter_facts,
        "characters": characters,
        "assets": assets,
        "known_issues": KNOWN_ISSUES,
        "outline_root": str(OUTLINE_ROOT),
    }


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    global CHAPTER_START, CHAPTER_END
    args = parse_args()
    CHAPTER_START = args.start
    CHAPTER_END = args.end
    if CHAPTER_START > CHAPTER_END:
        raise ValueError("start 不能大于 end")
    target_files = build_target_files()
    single_map = parse_single_outline_map()
    unit_map = parse_unit_outline_map()
    chapter_rows = load_chapter_rows()
    chapter_files = load_chapter_files()
    characters = load_characters()
    assets = load_assets()
    chapter_facts = build_chapter_fact_rows(single_map, unit_map, chapter_rows, chapter_files)
    structured_rows = build_chapter_structured_rows(chapter_facts)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_text(OUTPUT_DIR / "README.md", render_readme(chapter_facts, characters, assets))
    write_text(OUTPUT_DIR / "01_章节事实卡.md", render_chapter_fact_cards(chapter_facts))
    write_text(OUTPUT_DIR / "02_单元承接卡.md", render_unit_continuity_cards(chapter_facts, unit_map))
    write_text(OUTPUT_DIR / "03_角色状态快照.md", render_character_snapshot(characters))
    write_text(OUTPUT_DIR / "04_资产经营快照.md", render_asset_snapshot(assets))
    write_text(OUTPUT_DIR / "05_已曝光信息表.md", render_exposed_information())
    write_text(OUTPUT_DIR / "06_错误样本表.md", render_error_samples())
    (OUTPUT_DIR / "reference_index.json").write_text(
        json.dumps(build_reference_index(chapter_facts, characters, assets), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_text(target_files["chapter_facts"], render_target_chapter_facts(structured_rows))
    write_text(target_files["unit_cards"], render_target_unit_cards(structured_rows))
    write_text(target_files["character_snapshot"], render_target_character_snapshot())
    write_text(target_files["asset_snapshot"], render_target_asset_snapshot(chapter_facts, assets))
    write_text(target_files["exposed_info"], render_target_exposed_info())
    write_text(target_files["error_samples"], render_target_error_samples())
    write_text(target_files["outline_audit"], render_target_outline_audit(chapter_facts))

    drafted = sum(1 for item in chapter_facts if item["正文状态"] == "已落稿")
    outlined = sum(1 for item in chapter_facts if not item["outline_missing"])
    print(f"[OK] reference pack ready: {OUTPUT_DIR}")
    print(f"[OK] target files ready: {TEMP_DIR}")
    print(f"[OK] chapters covered: {chapter_range_slug()}")
    print(f"[OK] drafted chapters: {drafted}")
    print(f"[OK] single outlines found: {outlined}")
    print(f"[OK] characters: {len(characters)}")
    print(f"[OK] assets: {len(assets)}")


if __name__ == "__main__":
    main()
