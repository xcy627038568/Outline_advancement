from db.database import get_db

def get_dashboard_alerts():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM chapters_nav WHERE status = 'written' ORDER BY chapter_no DESC LIMIT 1")
    latest_chapter = cur.fetchone()
    latest_chapter = dict(latest_chapter) if latest_chapter else None
    
    cur.execute("SELECT * FROM wealth_and_assets")
    assets = [dict(row) for row in cur.fetchall()]
    
    alerts = []
    
    cur.execute("SELECT * FROM hooks_network WHERE status = 'burning'")
    burning_hooks = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    return {
        "latest_chapter": latest_chapter,
        "assets": assets,
        "burning_hooks": burning_hooks,
        "alerts": alerts
    }

def get_progress_matrix():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT name, importance_level, static_core, current_status FROM entities_registry WHERE entity_type = '角色' ORDER BY importance_level DESC")
    characters = [dict(row) for row in cur.fetchall()]
    
    cur.execute("SELECT hook_code, planted_in_chapter, status, description, resolution FROM hooks_network ORDER BY planted_in_chapter DESC")
    hooks = [dict(row) for row in cur.fetchall()]
    
    cur.execute(
        """
        SELECT chapter_no,
               COALESCE(timeline_mark, history_date_label) AS timeline_mark,
               stage_goal,
               chapter_target,
               written_summary,
               next_hook,
               key_assets_change
        FROM chapters_nav
        WHERE status != 'pending'
        ORDER BY chapter_no DESC
        """
    )
    chapters = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    return {
        "characters": characters,
        "hooks": hooks,
        "chapters": chapters
    }
