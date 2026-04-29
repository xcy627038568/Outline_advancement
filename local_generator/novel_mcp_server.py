import json
import re
import subprocess
import sys
from pathlib import Path

from single_db_utils import get_connection
from read_assets_db import get_assets_db
from read_character_db import extract_character_db
from read_recent_chapters import get_chapter_metadata

# MCP 官方推荐高层封装库 (需运行 pip install mcp 安装)
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    try:
        from fastmcp import FastMCP
    except ImportError:
        print("⚠️ 未检测到 MCP 库。请先在终端执行: pip install mcp", file=sys.stderr)
        sys.exit(1)

# 初始化 MCP 服务器
mcp = FastMCP("大明老子是赵王_主笔智能体")

ROOT = Path(__file__).resolve().parent.parent

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


def _get_radar_file_path(chapter_no: int) -> Path:
    return ROOT / "temp" / "workflow_preview" / f"ai_target_context_第{chapter_no:03d}章.md"


def _get_character_file_path(chapter_no: int) -> Path:
    return ROOT / "temp" / "workflow_preview" / f"character_context_第{chapter_no:03d}章.md"


def _get_assets_file_path(chapter_no: int) -> Path:
    return ROOT / "temp" / "workflow_preview" / f"assets_context_第{chapter_no:03d}章.md"


def _assert_write_prerequisites(chapter_no: int, action: str):
    _assert_chapter_chain_ready(chapter_no, action)
    _assert_radar_ready(chapter_no, action)
    _assert_character_context_ready(chapter_no, action)
    _assert_assets_context_ready(chapter_no, action)


def _assert_chapter_chain_ready(chapter_no: int, action: str):
    conn = get_connection()
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
        raise ValueError(f"主库中不存在第{chapter_no:03d}章记录，禁止{action}。")
    if current_row["status"] != "pending":
        raise ValueError(f"第{chapter_no:03d}章当前状态为 {current_row['status']}，不是 pending，禁止{action}。")
    if chapter_no > 1 and (not previous_row or previous_row["status"] != "written"):
        prev_status = previous_row["status"] if previous_row else "缺失"
        raise ValueError(f"第{chapter_no - 1:03d}章当前状态为 {prev_status}，未形成稳定前情基线，禁止{action}。")


def _assert_radar_ready(chapter_no: int, action: str) -> Path:
    radar_file = _get_radar_file_path(chapter_no)
    if not radar_file.exists():
        raise FileNotFoundError(
            f"第{chapter_no:03d}章未生成雷达文件 {radar_file.name}，禁止{action}。请先调用 build_and_read_target_radar。"
        )
    content = radar_file.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(
            f"第{chapter_no:03d}章雷达文件 {radar_file.name} 为空，禁止{action}。请重新生成雷达后再继续。"
        )
    _validate_radar_content(chapter_no, content)
    return radar_file


def _assert_character_context_ready(chapter_no: int, action: str) -> Path:
    preview_file = _get_character_file_path(chapter_no)
    if not preview_file.exists():
        raise FileNotFoundError(
            f"第{chapter_no:03d}章未生成角色上下文 {preview_file.name}，禁止{action}。"
        )
    content = preview_file.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"第{chapter_no:03d}章角色上下文 {preview_file.name} 为空，禁止{action}。")
    if not re.search(rf"=== 第 {chapter_no:03d} 章 角色设定对齐上下文", content):
        raise ValueError(f"第{chapter_no:03d}章角色上下文标题与章节号不一致。")
    if "⚠️ 数据库中未找到角色" in content:
        raise ValueError(f"第{chapter_no:03d}章角色上下文存在未入库角色，禁止{action}。")
    return preview_file


def _assert_assets_context_ready(chapter_no: int, action: str) -> Path:
    preview_file = _get_assets_file_path(chapter_no)
    if not preview_file.exists():
        raise FileNotFoundError(
            f"第{chapter_no:03d}章未生成资产上下文 {preview_file.name}，禁止{action}。"
        )
    content = preview_file.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"第{chapter_no:03d}章资产上下文 {preview_file.name} 为空，禁止{action}。")
    if not re.search(rf"=== 第 {chapter_no:03d} 章 大燕商行资产负债表 ===", content):
        raise ValueError(f"第{chapter_no:03d}章资产上下文标题与章节号不一致。")
    return preview_file


def _validate_radar_content(chapter_no: int, content: str):
    if not re.search(rf"# AI 单章战术突击靶点：第 {chapter_no} 章\b", content):
        raise ValueError(f"第{chapter_no:03d}章雷达标题与章节号不一致。")
    for marker in ["【▶ 本章必写任务 ◀】", "## 3. 章边界约束", "本章止步点：", "下一章禁止提前兑现项："]:
        if marker not in content:
            raise ValueError(f"第{chapter_no:03d}章雷达缺少关键结构：{marker}")


def _extract_ledger_payload(content: str):
    match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", content)
    if not match:
        raise ValueError("台账中未找到合法的 JSON 代码块。")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError(f"台账 JSON 解析失败：{exc}")


