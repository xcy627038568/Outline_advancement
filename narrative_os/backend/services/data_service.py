from db.database import get_db

def get_all_assets():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM wealth_and_assets ORDER BY asset_type")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def get_all_hooks():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM hooks_network ORDER BY planted_in_chapter DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def get_all_facts():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT domain as category, fact_key, fact_value, notes as description FROM world_facts ORDER BY domain, fact_key")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows
