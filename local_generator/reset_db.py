import sqlite3

from single_db_utils import DB_PATH

def reset_database():
    """彻底重置数据库，将进度恢复到初始状态"""
    print(f"正在连接数据库: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. 重置章节
    cur.execute("""
        UPDATE chapters_nav 
        SET status = 'pending', 
            written_summary = NULL, 
            next_hook = NULL, 
            key_assets_change = NULL
    """)
    print(f"清空章节表：影响了 {cur.rowcount} 行。")

    # 2. 重置实体状态
    cur.execute("""
        UPDATE entities_registry 
        SET current_status = NULL, 
            core_memories = NULL, 
            last_update_chapter = 0
    """)
    print(f"重置实体状态：影响了 {cur.rowcount} 行。")

    # 3. 重置资产状态
    cur.execute("""
        UPDATE wealth_and_assets 
        SET last_update_chapter = 0
    """)
    # 这里的 current_value 视情况而定，如果需要彻底重置也可以设为空或初始值。
    print(f"重置资产时间：影响了 {cur.rowcount} 行。")

    # 4. 重置伏笔状态
    cur.execute("""
        UPDATE hooks_network 
        SET status = 'sleeping', 
            resolution = NULL
    """)
    print(f"重置伏笔状态：影响了 {cur.rowcount} 行。")

    # 5. 清空角色进展日志
    cur.execute("DELETE FROM character_progress_log")
    print(f"清空角色进展日志：影响了 {cur.rowcount} 行。")

    # 重置自增 ID (可选)
    cur.execute("DELETE FROM sqlite_sequence WHERE name='character_progress_log'")

    conn.commit()
    conn.close()
    print("数据库重置完毕！所有记录已清理干净。")

if __name__ == "__main__":
    reset_database()
