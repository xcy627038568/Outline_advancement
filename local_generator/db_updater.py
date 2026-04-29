import sqlite3

from single_db_utils import DB_PATH

def update_chapter_status(chapter_no: int, summary: str, next_hook: str, assets_change: str):
    """生成完成后，更新章节表"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE chapters_nav 
        SET status = 'written', 
            written_summary = ?, 
            next_hook = ?, 
            key_assets_change = ?
        WHERE chapter_no = ?
    """, (summary, next_hook, assets_change, chapter_no))
    conn.commit()
    conn.close()

def get_pending_chapters():
    """获取所有待生成的章节"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM chapters_nav WHERE status = 'pending' ORDER BY chapter_no ASC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows
