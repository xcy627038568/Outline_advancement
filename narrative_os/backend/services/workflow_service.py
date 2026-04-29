import json
import re
import subprocess
import sys
from pathlib import Path

from db.database import CHAPTER_DIR, PROJECT_ROOT, get_db
from services import chapter_service

LOCAL_GENERATOR_DIR = PROJECT_ROOT / "local_generator"
if str(LOCAL_GENERATOR_DIR) not in sys.path:
    sys.path.insert(0, str(LOCAL_GENERATOR_DIR))

from local_generator.build_ai_target_context import find_volume_dir_by_chapter
from local_generator.read_assets_db import get_assets_db
from local_generator.read_character_db import extract_character_db
from local_generator.read_recent_chapters import get_chapter_metadata

TEMP_DIR = PROJECT_ROOT / "temp"
PREVIEW_DIR = PROJECT_ROOT / "temp" / "workflow_preview"
LEDGER_HISTORY_DIR = PROJECT_ROOT / "ledger" / "history"

ASSET_GROUP_LABELS = {
    "funds": "资金",
    "raw_materials": "原材料",
    "products": "成品",
    "personnel": "人力",
    "key_items": "关键资产",
    "contracts": "契约",
}

ASSET_FIELD_META = {
    "silver_taels": {"label": "银子", "unit": "两"},
    "treasure_notes": {"label": "银票", "unit": "张"},
    "gold_taels": {"label": "金子", "unit": "两"},
    "copper_coins": {"label": "铜钱", "unit": "文"},
    "grain_dan": {"label": "粮食", "unit": "石"},
    "flour_bags": {"label": "面粉", "unit": "袋"},
    "rice_bags": {"label": "米袋", "unit": "袋"},
    "salt_bags": {"label": "盐包", "unit": "袋"},
    "coal_carts": {"label": "煤车", "unit": "车"},
    "timber_logs": {"label": "木料", "unit": "根"},
    "iron_ingots": {"label": "铁锭", "unit": "块"},
    "cloth_bolts": {"label": "布匹", "unit": "匹"},
    "horses": {"label": "马匹", "unit": "匹"},
    "carts": {"label": "车架", "unit": "辆"},
    "guards": {"label": "护卫", "unit": "人"},
    "workers": {"label": "伙计", "unit": "人"},
    "craftsmen": {"label": "匠人", "unit": "人"},
    "apprentices": {"label": "学徒", "unit": "人"},
    "shops": {"label": "铺面", "unit": "间"},
    "warehouses": {"label": "仓库", "unit": "座"},
    "boats": {"label": "船只", "unit": "艘"},
    "letters_of_credit": {"label": "汇票", "unit": "张"},
    "debt_notes": {"label": "欠条", "unit": "张"},
    "slaughterhouse_contract": {"label": "屠宰场废油契约", "unit": ""},
    "teach_fang_contract": {"label": "教坊司香皂供货契约", "unit": ""},
    "bookkeepers": {"label": "账房", "unit": "人"},
    "core_guards": {"label": "核心护卫", "unit": "人"},
    "dead_pact_maids": {"label": "死契丫鬟", "unit": "人"},
    "alcohol_jars": {"label": "酒坛", "unit": "坛"},
    "crude_gunpowder_jin": {"label": "粗火药", "unit": "斤"},
    "incendiary_bottles": {"label": "燃烧瓶", "unit": "瓶"},
    "luxury_soap_blocks": {"label": "高档香皂", "unit": "块"},
    "charcoal_jin": {"label": "木炭", "unit": "斤"},
    "plant_ash_jin": {"label": "草木灰", "unit": "斤"},
    "raw_iron_jin": {"label": "生铁", "unit": "斤"},
    "saltpeter_jin": {"label": "硝石", "unit": "斤"},
    "sulfur_jin": {"label": "硫磺", "unit": "斤"},
    "waste_oil_jin": {"label": "废油", "unit": "斤"},
}

FORBIDDEN_NARRATIVE_PHRASES = [
    "这说明",
    "这意味着",
    "换句话说",
    "铺垫",
    "试探位",
    "定调",
    "靶点",
    "小高潮",
    "大纲",
    "复盘",
]

AMBIGUOUS_FORBIDDEN_TITLES = {
    "王爷",
    "殿下",
    "陛下",
    "圣上",
    "燕王",
    "三爷",
}