def _assert_title_ready(chapter_no: int, title: str):
    cleaned = (title or "").strip()
    if not cleaned:
        raise ValueError(f"第{chapter_no:03d}章标题为空，禁止保存正文。")
    if cleaned.startswith("第"):
        raise ValueError(f"第{chapter_no:03d}章标题不应包含章节号前缀，请只传纯标题。")


def _assert_chapter_content_ready(chapter_no: int, title: str, content: str):
    text = str(content or "")
    if not text.strip():
        raise ValueError(f"第{chapter_no:03d}章正文为空，禁止保存。")
    if not re.search(rf"^# 第0*{chapter_no}章\s+.+", text, re.M):
        raise ValueError(f"第{chapter_no:03d}章正文缺少规范标题行。")
    if title.strip() and not re.search(rf"^# 第0*{chapter_no}章\s+{re.escape(title.strip())}$", text, re.M):
        raise ValueError(f"第{chapter_no:03d}章正文标题行与提交标题不一致。")
    if not re.search(r"【新历\d{4}年\d{1,2}月\d{1,2}日·旧历[一二三四五六七八九十正冬腊元〇零两初廿卅]+(?:月)?[一二三四五六七八九十正冬腊元〇零两初廿卅]*，[^】]+】", text):
        raise ValueError(f"第{chapter_no:03d}章正文缺少合规日期地点行。")
    forbidden_hits = [phrase for phrase in FORBIDDEN_NARRATIVE_PHRASES if phrase in text]
    if forbidden_hits:
        raise ValueError(f"第{chapter_no:03d}章正文出现禁用叙事词：{'、'.join(forbidden_hits)}")
    _assert_forbidden_titles_not_used(chapter_no, text)
    _assert_dialogue_title_rules(chapter_no, text)


def _assert_forbidden_titles_not_used(chapter_no: int, content: str):
    db = extract_character_db(chapter_no)
    hits = []
    for name, info in db.items():
        title_info = info.get("effective_title") or {}
        for raw_title in title_info.get("forbidden_titles") or []:
            title = str(raw_title).strip()
            if not title or title in AMBIGUOUS_FORBIDDEN_TITLES:
                continue
            if title in content:
                hits.append(f"{name}:{title}")
    if hits:
        raise ValueError(f"第{chapter_no:03d}章正文出现高风险禁用称呼：{'、'.join(hits)}")


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
        for self_title, owners in self_title_map.items():
            if self_title and self_title in speech and speaker not in owners:
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
        raise ValueError(f"第{chapter_no:03d}章正文出现高风险动态称谓错误：{'；'.join(violations[:5])}")

# =========================================================================
# 领域一：状态侦测与沙盘推演 (Observe & Plan)
# =========================================================================

@mcp.tool()
def build_and_read_target_radar(chapter_no: int) -> str:
    """
    生成并直接返回指定章节的战术靶点雷达内容。
    无需额外调用文件读取工具，调用此工具即可拿到开写前的所有沙盘推演数据。
    """
    try:
        _assert_chapter_chain_ready(chapter_no, action="开始正文创作")
        result = subprocess.run(
            [sys.executable, str(ROOT / "local_generator" / "build_ai_target_context.py"), str(chapter_no)],
            cwd=ROOT, capture_output=True, text=True, check=True, encoding="utf-8"
        )
        radar_file = _assert_radar_ready(chapter_no, action="开始正文创作")
        return f"【雷达脚本执行日志】\n{result.stdout}\n\n【靶点雷达内容】\n{radar_file.read_text(encoding='utf-8')}"
    except subprocess.CalledProcessError as e:
        return f"雷达脚本执行失败:\n{e.stdout}\n{e.stderr}"
    except (FileNotFoundError, ValueError) as e:
        return f"雷达校验失败:\n{e}"

@mcp.tool()
def read_recent_chapters(current_chapter_no: int, count: int = 2) -> str:
    """
    读取最近 1~2 章的数据库摘要链，用于写新章前承接剧情。
    默认不再直接返回旧正文，避免历史文本脏词和错称回灌。
    """
    content = []
    for i in range(max(1, current_chapter_no - count), current_chapter_no):
        meta = get_chapter_metadata(i)
        if not meta:
            content.append(f"======== 第{i:03d}章 未找到 ========\n")
            continue
        content.append(
            "\n".join(
                [
                    f"======== 第{i:03d}章 前情摘要 ========",
                    f"时间线：{meta.get('timeline_mark', '') or '(未记录)'}",
                    f"摘要：{meta.get('written_summary', '') or '(未记录)'}",
                    f"钩子：{meta.get('next_hook', '') or '(未记录)'}",
                    f"资产变化：{meta.get('key_assets_change', '') or '(未记录)'}",
                ]
            )
        )
    return "\n".join(content) if content else "未找到任何近期章节正文。"

# =========================================================================
# 领域二：正文、备份与台账操作 (Action & Close)
# =========================================================================

