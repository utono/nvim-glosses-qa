#!/usr/bin/env python3
"""Database query functions for passage viewer.

Shared module for querying passages and glosses from the database.
Used by both nvim-glosses (Lua) and scene_analyzer.py (Python).
"""

import sqlite3
import sys
import json
from pathlib import Path
from typing import Optional

# Database location
DB_PATH = Path.home() / "utono" / "literature" / "gloss.db"


def get_plays() -> list[dict]:
    """Get list of all plays in database.

    Returns:
        List of dicts with play_name and passage count.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT play_name, COUNT(*) as count
        FROM passages
        WHERE play_name IS NOT NULL AND play_name != ''
        GROUP BY play_name
        ORDER BY play_name
    """)

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_passages_for_play(play_name: str) -> list[dict]:
    """Get all passages for a play, ordered sequentially.

    Args:
        play_name: Name of the play (e.g., 'henry-v')

    Returns:
        List of passage dicts ordered by act, scene, line_number.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.id, p.hash, p.source_text, p.source_file, p.play_name,
            p.act, p.scene, p.line_number, p.character,
            g.gloss_type, g.gloss_text
        FROM passages p
        JOIN glosses g ON g.passage_id = p.id
        WHERE p.play_name = ?
        ORDER BY
            CAST(p.act AS INTEGER),
            CAST(p.scene AS INTEGER),
            p.line_number
    """, (play_name,))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_qa_for_passage(passage_id: int) -> list[dict]:
    """Get Q&A addenda for a passage.

    Args:
        passage_id: The passage ID

    Returns:
        List of addendum dicts with question and answer.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, question, answer, timestamp
        FROM addenda
        WHERE passage_id = ?
        ORDER BY timestamp
    """, (passage_id,))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def search_passages(query: str, play_name: Optional[str] = None) -> list[dict]:
    """Search passages by text content.

    Args:
        query: Search string to match in source_text or character
        play_name: Optional play name to filter by

    Returns:
        List of matching passage dicts.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    search_term = f"%{query}%"

    if play_name:
        cursor.execute("""
            SELECT
                p.id, p.hash, p.source_text, p.source_file, p.play_name,
                p.act, p.scene, p.line_number, p.character,
                g.gloss_type, g.gloss_text
            FROM passages p
            JOIN glosses g ON g.passage_id = p.id
            WHERE p.play_name = ?
              AND (p.source_text LIKE ? OR p.character LIKE ?)
            ORDER BY
                CAST(p.act AS INTEGER),
                CAST(p.scene AS INTEGER),
                p.line_number
            LIMIT 100
        """, (play_name, search_term, search_term))
    else:
        cursor.execute("""
            SELECT
                p.id, p.hash, p.source_text, p.source_file, p.play_name,
                p.act, p.scene, p.line_number, p.character,
                g.gloss_type, g.gloss_text
            FROM passages p
            JOIN glosses g ON g.passage_id = p.id
            WHERE p.source_text LIKE ? OR p.character LIKE ?
            ORDER BY
                p.play_name,
                CAST(p.act AS INTEGER),
                CAST(p.scene AS INTEGER),
                p.line_number
            LIMIT 100
        """, (search_term, search_term))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_passage_by_hash(hash_value: str) -> Optional[dict]:
    """Get a single passage by hash.

    Args:
        hash_value: MD5 hash of the passage

    Returns:
        Passage dict or None if not found.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.id, p.hash, p.source_text, p.source_file, p.play_name,
            p.act, p.scene, p.line_number, p.character,
            g.gloss_type, g.gloss_text
        FROM passages p
        JOIN glosses g ON g.passage_id = p.id
        WHERE p.hash = ?
    """, (hash_value,))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# CLI interface for calling from Lua
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: db_queries.py <command> [args...]", file=sys.stderr)
        print("Commands: plays, passages <play>, qa <passage_id>, search <query> [play]",
              file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "plays":
        result = get_plays()
        print(json.dumps(result))

    elif command == "passages":
        if len(sys.argv) < 3:
            print("Error: play_name required", file=sys.stderr)
            sys.exit(1)
        play_name = sys.argv[2]
        result = get_passages_for_play(play_name)
        print(json.dumps(result))

    elif command == "qa":
        if len(sys.argv) < 3:
            print("Error: passage_id required", file=sys.stderr)
            sys.exit(1)
        passage_id = int(sys.argv[2])
        result = get_qa_for_passage(passage_id)
        print(json.dumps(result))

    elif command == "search":
        if len(sys.argv) < 3:
            print("Error: query required", file=sys.stderr)
            sys.exit(1)
        query = sys.argv[2]
        play_name = sys.argv[3] if len(sys.argv) > 3 else None
        result = search_passages(query, play_name)
        print(json.dumps(result))

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
