from db.database import get_db

def get_all_entities():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM entities_registry ORDER BY importance_level DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def get_relationships_graph():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT name as id, name, entity_type, importance_level, current_status as current_state FROM entities_registry")
    nodes = [dict(row) for row in cur.fetchall()]
    
    cur.execute("SELECT source_entity as source, target_entity as target, relation_type as relationship_type, intensity as strength, core_conflict as description FROM entity_relationships")
    links = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    return {"nodes": nodes, "links": links}
