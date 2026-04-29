import re

from db.database import get_db, CHAPTER_DIR


def _normalize_timeline_text(value: str):
    text = str(value or "").strip()
    if not text:
        return ""
    return re.sub(
        r"(\d+)年([一二三四五六七八九十正冬腊元〇零]+)月",
        lambda match: f"{match.group(1)}年农历{match.group(2)}月",
        text,
    )

def get_all_chapters():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT chapter_no,
               COALESCE(timeline_mark, history_date_label) AS timeline_mark,
               stage_goal,
               chapter_target,
               status
        FROM chapters_nav
        ORDER BY chapter_no
        """
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    # 获取标题
    for row in rows:
        row['timeline_mark'] = _normalize_timeline_text(row.get('timeline_mark', ''))
        row['title'] = ""
        if CHAPTER_DIR.exists():
            prefix = f"第{row['chapter_no']:03d}章"
            for file in CHAPTER_DIR.glob(f"{prefix}*.md"):
                # 文件名格式: 第001章 猪食与皇子.md
                name = file.stem
                if " " in name:
                    row['title'] = name.split(" ", 1)[1]
                break

    return rows

def get_chapter_by_no(chapter_no: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chapters_nav WHERE chapter_no = ?", (chapter_no,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return None
        
    chapter_data = dict(row)
    if not chapter_data.get('timeline_mark'):
        chapter_data['timeline_mark'] = chapter_data.get('history_date_label', '')
    chapter_data['timeline_mark'] = _normalize_timeline_text(chapter_data.get('timeline_mark', ''))
    
    # 尝试读取正文内容
    chapter_data['chapter_content'] = "该章节尚未生成或找不到对应的正文文件。"
    
    if CHAPTER_DIR.exists():
        # 寻找格式为 "第XXX章 *.md" 的文件
        prefix = f"第{chapter_no:03d}章"
        for file in CHAPTER_DIR.glob(f"{prefix}*.md"):
            try:
                chapter_data['chapter_content'] = file.read_text(encoding="utf-8")
                name = file.stem
                if " " in name:
                    chapter_data['title'] = name.split(" ", 1)[1]
                else:
                    chapter_data['title'] = ""
                break
            except Exception:
                chapter_data['chapter_content'] = "读取正文文件失败"
                chapter_data['title'] = ""
                
    if 'title' not in chapter_data:
        chapter_data['title'] = ""
        
    return chapter_data
