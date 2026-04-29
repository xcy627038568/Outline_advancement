import json
import os
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).absolute().parent.parent
DB_PATH = Path(os.environ.get("NOVEL_LEDGER_DB_PATH", str(ROOT / "novel_ledger.db"))).expanduser()

CHARACTER_EXTRA_COLUMNS = {
    "aliases_json": "TEXT",
    "role_type": "TEXT",
    "affiliation": "TEXT",
    "occupation": "TEXT",
    "personality": "TEXT",
    "appearance": "TEXT",
    "first_appearance": "TEXT",
    "status": "TEXT",
    "relationships_json": "TEXT",
    "history_json": "TEXT",
}

ASSET_EXTRA_COLUMNS = {
    "asset_group": "TEXT",
    "value_kind": "TEXT",
    "current_value_num": "REAL",
    "current_value_text": "TEXT",
    "unit": "TEXT",
}

ASSET_TYPE_LABELS = {
    "funds": "资金",
    "raw_materials": "原材料",
    "products": "成品",
    "personnel": "人力",
    "key_items": "关键资产",
}

TITLE_TIMELINE_COLUMNS = (
    "character_name",
    "start_chapter",
    "end_chapter",
    "timeline_mark",
    "identity_label",
    "narrative_label",
    "formal_title",
    "common_title",
    "self_title",
    "subordinate_title",
    "hostile_title",
    "public_title",
    "forbidden_titles_json",
    "scene_rules_json",
    "source_note",
)


def clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_timeline_text(value) -> str:
    text = clean_text(value)
    if not text:
        return ""
    return re.sub(
        r"(\d+)年([一二三四五六七八九十正冬腊元〇零]+)月",
        lambda match: f"{match.group(1)}年农历{match.group(2)}月",
        text,
    )


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cur.fetchall()}


def ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_type: str) -> None:
    if column_name not in get_columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def ensure_schema(conn: sqlite3.Connection) -> None:
    ensure_column(conn, "chapters_nav", "timeline_mark", "TEXT")
    for column_name, column_type in CHARACTER_EXTRA_COLUMNS.items():
        ensure_column(conn, "entities_registry", column_name, column_type)
    for column_name, column_type in ASSET_EXTRA_COLUMNS.items():
        ensure_column(conn, "wealth_and_assets", column_name, column_type)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS character_history_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_name TEXT NOT NULL,
            chapter_no INTEGER NOT NULL,
            event_summary TEXT NOT NULL,
            visibility TEXT DEFAULT '',
            certainty TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
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
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS character_titles_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_name TEXT NOT NULL,
            start_chapter INTEGER NOT NULL,
            end_chapter INTEGER,
            timeline_mark TEXT DEFAULT '',
            identity_label TEXT DEFAULT '',
            narrative_label TEXT DEFAULT '',
            formal_title TEXT DEFAULT '',
            common_title TEXT DEFAULT '',
            self_title TEXT DEFAULT '',
            subordinate_title TEXT DEFAULT '',
            hostile_title TEXT DEFAULT '',
            public_title TEXT DEFAULT '',
            forbidden_titles_json TEXT DEFAULT '[]',
            scene_rules_json TEXT DEFAULT '{}',
            source_note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_character_titles_unique
        ON character_titles_timeline (character_name, start_chapter)
        """
    )
    conn.commit()


def parse_json_text(text: str | None, default):
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def to_json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def merge_unique_list(existing: list, incoming: list, limit: int | None = None) -> list:
    merged = list(existing or [])
    for item in incoming or []:
        if item not in merged:
            merged.append(item)
    return merged[-limit:] if limit else merged


def merge_dict(existing: dict, incoming: dict) -> dict:
    merged = dict(existing or {})
    merged.update(incoming or {})
    return merged


def chapter_row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def chapter_payload_has_content(payload: dict) -> bool:
    return any(
        payload.get(field)
        for field in ("timeline_mark", "written_summary", "next_hook", "key_assets_change")
    ) or payload.get("status") == "written"


def merge_chapter_payload(existing: dict | None, incoming: dict) -> dict:
    merged = dict(existing or {})
    for field in ("written_summary", "next_hook", "key_assets_change", "timeline_mark", "status"):
        value = incoming.get(field)
        if value not in (None, ""):
            merged[field] = value
    timeline_value = incoming.get("timeline_mark") or merged.get("timeline_mark") or merged.get("history_date_label") or ""
    timeline_value = normalize_timeline_text(timeline_value)
    if timeline_value:
        merged["timeline_mark"] = timeline_value
    if incoming.get("status") == "written":
        merged["status"] = "written"
    return merged


def upsert_character(conn: sqlite3.Connection, name: str, char_data: dict, chapter_no: int | None = None) -> None:
    cur = conn.cursor()
    cur.execute("SELECT * FROM entities_registry WHERE name = ?", (name,))
    existing = cur.fetchone()
    existing_data = dict(existing) if existing else {}

    aliases = merge_unique_list(parse_json_text(existing_data.get("aliases_json"), []), char_data.get("aliases", []))
    relationships = merge_dict(
        parse_json_text(existing_data.get("relationships_json"), {}),
        char_data.get("relationships", {}),
    )
    history = merge_unique_list(
        parse_json_text(existing_data.get("history_json"), []),
        char_data.get("history", []),
        limit=20,
    )

    payload = {
        "name": clean_text(name),
        "entity_type": "角色",
        "importance_level": existing_data.get("importance_level") or 3,
        "static_core": clean_text(char_data.get("personality") or existing_data.get("static_core") or ""),
        "current_status": clean_text(char_data.get("status") or existing_data.get("current_status") or ""),
        "core_memories": existing_data.get("core_memories"),
        "last_update_chapter": chapter_no or existing_data.get("last_update_chapter") or 0,
        "aliases_json": to_json_text(aliases),
        "role_type": clean_text(char_data.get("role_type") or existing_data.get("role_type") or ""),
        "affiliation": clean_text(char_data.get("affiliation") or existing_data.get("affiliation") or ""),
        "occupation": clean_text(char_data.get("occupation") or existing_data.get("occupation") or ""),
        "personality": clean_text(char_data.get("personality") or existing_data.get("personality") or ""),
        "appearance": clean_text(char_data.get("appearance") or existing_data.get("appearance") or ""),
        "first_appearance": clean_text(char_data.get("first_appearance") or existing_data.get("first_appearance") or ""),
        "status": clean_text(char_data.get("status") or existing_data.get("status") or ""),
        "relationships_json": to_json_text(relationships),
        "history_json": to_json_text(history),
    }

    if existing:
        cur.execute(
            """
            UPDATE entities_registry
            SET entity_type = ?, importance_level = ?, static_core = ?, current_status = ?,
                core_memories = ?, last_update_chapter = ?, aliases_json = ?, role_type = ?,
                affiliation = ?, occupation = ?, personality = ?, appearance = ?,
                first_appearance = ?, status = ?, relationships_json = ?, history_json = ?
            WHERE name = ?
            """,
            (
                payload["entity_type"],
                payload["importance_level"],
                payload["static_core"],
                payload["current_status"],
                payload["core_memories"],
                payload["last_update_chapter"],
                payload["aliases_json"],
                payload["role_type"],
                payload["affiliation"],
                payload["occupation"],
                payload["personality"],
                payload["appearance"],
                payload["first_appearance"],
                payload["status"],
                payload["relationships_json"],
                payload["history_json"],
                name,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO entities_registry (
                name, entity_type, importance_level, static_core, current_status,
                core_memories, last_update_chapter, aliases_json, role_type,
                affiliation, occupation, personality, appearance, first_appearance,
                status, relationships_json, history_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["name"],
                payload["entity_type"],
                payload["importance_level"],
                payload["static_core"],
                payload["current_status"],
                payload["core_memories"],
                payload["last_update_chapter"],
                payload["aliases_json"],
                payload["role_type"],
                payload["affiliation"],
                payload["occupation"],
                payload["personality"],
                payload["appearance"],
                payload["first_appearance"],
                payload["status"],
                payload["relationships_json"],
                payload["history_json"],
            ),
        )


def upsert_asset(conn: sqlite3.Connection, asset_group: str, asset_name: str, value, chapter_no: int | None = None) -> None:
    cur = conn.cursor()
    cur.execute("SELECT * FROM wealth_and_assets WHERE asset_name = ?", (asset_name,))
    existing = cur.fetchone()
    existing_data = dict(existing) if existing else {}

    is_numeric = isinstance(value, (int, float))
    current_value_num = float(value) if is_numeric else None
    current_value_text = "" if is_numeric else str(value)

    payload = {
        "asset_name": clean_text(asset_name),
        "asset_type": clean_text(existing_data.get("asset_type") or ASSET_TYPE_LABELS.get(asset_group, asset_group)),
        "current_value": str(value),
        "last_update_chapter": chapter_no or existing_data.get("last_update_chapter") or 0,
        "hidden_risk": clean_text(existing_data.get("hidden_risk") or ""),
        "asset_group": clean_text(asset_group),
        "value_kind": "number" if is_numeric else "text",
        "current_value_num": current_value_num,
        "current_value_text": current_value_text,
        "unit": clean_text(existing_data.get("unit") or ""),
    }

    if existing:
        cur.execute(
            """
            UPDATE wealth_and_assets
            SET asset_type = ?, current_value = ?, last_update_chapter = ?, hidden_risk = ?,
                asset_group = ?, value_kind = ?, current_value_num = ?, current_value_text = ?, unit = ?
            WHERE asset_name = ?
            """,
            (
                payload["asset_type"],
                payload["current_value"],
                payload["last_update_chapter"],
                payload["hidden_risk"],
                payload["asset_group"],
                payload["value_kind"],
                payload["current_value_num"],
                payload["current_value_text"],
                payload["unit"],
                asset_name,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO wealth_and_assets (
                asset_name, asset_type, current_value, last_update_chapter, hidden_risk,
                asset_group, value_kind, current_value_num, current_value_text, unit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["asset_name"],
                payload["asset_type"],
                payload["current_value"],
                payload["last_update_chapter"],
                payload["hidden_risk"],
                payload["asset_group"],
                payload["value_kind"],
                payload["current_value_num"],
                payload["current_value_text"],
                payload["unit"],
            ),
        )


def append_character_history(
    conn: sqlite3.Connection,
    character_name: str,
    chapter_no: int,
    event_summary: str,
    visibility: str = "",
    certainty: str = "",
) -> None:
    event_summary = clean_text(event_summary)
    if not event_summary:
        return
    conn.execute(
        """
        INSERT INTO character_history_log (
            character_name, chapter_no, event_summary, visibility, certainty
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            clean_text(character_name),
            chapter_no,
            event_summary,
            clean_text(visibility),
            clean_text(certainty),
        ),
    )