def get_current_workflow():
    chapter_no = _get_current_chapter_no()
    if chapter_no is None:
        return None
    return get_workflow_by_chapter(chapter_no)


def get_workflow_by_chapter(
    chapter_no: int,
    chapter_text: str | None = None,
    requested_names: list[str] | None = None,
):
    chapter = chapter_service.get_chapter_by_no(chapter_no)
    if not chapter:
        return None

    outline = _get_chapter_outline(chapter_no)
    radar = _get_radar_context(chapter_no)
    recent_context = _get_recent_context(chapter_no)
    effective_chapter_text = chapter_text if chapter_text is not None else chapter.get("chapter_content", "")
    characters = _get_character_context(
        chapter_no,
        effective_chapter_text,
        outline["content"],
        radar["content"],
        requested_names or [],
    )
    assets = _get_asset_context(chapter_no)
    files = _get_workflow_files(chapter_no, chapter)
    ledger = _get_ledger_context(chapter_no, chapter)

    return {
        "chapter": chapter,
        "outline": outline,
        "radar": radar,
        "recent_context": recent_context,
        "characters": characters,
        "assets": assets,
        "files": files,
        "ledger": ledger,
    }


def get_character_context(chapter_no: int, chapter_text: str = "", requested_names: list[str] | None = None):
    chapter = chapter_service.get_chapter_by_no(chapter_no)
    if not chapter:
        return None

    outline = _get_chapter_outline(chapter_no)
    radar = _get_radar_context(chapter_no)
    effective_text = chapter_text if chapter_text is not None else chapter.get("chapter_content", "")
    return _get_character_context(
        chapter_no,
        effective_text,
        outline["content"],
        radar["content"],
        requested_names or [],
    )


def save_chapter_draft(chapter_no: int, title: str, content: str):
    _assert_write_prerequisites(chapter_no, action="保存正文")
    _assert_title_ready(chapter_no, title)
    _assert_chapter_content_ready(chapter_no, title, content)
    file_path = _resolve_chapter_file_path(chapter_no, title)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return {
        "path": str(file_path),
        "title": _extract_title_from_filename(file_path),
        "message": f"已保存正文到 {file_path.name}",
    }


def save_chapter_ledger(chapter_no: int, content: str):
    _assert_write_prerequisites(chapter_no, action="保存台账")
    _assert_ledger_ready(chapter_no, content)
    ledger_path = _get_ledger_file_path(chapter_no)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(content, encoding="utf-8")
    return {
        "path": str(ledger_path),
        "message": f"已保存台账到 {ledger_path.name}",
    }


def generate_radar(chapter_no: int):
    _assert_chapter_chain_ready(chapter_no, action="生成雷达")
    result = _run_local_generator_script(
        "build_ai_target_context.py",
        str(chapter_no),
    )
    success = result.returncode == 0
    error_message = ""
    if success:
        try:
            _assert_write_prerequisites(chapter_no, action="生成雷达")
        except RuntimeError as exc:
            success = False
            error_message = str(exc)

    return {
        "success": success,
        "stdout": result.stdout.strip(),
        "stderr": "\n".join(part for part in [result.stderr.strip(), error_message] if part).strip(),
        "returncode": result.returncode if success else (result.returncode or 1),
        "workflow": get_workflow_by_chapter(chapter_no),
    }


def finalize_chapter(chapter_no: int):
    _assert_write_prerequisites(chapter_no, action="执行闭环")
    ledger_path = _get_ledger_file_path(chapter_no)
    if not ledger_path.exists():
        raise RuntimeError(f"第{chapter_no:03d}章缺少台账文件 {ledger_path.name}，禁止执行闭环。")
    _assert_ledger_ready(chapter_no, ledger_path.read_text(encoding="utf-8"))
    result = _run_local_generator_script(
        "finalize_chapter_workflow.py",
        str(chapter_no),
    )

    return {
        "success": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
        "workflow": get_workflow_by_chapter(chapter_no),
    }


def _get_current_chapter_no():
    conn = get_db()
    cur = conn.cursor()
    pending_row = cur.execute(
        "SELECT chapter_no FROM chapters_nav WHERE status = 'pending' ORDER BY chapter_no LIMIT 1"
    ).fetchone()
    if pending_row:
        conn.close()
        return pending_row["chapter_no"]

    latest_written = cur.execute(
        "SELECT chapter_no FROM chapters_nav WHERE status = 'written' ORDER BY chapter_no DESC LIMIT 1"
    ).fetchone()
    if latest_written:
        conn.close()
        return latest_written["chapter_no"]

    first_row = cur.execute("SELECT chapter_no FROM chapters_nav ORDER BY chapter_no LIMIT 1").fetchone()
    conn.close()
    return first_row["chapter_no"] if first_row else None