@mcp.tool()
def save_chapter_text(chapter_no: int, title: str, content: str) -> str:
    """
    保存正文定稿。会自动处理规范的文件名和路径。
    title: 不包含'第XXX章'的纯标题（如：世子登门与更大的算盘）
    content: 包含 Markdown 格式的完整正文和结尾的可视台账。
    """
    _assert_write_prerequisites(chapter_no, action="保存正文")
    _assert_title_ready(chapter_no, title)
    _assert_chapter_content_ready(chapter_no, title, content)
    chapter_dir = ROOT / "chapter"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"第{chapter_no:03d}章 {title.strip()}.md"
    file_path = chapter_dir / file_name
    file_path.write_text(content, encoding='utf-8')
    return f"✅ 成功写入正文到：{file_path}"


@mcp.tool()
def save_chapter_ledger(chapter_no: int, content: str) -> str:
    """
    兼容工具：将 JSON 格式的台账保存到 temp 目录，准备用于闭环洗地。
    当前主流程推荐直接使用 Write 工具写入 temp/update_chapter_XXX.md。
    """
    _assert_write_prerequisites(chapter_no, action="保存台账")
    payload = _extract_ledger_payload(content)
    if payload.get("chapter_no") != chapter_no:
        raise ValueError(f"台账中的 chapter_no={payload.get('chapter_no')} 与当前章节 {chapter_no} 不一致。")
    assets_updates = payload.get("assets_updates") or {}
    current_assets = get_assets_db(chapter_no)
    for group_name, items in assets_updates.items():
        if not isinstance(items, dict):
            raise ValueError(f"资产更新分组 `{group_name}` 的内容必须为对象。")
        known_names = set((current_assets.get(group_name) or {}).keys())
        for item_key, change_val in items.items():
            if item_key not in known_names:
                note = change_val.get("note", "") if isinstance(change_val, dict) else ""
                if "新资产" not in note:
                    raise ValueError(
                        f"资产更新 `{group_name}.{item_key}` 未出现在当前资产上下文中；如属新资产，请在 note 中显式写明“新资产”。"
                    )
    temp_dir = ROOT / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"update_chapter_{chapter_no:03d}.md"
    file_path = temp_dir / file_name
    file_path.write_text(content, encoding='utf-8')
    return f"✅ 成功写入台账到：{file_path}"

@mcp.tool()
def finalize_chapter(chapter_no: int) -> str:
    """
    执行章节闭环洗地（将台账写入数据库，无需再更新 Markdown）。
    前提条件：正文已保存，且 temp/update_chapter_XXX.md 已存在。
    """
    try:
        _assert_write_prerequisites(chapter_no, action="执行闭环")
        result = subprocess.run(
            [sys.executable, str(ROOT / "local_generator" / "finalize_chapter_workflow.py"), str(chapter_no)],
            cwd=ROOT, capture_output=True, text=True, check=True, encoding="utf-8"
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"闭环洗地脚本执行失败:\n{e.stdout}\n{e.stderr}"
    except (FileNotFoundError, ValueError) as e:
        return f"雷达校验失败:\n{e}"

# =========================================================================
# 领域三：数据库直接查证与注入 (Database Intel & Injection)
# =========================================================================

@mcp.tool()
def get_db_schema(table_name: str = "") -> str:
    """
    获取 novel_ledger.db 的表结构。如果不知道某张表有哪些字段，调用此工具查询。
    table_name: 可选。提供表名返回字段名；留空则返回所有表名。
    """
    conn = get_connection()
    cur = conn.cursor()
    if not table_name:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()
        return "数据库中的所有表：\n" + ", ".join(tables)
    else:
        try:
            cur.execute(f"PRAGMA table_info({table_name})")
            columns = cur.fetchall()
            conn.close()
            if not columns:
                return f"未找到表 {table_name}。"
            res = [f"表 {table_name} 字段："]
            for col in columns:
                res.append(f"- {col[1]} ({col[2]})")
            return "\n".join(res)
        except Exception as e:
            return f"查询表结构失败: {e}"

@mcp.tool()
def query_novel_db(sql_query: str) -> str:
    """
    执行 SELECT 查询以获取小说事实设定（如物价、人物状态、地理位置）。
    注意：为了防止污染，此工具仅限执行 SELECT 和 PRAGMA 语句。
    """
    if not sql_query.strip().upper().startswith("SELECT") and not sql_query.strip().upper().startswith("PRAGMA"):
        return "⚠️ 此工具仅限执行 SELECT/PRAGMA 查询，修改数据库请使用 modify_novel_db。"
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql_query)
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return "查询成功，但没有找到匹配的数据。"
        return str([dict(row) for row in rows])
    except Exception as e:
        return f"SQL查询异常: {str(e)}"

@mcp.tool()
def modify_novel_db(sql_statement: str) -> str:
    """
    执行 INSERT/UPDATE/DELETE 语句修改设定。
    【警告】仅在原创了新角色/新物品，需要向 entities_registry、world_facts 等表注入数据时使用！
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        # 允许执行多条语句（以分号隔开）
        cur.executescript(sql_statement)
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return f"✅ SQL 执行成功！受影响的行数：{changes}"
    except Exception as e:
        return f"❌ SQL执行异常: {str(e)}"

if __name__ == "__main__":
    # 以 stdio 模式运行 MCP 服务器，供 IDE/客户端接入
    mcp.run()
