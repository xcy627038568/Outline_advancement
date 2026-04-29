import sqlite3

from single_db_utils import DB_PATH, ROOT

SCHEMA_PATH = ROOT / "rules" / "schema_v3.sql"

def init_db():
    print("正在创建 V4 极简数据库结构...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 如果没有 schema_v3.sql，就用硬编码的建表语句
    if SCHEMA_PATH.exists():
        cur.executescript(SCHEMA_PATH.read_text(encoding='utf-8'))
    else:
        cur.executescript('''
        CREATE TABLE IF NOT EXISTS chapters_nav (
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
        CREATE TABLE IF NOT EXISTS entities_registry (
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
        CREATE TABLE IF NOT EXISTS entity_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_entity TEXT,
            target_entity TEXT,
            relation_type TEXT,
            intensity INTEGER,
            last_event_chapter INTEGER,
            core_conflict TEXT
        );
        CREATE TABLE IF NOT EXISTS locations_and_territories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_name TEXT UNIQUE,
            owner_entity TEXT,
            function_desc TEXT,
            current_status TEXT,
            established_chapter INTEGER
        );
        CREATE TABLE IF NOT EXISTS wealth_and_assets (
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
        CREATE TABLE IF NOT EXISTS hooks_network (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hook_code TEXT UNIQUE,
            description TEXT,
            planted_in_chapter INTEGER,
            status TEXT,
            resolution TEXT
        );
        CREATE TABLE IF NOT EXISTS world_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT,
            fact_key TEXT,
            fact_value TEXT,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS character_history_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_name TEXT NOT NULL,
            chapter_no INTEGER NOT NULL,
            event_summary TEXT NOT NULL,
            visibility TEXT DEFAULT '',
            certainty TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS asset_history_log (
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
        ''')
    conn.commit()
    return conn, cur

def inject_initial_entities(cur):
    print("正在注入初始核心实体与资产...")
    entities = [
        ("朱棣", "角色", 5, "极度多疑，雄才大略。主角最强保护伞也是最大威胁。"),
        ("徐皇后", "角色", 5, "温婉端庄，女中诸葛。主角内院绝对安全区，纯粹的慈母。"),
        ("朱高炽", "角色", 5, "宽厚仁慈但精明。主角最稳政治盟友，后勤大总管。")
    ]
    cur.executemany("INSERT OR IGNORE INTO entities_registry (name, entity_type, importance_level, static_core) VALUES (?, ?, ?, ?)", entities)
    
def main():
    conn, cur = init_db()
    inject_initial_entities(cur)
    conn.commit()
    conn.close()
    print("🎉 V4 数据库构建并灌库完成！")

if __name__ == "__main__":
    main()