def _get_chapter_outline(chapter_no: int):
    _, chapter_dict = find_volume_dir_by_chapter(chapter_no)
    title, content = chapter_dict.get(chapter_no, ("", "未找到当前章细纲。"))
    return {
        "title": title,
        "content": content,
    }


def _get_radar_context(chapter_no: int):
    radar_file = PREVIEW_DIR / f"ai_target_context_第{chapter_no:03d}章.md"
    exists = radar_file.exists()
    content = radar_file.read_text(encoding="utf-8") if exists else ""
    valid = False
    if exists and content.strip():
        try:
            _validate_radar_content(chapter_no, content)
            valid = True
        except RuntimeError:
            valid = False
    return {
        "path": str(radar_file),
        "exists": exists,
        "content": content,
        "valid": valid,
        "message": "" if valid else f"第{chapter_no:03d}章雷达缺失或为空，禁止继续正文、台账与闭环。",
    }


def _get_radar_file_path(chapter_no: int):
    return PREVIEW_DIR / f"ai_target_context_第{chapter_no:03d}章.md"


def _get_character_preview_file_path(chapter_no: int):
    return PREVIEW_DIR / f"character_context_第{chapter_no:03d}章.md"


def _get_assets_preview_file_path(chapter_no: int):
    return PREVIEW_DIR / f"assets_context_第{chapter_no:03d}章.md"


def _assert_write_prerequisites(chapter_no: int, action: str):
    _assert_chapter_chain_ready(chapter_no, action=action)
    _assert_recent_context_ready(chapter_no, action=action)
    _assert_radar_ready(chapter_no, action=action)
    _assert_character_context_ready(chapter_no, action=action)
    _assert_assets_context_ready(chapter_no, action=action)


def _assert_title_ready(chapter_no: int, title: str):
    cleaned = (title or "").strip()
    if not cleaned:
        raise RuntimeError(f"第{chapter_no:03d}章标题为空，禁止保存正文。")
    if cleaned.startswith("第"):
        raise RuntimeError(f"第{chapter_no:03d}章标题不应包含章节号前缀，请只传纯标题。")
    outline_title = (_get_chapter_outline(chapter_no).get("title") or "").strip()
    if outline_title and cleaned == outline_title:
        raise RuntimeError(f"第{chapter_no:03d}章标题与细纲标题完全相同，请改成可发布章名。")


def _assert_chapter_content_ready(chapter_no: int, title: str, content: str):
    text = str(content or "")
    if not text.strip():
        raise RuntimeError(f"第{chapter_no:03d}章正文为空，禁止保存。")
    chapter_heading_pattern = rf"^# 第0*{chapter_no}章\s+.+"
    if not re.search(chapter_heading_pattern, text, re.M):
        raise RuntimeError(f"第{chapter_no:03d}章正文缺少规范标题行。")
    if title.strip() and not re.search(rf"^# 第0*{chapter_no}章\s+{re.escape(title.strip())}$", text, re.M):
        raise RuntimeError(f"第{chapter_no:03d}章正文标题行与提交标题不一致。")
    date_line_pattern = r"【新历\d{4}年\d{1,2}月\d{1,2}日·旧历[一二三四五六七八九十正冬腊元〇零两初廿卅]+(?:月)?[一二三四五六七八九十正冬腊元〇零两初廿卅]*，[^】]+】"
    if not re.search(date_line_pattern, text):
        raise RuntimeError(f"第{chapter_no:03d}章正文缺少合规日期地点行。")
    forbidden_hits = [phrase for phrase in FORBIDDEN_NARRATIVE_PHRASES if phrase in text]
    if forbidden_hits:
        raise RuntimeError(f"第{chapter_no:03d}章正文出现禁用叙事词：{'、'.join(forbidden_hits)}")
    _assert_forbidden_titles_not_used(chapter_no, text)
    _assert_dialogue_title_rules(chapter_no, text)