def get_character_history_upto(
    conn: sqlite3.Connection,
    character_name: str,
    chapter_no: int,
    limit: int = 5,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT character_name, chapter_no, event_summary, visibility, certainty
        FROM character_history_log
        WHERE character_name = ? AND chapter_no <= ?
        ORDER BY chapter_no DESC, id DESC
        LIMIT ?
        """,
        (character_name, chapter_no, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def _normalize_title_record(character_name: str, title_data: dict) -> dict:
    payload = {}
    payload["character_name"] = clean_text(character_name)
    payload["start_chapter"] = int(title_data.get("start_chapter") or 1)
    end_chapter = title_data.get("end_chapter")
    payload["end_chapter"] = None if end_chapter in (None, "", 0) else int(end_chapter)
    payload["timeline_mark"] = normalize_timeline_text(title_data.get("timeline_mark") or "")
    payload["identity_label"] = clean_text(title_data.get("identity_label") or title_data.get("identity") or "")
    payload["narrative_label"] = clean_text(title_data.get("narrative_label") or "")
    payload["formal_title"] = clean_text(title_data.get("formal_title") or "")
    payload["common_title"] = clean_text(title_data.get("common_title") or "")
    payload["self_title"] = clean_text(title_data.get("self_title") or "")
    payload["subordinate_title"] = clean_text(title_data.get("subordinate_title") or "")
    payload["hostile_title"] = clean_text(title_data.get("hostile_title") or "")
    payload["public_title"] = clean_text(title_data.get("public_title") or "")
    payload["forbidden_titles_json"] = to_json_text(title_data.get("forbidden_titles") or [])
    payload["scene_rules_json"] = to_json_text(title_data.get("scene_rules") or {})
    payload["source_note"] = clean_text(title_data.get("note") or title_data.get("source_note") or "")
    return payload


def upsert_character_title_timeline(
    conn: sqlite3.Connection,
    character_name: str,
    title_entries,
) -> int:
    if not title_entries:
        return 0
    if isinstance(title_entries, dict):
        title_entries = [title_entries]
    ensure_schema(conn)
    cur = conn.cursor()
    count = 0
    for raw_entry in title_entries:
        payload = _normalize_title_record(character_name, raw_entry or {})
        cur.execute(
            """
            INSERT INTO character_titles_timeline (
                character_name, start_chapter, end_chapter, timeline_mark,
                identity_label, narrative_label, formal_title, common_title,
                self_title, subordinate_title, hostile_title, public_title,
                forbidden_titles_json, scene_rules_json, source_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(character_name, start_chapter) DO UPDATE SET
                end_chapter = excluded.end_chapter,
                timeline_mark = excluded.timeline_mark,
                identity_label = excluded.identity_label,
                narrative_label = excluded.narrative_label,
                formal_title = excluded.formal_title,
                common_title = excluded.common_title,
                self_title = excluded.self_title,
                subordinate_title = excluded.subordinate_title,
                hostile_title = excluded.hostile_title,
                public_title = excluded.public_title,
                forbidden_titles_json = excluded.forbidden_titles_json,
                scene_rules_json = excluded.scene_rules_json,
                source_note = excluded.source_note
            """,
            tuple(payload[column] for column in TITLE_TIMELINE_COLUMNS),
        )
        count += 1
    return count


def get_effective_character_title(
    conn: sqlite3.Connection,
    character_name: str,
    chapter_no: int,
) -> dict:
    ensure_schema(conn)
    row = conn.execute(
        """
        SELECT *
        FROM character_titles_timeline
        WHERE character_name = ?
          AND start_chapter <= ?
          AND (end_chapter IS NULL OR end_chapter >= ?)
        ORDER BY start_chapter DESC, id DESC
        LIMIT 1
        """,
        (character_name, chapter_no, chapter_no),
    ).fetchone()
    if not row:
        return {}
    result = dict(row)
    result["forbidden_titles"] = parse_json_text(result.get("forbidden_titles_json"), [])
    result["scene_rules"] = parse_json_text(result.get("scene_rules_json"), {})
    return result


def get_effective_titles_for_characters(
    conn: sqlite3.Connection,
    chapter_no: int,
    character_names: list[str],
) -> dict[str, dict]:
    result = {}
    for name in character_names:
        title_info = get_effective_character_title(conn, name, chapter_no)
        if title_info:
            result[name] = title_info
    return result


def append_asset_history(
    conn: sqlite3.Connection,
    asset_group: str,
    asset_name: str,
    value,
    chapter_no: int,
    change_note: str = "",
) -> None:
    is_numeric = isinstance(value, (int, float))
    conn.execute(
        """
        INSERT INTO asset_history_log (
            asset_name, asset_group, chapter_no, value_kind, value_num, value_text, change_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            clean_text(asset_name),
            clean_text(asset_group),
            chapter_no,
            "number" if is_numeric else "text",
            float(value) if is_numeric else None,
            "" if is_numeric else clean_text(value),
            clean_text(change_note),
        ),
    )


def get_latest_asset_snapshot_upto(
    conn: sqlite3.Connection,
    chapter_no: int,
) -> dict[str, dict]:
    rows = conn.execute(
        """
        SELECT asset_name, asset_group, chapter_no, value_kind, value_num, value_text, change_note
        FROM (
            SELECT
                asset_name,
                asset_group,
                chapter_no,
                value_kind,
                value_num,
                value_text,
                change_note,
                ROW_NUMBER() OVER (
                    PARTITION BY asset_name
                    ORDER BY chapter_no DESC, id DESC
                ) AS rn
            FROM asset_history_log
            WHERE chapter_no <= ?
        )
        WHERE rn = 1
        ORDER BY asset_group, asset_name
        """,
        (chapter_no,),
    ).fetchall()
    return {row["asset_name"]: dict(row) for row in rows}