def _assert_chapter_chain_ready(chapter_no: int, action: str):
    conn = get_db()
    cur = conn.cursor()
    current_row = cur.execute(
        "SELECT status FROM chapters_nav WHERE chapter_no = ?",
        (chapter_no,),
    ).fetchone()
    previous_row = None
    if chapter_no > 1:
        previous_row = cur.execute(
            "SELECT status FROM chapters_nav WHERE chapter_no = ?",
            (chapter_no - 1,),
        ).fetchone()
    conn.close()

    if not current_row:
        raise RuntimeError(f"主库中不存在第{chapter_no:03d}章记录，禁止{action}。")
    if current_row["status"] != "pending":
        raise RuntimeError(
            f"第{chapter_no:03d}章当前状态为 {current_row['status']}，不是 pending，禁止{action}。"
        )
    if chapter_no > 1:
        if not previous_row or previous_row["status"] != "written":
            prev_status = previous_row["status"] if previous_row else "缺失"
            raise RuntimeError(
                f"第{chapter_no - 1:03d}章当前状态为 {prev_status}，未形成稳定前情基线，禁止{action}。"
            )


def _assert_recent_context_ready(chapter_no: int, action: str):
    if chapter_no <= 1:
        return
    meta = get_chapter_metadata(chapter_no - 1)
    if not any((meta or {}).get(key) for key in ["timeline_mark", "written_summary", "next_hook", "key_assets_change"]):
        raise RuntimeError(
            f"第{chapter_no - 1:03d}章前情基线为空，无法可靠承接第{chapter_no:03d}章，禁止{action}。"
        )


def _assert_radar_ready(chapter_no: int, action: str):
    radar_file = _get_radar_file_path(chapter_no)
    if not radar_file.exists():
        raise RuntimeError(
            f"第{chapter_no:03d}章未生成雷达文件 {radar_file.name}，禁止{action}。请先执行 build_ai_target_context.py 或 build_and_read_target_radar。"
        )
    content = radar_file.read_text(encoding="utf-8")
    if not content.strip():
        raise RuntimeError(
            f"第{chapter_no:03d}章雷达文件 {radar_file.name} 为空，禁止{action}。请重新生成雷达后再继续。"
        )
    _validate_radar_content(chapter_no, content)


def _assert_character_context_ready(chapter_no: int, action: str):
    preview_file = _get_character_preview_file_path(chapter_no)
    if not preview_file.exists():
        raise RuntimeError(
            f"第{chapter_no:03d}章未生成角色上下文 {preview_file.name}，禁止{action}。请先执行 read_character_db.py。"
        )
    content = preview_file.read_text(encoding="utf-8")
    if not content.strip():
        raise RuntimeError(
            f"第{chapter_no:03d}章角色上下文 {preview_file.name} 为空，禁止{action}。"
        )
    _validate_character_content(chapter_no, content)


def _assert_assets_context_ready(chapter_no: int, action: str):
    preview_file = _get_assets_preview_file_path(chapter_no)
    if not preview_file.exists():
        raise RuntimeError(
            f"第{chapter_no:03d}章未生成资产上下文 {preview_file.name}，禁止{action}。请先执行 read_assets_db.py。"
        )
    content = preview_file.read_text(encoding="utf-8")
    if not content.strip():
        raise RuntimeError(
            f"第{chapter_no:03d}章资产上下文 {preview_file.name} 为空，禁止{action}。"
        )
    _validate_assets_content(chapter_no, content)


def _validate_radar_content(chapter_no: int, content: str):
    if not re.search(rf"# AI 单章战术突击靶点：第 {chapter_no} 章\b", content):
        raise RuntimeError(f"第{chapter_no:03d}章雷达标题与章节号不一致。")
    required_markers = [
        "## 2. 当前 5 章精细视野",
        "【▶ 本章必写任务 ◀】",
        "## 3. 章边界约束",
        "本章止步点：",
        "下一章禁止提前兑现项：",
    ]
    missing = [marker for marker in required_markers if marker not in content]
    if missing:
        raise RuntimeError(f"第{chapter_no:03d}章雷达缺少关键结构：{'、'.join(missing)}")
    if f"**第{chapter_no}章" not in content and f"**第{chapter_no}章：" not in content:
        raise RuntimeError(f"第{chapter_no:03d}章雷达未锁定当前章任务块。")


def _validate_character_content(chapter_no: int, content: str):
    if not re.search(rf"=== 第 {chapter_no:03d} 章 角色设定对齐上下文", content):
        raise RuntimeError(f"第{chapter_no:03d}章角色上下文标题与章节号不一致。")
    if "⚠️ 数据库中未找到角色" in content:
        raise RuntimeError(f"第{chapter_no:03d}章角色上下文存在未入库角色，禁止继续。")
    match = re.search(r"共找到\s+(\d+)\s+个角色记录", content)
    if not match or int(match.group(1)) <= 0:
        raise RuntimeError(f"第{chapter_no:03d}章角色上下文未找到有效角色记录。")


def _validate_assets_content(chapter_no: int, content: str):
    if not re.search(rf"=== 第 {chapter_no:03d} 章 大燕商行资产负债表 ===", content):
        raise RuntimeError(f"第{chapter_no:03d}章资产上下文标题与章节号不一致。")
    if "【当前资金】" not in content and "【核心契约与特殊资产】" not in content:
        raise RuntimeError(f"第{chapter_no:03d}章资产上下文缺少核心资产区块。")


def _assert_ledger_ready(chapter_no: int, content: str):
    payload = _extract_ledger_payload(content)
    if payload.get("chapter_no") != chapter_no:
        raise RuntimeError(f"台账中的 chapter_no={payload.get('chapter_no')} 与当前章节 {chapter_no} 不一致。")
    if not any(payload.get(key) for key in ["written_summary", "next_hook", "key_assets_change"]):
        raise RuntimeError(f"第{chapter_no:03d}章台账缺少摘要/钩子/资产变化，禁止继续。")

    character_updates = payload.get("character_updates") or {}
    if not isinstance(character_updates, dict):
        raise RuntimeError("台账中的 character_updates 必须为对象。")
    assets_updates = payload.get("assets_updates") or {}
    if not isinstance(assets_updates, dict):
        raise RuntimeError("台账中的 assets_updates 必须为对象。")

    chapter_file = _resolve_chapter_file_path(chapter_no, "")
    if not chapter_file.exists():
        raise RuntimeError(f"第{chapter_no:03d}章正文尚未保存，禁止写入台账。")
    chapter_text = chapter_file.read_text(encoding="utf-8")
    character_preview = _get_character_preview_file_path(chapter_no).read_text(encoding="utf-8")

    for name in character_updates.keys():
        if name not in chapter_text and name not in character_preview:
            raise RuntimeError(f"角色更新 `{name}` 未在正文或角色上下文中出现，疑似凭空捏造。")

    allowed_asset_groups = set(ASSET_GROUP_LABELS.keys())
    current_assets = get_assets_db(chapter_no)
    for group_name, items in assets_updates.items():
        if group_name not in allowed_asset_groups:
            raise RuntimeError(
                f"资产更新分组 `{group_name}` 非法。允许分组：{'、'.join(sorted(allowed_asset_groups))}。"
            )
        if not isinstance(items, dict):
            raise RuntimeError(f"资产更新分组 `{group_name}` 的内容必须为对象。")
        known_names = set((current_assets.get(group_name) or {}).keys())
        for item_key, change_val in items.items():
            if item_key not in known_names:
                note = change_val.get("note", "") if isinstance(change_val, dict) else ""
                if "新资产" not in note:
                    raise RuntimeError(
                        f"资产更新 `{group_name}.{item_key}` 未出现在当前资产上下文中；如属新资产，请在 note 中显式写明“新资产”。"
                    )


def _extract_ledger_payload(content: str):
    match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", content)
    if not match:
        raise RuntimeError("台账中未找到合法的 JSON 代码块。")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"台账 JSON 解析失败：{exc}")


def _assert_forbidden_titles_not_used(chapter_no: int, content: str):
    outline = _get_chapter_outline(chapter_no)
    radar = _get_radar_context(chapter_no)
    relevant_names, _ = _infer_relevant_character_names(content, outline.get("content", ""), radar.get("content", ""), [])
    db = extract_character_db(chapter_no)
    forbidden_hits = []
    for name in relevant_names:
        info = db.get(name) or {}
        title_info = info.get("effective_title") or {}
        for raw_title in title_info.get("forbidden_titles") or []:
            title = str(raw_title).strip()
            if not title or title in AMBIGUOUS_FORBIDDEN_TITLES:
                continue
            if title in content:
                forbidden_hits.append(f"{name}:{title}")
    if forbidden_hits:
        raise RuntimeError(
            f"第{chapter_no:03d}章正文出现高风险禁用称呼：{'、'.join(forbidden_hits)}"
        )


def _assert_dialogue_title_rules(chapter_no: int, content: str):
    db = extract_character_db(chapter_no)
    if not db:
        return

    speakers = [name for name in db.keys() if name]
    if not speakers:
        return

    speaker_pattern = "|".join(sorted((re.escape(name) for name in speakers), key=len, reverse=True))
    dialogue_pattern = re.compile(
        rf"(?P<speaker>{speaker_pattern})[^\n“”\"]{{0,16}}?(?:道|说道|说|问道|问|喝道|骂道|应道|回道|答道|低声道|轻声道|冷笑道|沉声道|厉声道|喊道|叫道)[：:，, ]*[“\"](?P<speech>[^”\"\n]{{1,120}})",
        re.M,
    )

    self_title_map = {}
    for name, info in db.items():
        title_info = info.get("effective_title") or {}
        self_title = str(title_info.get("self_title") or "").strip()
        if self_title:
            self_title_map.setdefault(self_title, set()).add(name)

    violations = []
    for match in dialogue_pattern.finditer(content):
        speaker = match.group("speaker")
        speech = match.group("speech")
        info = db.get(speaker) or {}
        title_info = info.get("effective_title") or {}
        expected_self = str(title_info.get("self_title") or "").strip()

        for self_title, owners in self_title_map.items():
            if not self_title or self_title not in speech:
                continue
            if speaker not in owners:
                violations.append(f"{speaker}自称误用`{self_title}`")

        scene_rules = title_info.get("scene_rules") or {}
        for scene_name, expected_title in scene_rules.items():
            if not scene_name.startswith("对"):
                continue
            target_name = scene_name[1:].strip()
            target_info = db.get(target_name) or {}
            target_title_info = target_info.get("effective_title") or {}
            candidate_titles = {
                str(target_title_info.get("formal_title") or "").strip(),
                str(target_title_info.get("common_title") or "").strip(),
                str(target_title_info.get("subordinate_title") or "").strip(),
                str(target_title_info.get("public_title") or "").strip(),
                str(target_title_info.get("narrative_label") or "").strip(),
            }
            candidate_titles = {title for title in candidate_titles if title}
            used_titles = [title for title in candidate_titles if title in speech]
            if used_titles and expected_title and expected_title not in used_titles:
                violations.append(f"{speaker}对{target_name}称呼误用`{'/'.join(used_titles)}`，应为`{expected_title}`")

    if violations:
        raise RuntimeError(
            f"第{chapter_no:03d}章正文出现高风险动态称谓错误：{'；'.join(violations[:5])}"
        )


def _get_recent_context(chapter_no: int):
    previous_chapter_no = max(chapter_no - 1, 0)
    if previous_chapter_no == 0:
        return {
            "chapter_no": 0,
            "timeline_mark": "",
            "written_summary": "",
            "next_hook": "",
            "key_assets_change": "",
        }
    meta = get_chapter_metadata(previous_chapter_no)
    return {
        "chapter_no": previous_chapter_no,
        "timeline_mark": _normalize_timeline_text(meta.get("timeline_mark", "")),
        "written_summary": meta.get("written_summary", ""),
        "next_hook": meta.get("next_hook", ""),
        "key_assets_change": meta.get("key_assets_change", ""),
    }


def _get_character_context(
    chapter_no: int,
    chapter_text: str,
    outline_text: str,
    radar_text: str,
    requested_names: list[str],
):
    db = extract_character_db(chapter_no)
    if not db:
        return {
            "names": [],
            "entries": [],
            "actual_names": [],
            "requested_names": [],
            "missing_names": requested_names or [],
            "fallback_names": [],
            "mode": "empty",
        }

    relevant_names, meta = _infer_relevant_character_names(chapter_text, outline_text, radar_text, requested_names)
    entries = []
    for name in relevant_names:
        info = db.get(name)
        if not info:
            continue
        entries.append(
            {
                "name": name,
                "role_type": info.get("role_type", ""),
                "occupation": info.get("occupation", ""),
                "personality": info.get("personality", ""),
                "status": info.get("status", ""),
                "history": info.get("history", []),
            }
        )
    return {
        "names": relevant_names,
        "entries": entries,
        "actual_names": meta["actual_names"],
        "requested_names": meta["requested_names"],
        "missing_names": meta["missing_names"],
        "fallback_names": meta["fallback_names"],
        "mode": meta["mode"],
    }


def _infer_relevant_character_names(
    chapter_text: str,
    outline_text: str,
    radar_text: str,
    requested_names: list[str],
):
    rows = _get_character_registry_rows()
    actual_names = _match_names_in_text(chapter_text, rows)
    normalized_requested = _normalize_requested_names(requested_names)
    requested_found = [name for name in normalized_requested if any(row["name"] == name for row in rows)]
    missing_names = [name for name in normalized_requested if name not in requested_found]

    fallback_names = []
    if not actual_names:
        fallback_names = _match_names_in_text("\n".join([outline_text or "", radar_text or ""]), rows)
        if not fallback_names:
            viewpoint_line = ""
            for line in (outline_text or "").splitlines():
                if line.startswith("- 视角："):
                    viewpoint_line = line.split("：", 1)[-1]
                    break

            if viewpoint_line:
                parts = [item.strip() for item in re.split(r"[\\/、,，]", viewpoint_line) if item.strip()]
                fallback_names = [name for name in parts if any(row["name"] == name for row in rows)]

    if actual_names:
        mode = "chapter"
    elif requested_found:
        mode = "requested"
    elif fallback_names:
        mode = "fallback"
    else:
        mode = "empty"

    merged_names = _dedupe_names(actual_names + requested_found + fallback_names)
    if not merged_names:
        merged_names = [row["name"] for row in rows[:5]]
        mode = "fallback"

    return merged_names[:8], {
        "actual_names": actual_names[:8],
        "requested_names": requested_found[:8],
        "missing_names": missing_names[:8],
        "fallback_names": fallback_names[:8],
        "mode": mode,
    }


def _get_character_registry_rows():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT name
        FROM entities_registry
        WHERE entity_type = '角色'
        ORDER BY importance_level DESC, name
        """
    ).fetchall()
    conn.close()
    return rows


def _match_names_in_text(text: str, rows):
    if not text:
        return []

    matched = []
    for row in rows:
        name = row["name"]
        if name and name in text:
            matched.append(name)
    return matched[:8]


def _normalize_requested_names(requested_names: list[str]):
    names = []
    for name in requested_names or []:
        for item in re.split(r"[\\/、,，\s]+", name or ""):
            item = item.strip()
            if item:
                names.append(item)
    return _dedupe_names(names)


def _dedupe_names(names: list[str]):
    seen = set()
    result = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result


def _get_asset_context(chapter_no: int):
    asset_map = get_assets_db(chapter_no)
    groups = []
    for group_name, values in asset_map.items():
        items = []
        for key, value in values.items():
            meta = _get_asset_meta(key)
            label = meta.get("label", key)
            unit = meta.get("unit", "")
            items.append(
                {
                    "name": key,
                    "label": label,
                    "value": value,
                    "unit": unit,
                    "display_value": _format_asset_display_value(value, unit),
                }
            )
        groups.append(
            {
                "group": group_name,
                "label": ASSET_GROUP_LABELS.get(group_name, group_name),
                "items": items,
            }
        )
    return {
        "groups": groups,
        "raw": asset_map,
    }


def _get_workflow_files(chapter_no: int, chapter: dict):
    chapter_file = _resolve_chapter_file_path(chapter_no, chapter.get("title", ""))
    ledger_file = _get_ledger_file_path(chapter_no)
    return {
        "chapter_path": str(chapter_file),
        "chapter_exists": chapter_file.exists(),
        "ledger_path": str(ledger_file),
        "ledger_exists": ledger_file.exists(),
    }


def _get_ledger_context(chapter_no: int, chapter: dict):
    ledger_path = _get_ledger_file_path(chapter_no)
    if ledger_path.exists():
        return {
            "path": str(ledger_path),
            "exists": True,
            "content": ledger_path.read_text(encoding="utf-8"),
        }

    archived_path = LEDGER_HISTORY_DIR / ledger_path.name
    if archived_path.exists():
        return {
            "path": str(archived_path),
            "exists": False,
            "content": archived_path.read_text(encoding="utf-8"),
            "archived": True,
        }

    return {
        "path": str(ledger_path),
        "exists": False,
        "content": _build_default_ledger_template(chapter_no, chapter),
        "archived": False,
    }


def _build_default_ledger_template(chapter_no: int, chapter: dict):
    timeline = _normalize_timeline_text(chapter.get("timeline_mark") or chapter.get("history_date_label") or "")
    summary = chapter.get("written_summary") or ""
    next_hook = chapter.get("next_hook") or ""
    key_assets_change = chapter.get("key_assets_change") or ""
    return (
        "## 章节更新\n"
        "```json\n"
        "{\n"
        f'  "chapter_no": {chapter_no},\n'
        f'  "timeline": "{_escape_json_string(timeline)}",\n'
        f'  "written_summary": "{_escape_json_string(summary)}",\n'
        f'  "next_hook": "{_escape_json_string(next_hook)}",\n'
        f'  "key_assets_change": "{_escape_json_string(key_assets_change)}",\n'
        '  "character_updates": {},\n'
        '  "assets_updates": {}\n'
        "}\n"
        "```"
    )


def _resolve_chapter_file_path(chapter_no: int, title: str):
    CHAPTER_DIR.mkdir(parents=True, exist_ok=True)
    existing_files = sorted(CHAPTER_DIR.glob(f"第{chapter_no:03d}章*.md"))
    if existing_files:
        return existing_files[0]

    safe_title = (title or "").strip() or "未命名章节"
    return CHAPTER_DIR / f"第{chapter_no:03d}章 {safe_title}.md"


def _get_ledger_file_path(chapter_no: int):
    return TEMP_DIR / f"update_chapter_{chapter_no:03d}.md"


def _extract_title_from_filename(file_path: Path):
    name = file_path.stem
    if " " in name:
        return name.split(" ", 1)[1]
    return ""


def _escape_json_string(value: str):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "")
        .replace("\n", "\\n")
    )


def _format_asset_display_value(value, unit: str):
    if value is None or value == "":
        return "-"
    if isinstance(value, (int, float)) and unit:
        return f"{value}{unit}"
    return str(value)


def _get_asset_meta(key: str):
    if key in ASSET_FIELD_META:
        return ASSET_FIELD_META[key]
    return {
        "label": _humanize_asset_key(key),
        "unit": _infer_asset_unit(key),
    }


def _humanize_asset_key(key: str):
    text = key.replace("_", " ").strip().lower()
    replacements = {
        "dead pact": "死契",
        "luxury soap": "高档香皂",
        "crude gunpowder": "粗火药",
        "teach fang": "教坊司",
        "plant ash": "草木灰",
        "raw iron": "生铁",
        "waste oil": "废油",
        "slaughterhouse": "屠宰场",
        "bookkeepers": "账房",
        "guards": "护卫",
        "maids": "丫鬟",
        "contract": "契约",
        "contracts": "契约",
        "charcoal": "木炭",
        "saltpeter": "硝石",
        "sulfur": "硫磺",
        "alcohol": "酒",
        "incendiary": "燃烧",
        "bottles": "瓶",
        "jars": "坛",
        "blocks": "块",
        "jin": "斤",
        "dan": "石",
        "core": "核心",
    }
    for source, target in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(source, target)
    text = re.sub(r"\s+", "", text)
    return text or key


def _infer_asset_unit(key: str):
    lowered = key.lower()
    if lowered.endswith("_jin"):
        return "斤"
    if lowered.endswith("_dan"):
        return "石"
    if lowered.endswith("_jars"):
        return "坛"
    if lowered.endswith("_bottles"):
        return "瓶"
    if lowered.endswith("_blocks"):
        return "块"
    if lowered.endswith("_maids") or lowered.endswith("_guards") or lowered.endswith("_workers") or lowered.endswith("_keepers"):
        return "人"
    return ""


def _normalize_timeline_text(value: str):
    text = str(value or "").strip()
    if not text:
        return ""
    return re.sub(
        r"(\d+)年([一二三四五六七八九十正冬腊元〇零]+)月",
        lambda match: f"{match.group(1)}年农历{match.group(2)}月",
        text,
    )


def _run_local_generator_script(script_name: str, *args: str, check: bool = False):
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "local_generator" / script_name), *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=False,
    )
    stdout = _decode_subprocess_output(completed.stdout)
    stderr = _decode_subprocess_output(completed.stderr)

    if check and completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode,
            completed.args,
            output=stdout,
            stderr=stderr,
        )

    return subprocess.CompletedProcess(
        completed.args,
        completed.returncode,
        stdout,
        stderr,
    )


def _decode_subprocess_output(output: bytes):
    for encoding in ("utf-8", "gbk", "cp936"):
        try:
            return output.decode(encoding)
        except UnicodeDecodeError:
            continue
    return output.decode("utf-8", errors="replace")
