#!/usr/bin/env python3
"""Scene-level line-by-line analysis generator.

Processes an entire scene by speech, generating line-by-line actor analysis
for each speech unit, caching results in the database, and producing a
unified markdown file per scene.

Usage:
    python scene_analyzer.py <play_file> <act> <scene> [--output-dir DIR]
    python scene_analyzer.py henry_v_gut.txt 4 7
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import hashlib

# Database and output paths
DB_PATH = Path.home() / "utono" / "literature" / "gloss.db"
GLOSSES_DIR = Path.home() / "utono" / "literature" / "glosses"


def generate_hash(text: str) -> str:
    """Generate MD5 hash for text with consistent normalization."""
    normalized = text.strip().replace('\r\n', '\n')
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


# Scene analyzer log file
LOG_DIR = Path.home() / "utono" / "nvim-glosses-qa" / "logs"
LOG_FILE = LOG_DIR / "scene_analyzer.log"


def setup_scene_logging() -> logging.Logger:
    """Set up logging for scene analyzer with dedicated log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stderr)
        ]
    )

    return logging.getLogger('scene_analyzer')


logger = setup_scene_logging()


# =============================================================================
# GlossDatabase - writes to passages/glosses/addenda tables
# =============================================================================

class GlossDatabase:
    """SQLite operations for gloss storage using normalized schema.

    Schema:
        passages: One row per unique source text (hash is unique key)
        glosses: One row per gloss type per passage (FK to passages)
        addenda: Multiple rows per passage for Q&A (FK to passages)
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_PATH

    def setup(self) -> None:
        """Create database schema if not exists."""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS passages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT UNIQUE NOT NULL,
            source_text TEXT NOT NULL,
            source_file TEXT NOT NULL,
            tag TEXT,
            line_number INTEGER,
            char_position INTEGER,
            character TEXT,
            act TEXT,
            scene TEXT,
            file_path TEXT,
            file_hash TEXT,
            last_modified TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            version INTEGER DEFAULT 1,
            play_name TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS glosses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passage_id INTEGER NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
            gloss_type TEXT NOT NULL,
            gloss_text TEXT NOT NULL,
            gloss_file TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(passage_id, gloss_type)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS addenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passage_id INTEGER NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_passages_hash ON passages(hash)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_glosses_passage_id ON glosses(passage_id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_glosses_type ON glosses(gloss_type)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_addenda_passage_id ON addenda(passage_id)")

        conn.commit()
        conn.close()

    def get_existing(self, text_hash: str, gloss_type: str) -> Optional[dict]:
        """Check if a gloss exists for this hash and type."""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT g.gloss_text, g.gloss_file
            FROM glosses g
            JOIN passages p ON g.passage_id = p.id
            WHERE p.hash = ? AND g.gloss_type = ?
        """, (text_hash, gloss_type))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {'text': row[0], 'file': row[1]}
        return None

    def get_or_create_passage(self, text_hash: str, source_text: str,
                               metadata: dict) -> int:
        """Get existing passage ID or create new passage."""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check if passage exists
        cursor.execute("SELECT id FROM passages WHERE hash = ?", (text_hash,))
        row = cursor.fetchone()

        if row:
            conn.close()
            return row[0]

        # Create new passage
        cursor.execute("""
            INSERT INTO passages (hash, source_text, source_file, character,
                                  act, scene, play_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            text_hash,
            source_text,
            metadata.get('source_file', ''),
            metadata.get('character'),
            metadata.get('act'),
            metadata.get('scene'),
            metadata.get('play_name')
        ))

        passage_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return passage_id

    def save(self, text_hash: str, source_text: str, gloss_text: str,
             gloss_file: str, gloss_type: str, metadata: dict) -> None:
        """Save or update a gloss."""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get or create passage
        passage_id = self.get_or_create_passage(text_hash, source_text, metadata)

        # Upsert gloss
        cursor.execute("""
            INSERT INTO glosses (passage_id, gloss_type, gloss_text, gloss_file)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(passage_id, gloss_type) DO UPDATE SET
                gloss_text = excluded.gloss_text,
                gloss_file = excluded.gloss_file,
                timestamp = CURRENT_TIMESTAMP
        """, (passage_id, gloss_type, gloss_text, gloss_file))

        conn.commit()
        conn.close()

    def save_addendum(self, text_hash: str, question: str, answer: str) -> None:
        """Save a Q&A addendum for a passage."""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get passage ID
        cursor.execute("SELECT id FROM passages WHERE hash = ?", (text_hash,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            logger.warning(f"Cannot save addendum: passage {text_hash[:8]} not found")
            return

        passage_id = row[0]

        cursor.execute("""
            INSERT INTO addenda (passage_id, question, answer)
            VALUES (?, ?, ?)
        """, (passage_id, question, answer))

        conn.commit()
        conn.close()


# =============================================================================
# Stub functions for removed gloss module imports
# =============================================================================

def create_backend(backend_type: str):
    """Stub for removed gloss module backend.

    The --save-chunk and --export-chunks modes don't use the backend.
    This stub allows the code to initialize but will fail if actually called.
    """
    class StubBackend:
        def generate(self, prompt: str) -> str:
            raise NotImplementedError(
                "API backend removed. Use --export-chunks and --save-chunk modes "
                "with Claude Code instead."
            )
    return StubBackend()


class PromptBuilder:
    """Stub for removed gloss module PromptBuilder.

    Only used in API mode which is no longer supported.
    """
    def __init__(self, text: str):
        self.text = text

    def build(self, style: str = None) -> str:
        raise NotImplementedError(
            "PromptBuilder removed. Use --export-chunks and --save-chunk modes "
            "with Claude Code instead."
        )


# Structured error codes for Claude Code intervention
class ErrorCode:
    """Error codes for structured error output."""
    SCENE_NOT_FOUND = "scene_not_found"
    API_FAILURE = "api_failure"
    API_RATE_LIMIT = "api_rate_limit"
    DATABASE_ERROR = "database_error"
    FILE_ERROR = "file_error"
    VALIDATION_ERROR = "validation_error"


def print_structured_error(
    code: str,
    message: str,
    context: dict = None,
    suggestion: str = None,
    action: str = None
) -> None:
    """Print a structured error message for Claude Code to parse.

    Args:
        code: Error code from ErrorCode class
        message: Human-readable error message
        context: Dict of contextual information (scene, file, chunk, etc.)
        suggestion: Suggested fix or next step
        action: Action to take (e.g., "Skip this scene", "Retry")
    """
    print(f"\n[ERROR] {code}", file=sys.stderr)
    print(f"  Message: {message}", file=sys.stderr)
    if context:
        for key, value in context.items():
            print(f"  {key.title()}: {value}", file=sys.stderr)
    if suggestion:
        print(f"  Suggestion: {suggestion}", file=sys.stderr)
    if action:
        print(f"  Action: {action}", file=sys.stderr)
    print("", file=sys.stderr)


def parse_line_translations(generated_output: str) -> list[tuple[str, str, str]]:
    """Parse generated translation output to extract line-level mappings.

    Input format (from Claude /line-by-line command):
        VIOLA.

        **"What country friends is this?"**

        What land is this, my friends?

        **"This is Illyria lady."**

        This is Illyria, my lady.

        CAPTAIN.

        **"A noble duke in nature"**

        A duke noble in character.

    Returns:
        List of (original_text, translation, character) tuples.
        Character is the most recent speaker heading seen.
    """
    results = []
    current_character = None

    # Pattern for speaker heading: ALL CAPS followed by period on its own line
    speaker_pattern = re.compile(r'^([A-Z][A-Z\s]+)\.\s*$')

    # Pattern for original line: **"text"**
    original_pattern = re.compile(r'^\*\*"([^"]+)"\*\*\s*$')

    lines = generated_output.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check for speaker heading
        speaker_match = speaker_pattern.match(line)
        if speaker_match:
            current_character = speaker_match.group(1).strip()
            i += 1
            continue

        # Check for original line
        original_match = original_pattern.match(line)
        if original_match:
            original_text = original_match.group(1)

            # Look for translation in subsequent non-empty lines
            # Skip blank lines, then take the next non-bold line as translation
            translation = None
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                # Skip empty lines
                if not next_line:
                    j += 1
                    continue
                # Stop if we hit another **"..."** or speaker heading
                if original_pattern.match(next_line) or speaker_pattern.match(next_line):
                    break
                # This is the translation
                translation = next_line
                break

            if translation:
                results.append((original_text, translation, current_character))

        i += 1

    return results


def save_line_translations(
    translations: list[tuple[str, str, str]],
    source_file: str,
    chunk_text: str,
    play_name: str,
    act: str,
    scene: str,
    chunk_hash: str,
    play_file_lines: list[str],
    chunk_start_line: int,
    scene_end_line: int = None
) -> int:
    """Save line-level translations to the database.

    Args:
        translations: List of (original_text, translation, character) tuples
        source_file: Path to the play file (for matching)
        chunk_text: The original chunk text (for line number mapping)
        play_name: Name of the play
        act: Act number as string
        scene: Scene number as string
        chunk_hash: Hash of the chunk for reference
        play_file_lines: All lines from the play file (for line number lookup)
        chunk_start_line: Starting line number of chunk in source file
        scene_end_line: Ending line number of the scene (optional, improves matching)

    Returns:
        Number of translations saved.
    """
    import sqlite3

    if not translations:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    saved = 0

    # Build a map of original text to line numbers in the source file
    # Search from scene start to scene end (or fallback to start + 500)
    search_start = max(0, chunk_start_line - 10)
    if scene_end_line is not None:
        search_end = min(len(play_file_lines), scene_end_line + 10)
    else:
        search_end = min(len(play_file_lines), chunk_start_line + 500)

    for original_text, translation, character in translations:
        # Find the line number in the source file
        line_number = None
        original_stripped = original_text.strip()

        for i in range(search_start, search_end):
            file_line = play_file_lines[i].strip()
            # Match if the line contains the original text
            if original_stripped in file_line or file_line == original_stripped:
                line_number = i + 1  # 1-indexed
                break

        if line_number is None:
            logger.debug(f"Could not find line number for: {original_text[:50]}...")
            continue

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO line_translations
                (source_file, line_number, original_text, translation,
                 character, play_name, act, scene, chunk_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source_file,
                line_number,
                original_text,
                translation,
                character,
                play_name,
                act,
                scene,
                chunk_hash
            ))
            saved += 1
        except sqlite3.Error as e:
            logger.warning(f"Failed to save line translation: {e}")

    conn.commit()
    conn.close()
    return saved


def validate_line_translations(source_file: str, fix: bool = False) -> list[dict]:
    """Validate DB line_translations against actual source file content.

    Compares stored original_text with actual file lines at the same line numbers.
    Reports mismatches (orphaned entries) and optionally deletes them.

    Args:
        source_file: Absolute path to the play file to validate
        fix: If True, delete orphaned entries from database

    Returns:
        List of mismatch dictionaries with keys: id, line_number, db_text, file_text
    """
    import sqlite3

    # Load source file lines
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            file_lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Source file not found: {source_file}", file=sys.stderr)
        return []

    # Query all translations for this source file
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, line_number, original_text
        FROM line_translations
        WHERE source_file = ?
        ORDER BY line_number
    """, (source_file,))
    rows = cursor.fetchall()

    if not rows:
        print(f"No translations found for: {source_file}")
        conn.close()
        return []

    print(f"Validating: {source_file}")
    print(f"Checking {len(rows)} translations...\n")

    mismatches = []
    for row_id, line_number, db_text in rows:
        # Check if line number is within file range (line_number is 1-indexed)
        if line_number < 1 or line_number > len(file_lines):
            mismatches.append({
                'id': row_id,
                'line_number': line_number,
                'db_text': db_text,
                'file_text': '<LINE OUT OF RANGE>'
            })
            continue

        # Get actual file content at that line (convert to 0-indexed)
        file_text = file_lines[line_number - 1].strip()
        db_text_stripped = db_text.strip()

        # Match using same logic as save_line_translations:
        # DB text should be contained in file text, or exact match
        if db_text_stripped not in file_text and file_text != db_text_stripped:
            mismatches.append({
                'id': row_id,
                'line_number': line_number,
                'db_text': db_text,
                'file_text': file_text
            })

    # Report mismatches
    for m in mismatches:
        print(f"MISMATCH at line {m['line_number']}:")
        print(f"  DB:   \"{m['db_text']}\"")
        print(f"  File: \"{m['file_text']}\"")
        print()

    if mismatches:
        print(f"Found {len(mismatches)} orphaned translation(s).")
        if fix:
            # Delete orphaned entries
            orphan_ids = [m['id'] for m in mismatches]
            placeholders = ','.join('?' * len(orphan_ids))
            cursor.execute(f"DELETE FROM line_translations WHERE id IN ({placeholders})", orphan_ids)
            conn.commit()
            print(f"Deleted {len(mismatches)} orphaned translation(s).")
        else:
            print("\nRun with --fix to delete orphaned entries.")
    else:
        print("All translations match source file.")

    conn.close()
    return mismatches


@dataclass
class Speech:
    """A single character's continuous speech."""
    speaker: str
    lines: list[str]
    text: str  # Full text including speaker name
    line_start: int  # Line number in source file
    line_end: int

    # Pattern for stage directions
    STAGE_DIR_RE = re.compile(r'^\[.*\]\s*$')

    @property
    def hash(self) -> str:
        """Generate hash for this speech."""
        return generate_hash(self.text)

    @property
    def line_count(self) -> int:
        """Total lines including speaker name."""
        return len(self.lines) + 1  # +1 for "SPEAKER." line

    @property
    def has_dialogue(self) -> bool:
        """Check if speech contains actual dialogue (not just stage directions)."""
        for line in self.lines:
            stripped = line.strip()
            # Skip empty lines and stage directions
            if not stripped:
                continue
            if self.STAGE_DIR_RE.match(stripped):
                continue
            # Found actual dialogue
            return True
        return False


@dataclass
class SpeechChunk:
    """A group of consecutive speeches processed together."""
    speeches: list[Speech]
    text: str  # Combined text of all speeches

    @property
    def hash(self) -> str:
        """Generate hash for the combined chunk."""
        return generate_hash(self.text)

    @property
    def line_count(self) -> int:
        """Total lines across all speeches."""
        return sum(s.line_count for s in self.speeches)

    @property
    def speaker_summary(self) -> str:
        """Summary of speakers in this chunk."""
        speakers = [s.speaker for s in self.speeches]
        if len(speakers) == 1:
            return speakers[0]
        return f"{speakers[0]}...{speakers[-1]} ({len(speakers)} speeches)"


class PlayParser:
    """Parse a play file to extract scenes and speeches."""

    # Patterns for play structure
    # ACT pattern matches Roman numerals (ACT IV.), Arabic (ACT 1.), words (ACT FIRST.)
    # Also matches First Folio Latin: "Actus Primus." etc.
    ACT_PATTERN = re.compile(
        r'^(?:ACT|ACTUS)\s+([IVX]+|\d+|FIRST|SECOND|THIRD|FOURTH|FIFTH|'
        r'PRIMUS|SECUNDUS|TERTIUS|QUARTUS|QUINTUS)\.?\s*$',
        re.IGNORECASE
    )
    # SCENE pattern matches Roman (SCENE I.), Arabic (SCENE 1.), and First Folio Latin
    SCENE_PATTERN = re.compile(
        r'^(?:SCENE|SC[OE]?ENA)\s+([IVX]+|\d+|'
        r'PRIMA|SECUNDA|TERTIA|QUARTA|QUINTA|SEXTA|SEPTIMA|OCTAVA|NONA|DECIMA)[\.\s:]?(.*)$',
        re.IGNORECASE
    )
    # Combined ACT + SCENE on same line (e.g., "ACT IV. SCENE I." or "Actus Primus. Scoena Prima.")
    ACT_SCENE_COMBINED_PATTERN = re.compile(
        r'^(?:ACT|ACTUS)\s+([IVX]+|\d+|FIRST|SECOND|THIRD|FOURTH|FIFTH|'
        r'PRIMUS|SECUNDUS|TERTIUS|QUARTUS|QUINTUS)\.?\s*'
        r'(?:SCENE|SC[OE]?ENA)\s+([IVX]+|\d+|'
        r'PRIMA|SECUNDA|TERTIA|QUARTA|QUINTA|SEXTA|SEPTIMA|OCTAVA|NONA|DECIMA)[\.\s:]?(.*)$',
        re.IGNORECASE
    )
    PROLOGUE_PATTERN = re.compile(r'^PROLOGUE\.?\s*$', re.IGNORECASE)
    EPILOGUE_PATTERN = re.compile(r'^EPILOGUE\.?\s*$', re.IGNORECASE)
    # Cast list section headers
    CAST_LIST_PATTERN = re.compile(
        r'^(PERSONS REPRESENTED|DRAMATIS PERSONAE|DRAMATIS PERSON|CHARACTERS)\.?\s*$',
        re.IGNORECASE
    )
    STAGE_DIR_PATTERN = re.compile(r'^\[.*\]\s*$')

    # Ordinal words to integers (English and Latin)
    ORDINAL_TO_INT = {
        'FIRST': 1, 'SECOND': 2, 'THIRD': 3, 'FOURTH': 4, 'FIFTH': 5,
        # Latin ordinals for acts (masculine)
        'PRIMUS': 1, 'SECUNDUS': 2, 'TERTIUS': 3, 'QUARTUS': 4, 'QUINTUS': 5,
        # Latin ordinals for scenes (feminine)
        'PRIMA': 1, 'SECUNDA': 2, 'TERTIA': 3, 'QUARTA': 4, 'QUINTA': 5,
        'SEXTA': 6, 'SEPTIMA': 7, 'OCTAVA': 8, 'NONA': 9, 'DECIMA': 10,
    }

    def __init__(self, play_file: Path):
        """Initialize parser with play file.

        Args:
            play_file: Path to the play text file.
        """
        self.play_file = Path(play_file)
        self.lines: list[str] = []
        self.character_names: set[str] = set()
        self._load_file()
        self._parse_cast_list()

    def _load_file(self) -> None:
        """Load play file into memory."""
        with open(self.play_file, 'r', encoding='utf-8') as f:
            self.lines = f.readlines()

    def _detect_format(self) -> str:
        """Detect the format of the play text.

        Returns:
            'folio_full' - Has Latin headers AND multiple scene markers (5+)
            'folio_minimal' - Has Latin headers BUT only 1-4 markers
            'modern' - Has English ACT/SCENE markers
            'unmarked' - No act/scene markers found
        """
        latin_count = 0
        english_count = 0

        for line in self.lines:
            stripped = line.strip()
            # Count Latin markers (Actus, Scena, Scoena)
            if re.match(r'^(Actus|Scoena|Scena)\s+', stripped, re.IGNORECASE):
                latin_count += 1
            # Also check for combined "Actus... Scoena..." on one line
            elif re.match(r'^Actus\s+\w+.*Sco?ena', stripped, re.IGNORECASE):
                latin_count += 1
            # Count English markers
            elif re.match(r'^ACT\s+', stripped, re.IGNORECASE):
                english_count += 1
            elif re.match(r'^SCENE\s+', stripped, re.IGNORECASE):
                english_count += 1

        if latin_count >= 5:
            return 'folio_full'
        elif latin_count >= 1:
            return 'folio_minimal'
        elif english_count >= 1:
            return 'modern'
        return 'unmarked'

    def _infer_scene_boundaries(self) -> dict[int, tuple[int, int]]:
        """Infer scene boundaries from Exeunt/Enter patterns.

        For minimally-marked First Folio texts, scenes are inferred from
        stage directions: "Exeunt." followed by "Enter" indicates a scene
        change.

        Returns:
            Dict mapping scene number (1-based) to (start_line, end_line)
            where lines are 0-indexed.
        """
        scenes = {}
        scene_num = 1
        scene_start = 0

        # Find the first Enter (start of Scene 1)
        for i, line in enumerate(self.lines):
            stripped = line.strip()
            if stripped.startswith('Enter '):
                scene_start = i
                break

        for i, line in enumerate(self.lines):
            stripped = line.strip()

            # Scene ends at "Exeunt." (full cast exit)
            # Match: "Exeunt.", "Exeunt omnes.", "Exeunt omnes"
            if re.match(r'^Exeunt\.?$', stripped) or \
               re.match(r'^Exeunt omnes\.?$', stripped, re.IGNORECASE):
                # Look for "Enter" within next 5 lines
                found_enter = False
                for j in range(i + 1, min(i + 6, len(self.lines))):
                    next_line = self.lines[j].strip()
                    if next_line.startswith('Enter '):
                        scenes[scene_num] = (scene_start, i)
                        scene_num += 1
                        scene_start = j
                        found_enter = True
                        break

        # Final scene goes to end of file
        scenes[scene_num] = (scene_start, len(self.lines) - 1)

        logger.debug(f"Inferred {len(scenes)} scene boundaries")
        return scenes

    def _parse_cast_list(self) -> None:
        """Parse the cast list (Dramatis Personae) to extract character names.

        Populates self.character_names with normalized speaker names that can
        appear in the play. Handles both ALL CAPS plays (Twelfth Night) and
        Title Case plays (Romeo and Juliet).

        Also scans the play text for ALL CAPS speaker patterns as a fallback
        to catch speakers not in the cast list or listed under different names.
        """
        in_cast_section = False
        cast_end_line = 0

        # Find cast list section
        for i, line in enumerate(self.lines):
            stripped = line.strip()

            # Start of cast list
            if self.CAST_LIST_PATTERN.match(stripped):
                in_cast_section = True
                continue

            # End of cast list (ACT, SCENE, PROLOGUE, or significant blank gap)
            if in_cast_section:
                if (self.ACT_PATTERN.match(stripped) or
                    self.SCENE_PATTERN.match(stripped) or
                    self.PROLOGUE_PATTERN.match(stripped) or
                    stripped.startswith('SCENE')):
                    cast_end_line = i
                    break

        # Parse character names from cast list if found
        if in_cast_section:
            self._parse_cast_entries(cast_end_line)

        # Always also scan for ALL CAPS speakers in the text itself
        # This catches speakers like "DUKE" when cast says "ORSINO"
        self._scan_for_speakers()

        # Add common generic speakers that may not be in cast list
        generic_speakers = [
            'ALL', 'BOTH', 'CHORUS', 'CHOR', 'PROLOGUE', 'EPILOGUE',
            'SERVANT', 'MESSENGER', 'ATTENDANT', 'OFFICER', 'GENTLEMAN',
            'SOLDIER', 'CITIZEN', 'PAGE', 'BOY', 'WATCHMAN', 'GUARD',
            'FIRST OFFICER', 'SECOND OFFICER', 'FIRST CITIZEN',
            'SECOND CITIZEN', 'FIRST SERVANT', 'SECOND SERVANT',
            'FIRST GENTLEMAN', 'SECOND GENTLEMAN', 'FIRST WATCHMAN',
            'FIRST MUSICIAN', 'SECOND MUSICIAN', 'THIRD MUSICIAN',
        ]
        for speaker in generic_speakers:
            self.character_names.add(speaker)

        logger.debug(f"Parsed {len(self.character_names)} character names")

    def _parse_cast_entries(self, cast_end_line: int) -> None:
        """Parse individual entries from the cast list section.

        Args:
            cast_end_line: Line number where cast list ends (0-indexed).
        """
        # Title words that extend a character name
        title_prefixes = {'LADY', 'LORD', 'SIR', 'FRIAR', 'DUKE', 'KING',
                          'QUEEN', 'PRINCE', 'PRINCESS', 'FIRST', 'SECOND',
                          'THIRD', 'AN', 'A'}
        # Description words that end a character name
        description_words = {'WIFE', 'SON', 'DAUGHTER', 'SERVANT', 'FRIEND',
                             'KINSMAN', 'NEPHEW', 'UNCLE', 'BROTHER', 'SISTER',
                             'STEWARD', 'WOMAN', 'ATTENDING', 'OF', 'TO', 'IN',
                             'A', 'THE', 'HIS', 'HER', 'RICH', 'YOUNG', 'OLD'}

        for i, line in enumerate(self.lines):
            if i >= cast_end_line and cast_end_line > 0:
                break

            stripped = line.strip()
            if not stripped or self.CAST_LIST_PATTERN.match(stripped):
                continue

            # Skip stage directions and scene descriptions
            if stripped.startswith('[') or stripped.startswith('SCENE'):
                continue

            # Split on comma first (some entries use comma to separate)
            parts = stripped.split(',', 1)
            first_part = parts[0].strip()

            # Also check for multi-word entries without comma
            # e.g., "MALVOLIO Steward to Olivia."
            words = first_part.split()
            if not words:
                continue

            # Skip if first word doesn't start with capital
            if not words[0][0].isupper():
                continue

            # Build name from leading capitalized words (respecting titles)
            name_words = []
            for w in words:
                w_upper = w.upper().rstrip('.,')
                # Stop at description words (unless it's a title prefix)
                if w_upper in description_words and w_upper not in title_prefixes:
                    break
                # Stop at lowercase words (descriptions)
                if w[0].islower():
                    break
                # Stop at very long "words" (likely merged text)
                if len(w) > 20:
                    break
                name_words.append(w.rstrip('.,'))

            if name_words:
                name = ' '.join(name_words)
                self.character_names.add(name.upper())

                # Also extract title as potential speaker
                # e.g., "ORSINO, Duke of Illyria" -> also add "DUKE"
                if len(parts) > 1:
                    desc = parts[1].strip()
                    desc_words = desc.split()
                    if desc_words and desc_words[0][0].isupper():
                        first_desc_word = desc_words[0].rstrip('.,').upper()
                        if first_desc_word in title_prefixes:
                            self.character_names.add(first_desc_word)

                # Add abbreviation for Chorus
                if name.upper() == 'CHORUS':
                    self.character_names.add('CHOR')

    def _scan_for_speakers(self) -> None:
        """Scan play text to find speaker patterns.

        Detects both ALL CAPS (Henry V) and Title Case (Romeo and Juliet).
        Also handles formats without trailing periods (e.g., Gutenberg texts).
        """
        # Pattern for ALL CAPS speaker with period (e.g., "SAMPSON.")
        all_caps_with_period = re.compile(r'^([A-Z][A-Z\s]+)\.\s*$')

        # Pattern for ALL CAPS speaker without period (e.g., "THESEUS")
        # Must be alone on a line, 2+ chars, no lowercase
        all_caps_no_period = re.compile(r'^([A-Z][A-Z\s]{1,25})$')

        # Pattern for Title Case speaker (e.g., "Sampson.", "Lady Capulet.")
        # Matches: Capital letter + lowercase, optionally followed by more
        # capitalized words
        title_case_pattern = re.compile(
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\.\s*$'
        )

        for i, line in enumerate(self.lines):
            stripped = line.strip()
            if len(stripped) > 30 or len(stripped) < 2:
                continue

            # Try ALL CAPS with period first
            match = all_caps_with_period.match(stripped)
            if match:
                name = match.group(1).strip()
                # Skip ACT/SCENE markers
                if not (name.startswith('ACT') or name.startswith('SCENE')):
                    self.character_names.add(name)
                continue

            # Try ALL CAPS without period (check next line has content)
            match = all_caps_no_period.match(stripped)
            if match:
                name = match.group(1).strip()
                # Skip ACT/SCENE markers and stage directions
                if (name.startswith('ACT') or name.startswith('SCENE') or
                        name.startswith('ENTER') or name.startswith('EXIT') or
                        name.startswith('EXEUNT')):
                    continue
                # Verify next non-empty line is dialogue (not stage direction)
                if i + 1 < len(self.lines):
                    next_line = self.lines[i + 1].strip()
                    # If next line is not empty and not a stage direction
                    if next_line and not next_line.startswith('['):
                        self.character_names.add(name)
                continue

            # Try Title Case
            match = title_case_pattern.match(stripped)
            if match:
                name = match.group(1).strip()
                # Convert to upper for consistent storage
                name_upper = name.upper()
                if not (name_upper.startswith('ACT') or
                        name_upper.startswith('SCENE')):
                    self.character_names.add(name_upper)

        logger.debug(f"Scanned {len(self.character_names)} speaker names")

    def _is_speaker_line(self, line: str) -> Optional[str]:
        """Check if a line is a speaker designation.

        Args:
            line: The line to check (should be stripped).

        Returns:
            The speaker name if this is a speaker line, None otherwise.
        """
        # Must be reasonably short
        if len(line) > 30 or len(line) < 2:
            return None

        # Handle lines with trailing period
        if line.endswith('.'):
            potential_name = line[:-1].strip()
        else:
            # Handle ALL CAPS without period (e.g., "THESEUS")
            # Must be all uppercase letters and spaces
            if not re.match(r'^[A-Z][A-Z\s]+$', line):
                return None
            potential_name = line

        # Skip ACT/SCENE markers and stage directions
        upper_name = potential_name.upper()
        if upper_name.startswith(('ACT', 'SCENE', 'ENTER', 'EXIT', 'EXEUNT')):
            return None

        # Check against known character names (case-insensitive)
        if upper_name in self.character_names:
            return upper_name

        # Also check if it matches the pattern of known multi-word names
        # e.g., "Lady Montague" should match if "LADY MONTAGUE" is known
        normalized = ' '.join(potential_name.split()).upper()
        if normalized in self.character_names:
            return normalized

        return None

    def _roman_to_int(self, roman: str) -> int:
        """Convert Roman numeral to integer."""
        values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
        result = 0
        prev = 0
        for char in reversed(roman.upper()):
            curr = values.get(char, 0)
            if curr < prev:
                result -= curr
            else:
                result += curr
            prev = curr
        return result

    def _int_to_roman(self, num: int) -> str:
        """Convert integer to Roman numeral."""
        val = [10, 9, 5, 4, 1]
        syms = ['X', 'IX', 'V', 'IV', 'I']
        result = ''
        for i, v in enumerate(val):
            while num >= v:
                result += syms[i]
                num -= v
        return result

    def _normalize_act(self, act_str: str) -> int:
        """Normalize act string (Roman numeral, Arabic numeral, or ordinal word) to integer.

        Args:
            act_str: Act identifier like 'III', '3', 'FIRST', 'IV', etc.

        Returns:
            Integer act number.
        """
        act_upper = act_str.upper().strip()
        if act_upper in self.ORDINAL_TO_INT:
            return self.ORDINAL_TO_INT[act_upper]
        # Try Arabic numeral first
        if act_upper.isdigit():
            return int(act_upper)
        return self._roman_to_int(act_upper)

    def _normalize_scene(self, scene_str: str) -> int:
        """Normalize scene string (Roman, Arabic, or Latin ordinal) to integer.

        Args:
            scene_str: Scene identifier like 'III', '3', 'IV', 'SECUNDA', etc.

        Returns:
            Integer scene number.
        """
        scene_str = scene_str.strip().upper()
        if scene_str.isdigit():
            return int(scene_str)
        # Check for Latin ordinals (PRIMA, SECUNDA, etc.)
        if scene_str in self.ORDINAL_TO_INT:
            return self.ORDINAL_TO_INT[scene_str]
        return self._roman_to_int(scene_str)

    def find_scene(self, act: int, scene: int,
                   infer_scenes: bool = False) -> tuple[int, int]:
        """Find the start and end line numbers for a scene.

        Args:
            act: Act number (integer), or 0 for opening prologue
            scene: Scene number (integer), or 0 for prologue
            infer_scenes: If True, use structural inference for minimally-marked
                          First Folio texts

        Returns:
            Tuple of (start_line, end_line) as 0-indexed line numbers.

        Raises:
            ValueError: If scene not found.
        """
        # Handle prologue (scene=0) and epilogue (scene=-1)
        if scene == 0:
            return self._find_prologue(act)
        if scene == -1:
            return self._find_epilogue()

        # For minimally-marked First Folio texts, use structural inference
        format_type = self._detect_format()
        if format_type == 'folio_minimal' and infer_scenes:
            boundaries = self._infer_scene_boundaries()
            if scene in boundaries:
                logger.info(f"Using inferred scene boundary for scene {scene}")
                return boundaries[scene]
            raise ValueError(
                f"Inferred scene {scene} not found (available: 1-{len(boundaries)})"
            )

        # Use integer comparison for flexibility with different formats
        target_act = act
        target_scene = scene

        current_act = None
        scene_start = None
        scene_end = None

        for i, line in enumerate(self.lines):
            stripped = line.strip()

            # Check for combined ACT + SCENE on same line (e.g., "ACT IV. SCENE I.")
            combined_match = self.ACT_SCENE_COMBINED_PATTERN.match(stripped)
            if combined_match:
                line_act = self._normalize_act(combined_match.group(1))
                line_scene = self._normalize_scene(combined_match.group(2))

                # If we already found our scene, this marks the end
                if scene_start is not None:
                    scene_end = i - 1
                    break

                # Update current act and check if this is our target
                current_act = line_act
                if line_act == target_act and line_scene == target_scene:
                    scene_start = i
                continue

            # Check for act header (standalone)
            act_match = self.ACT_PATTERN.match(stripped)
            if act_match:
                # Normalize to integer (handles both Roman and ordinal words)
                current_act = self._normalize_act(act_match.group(1))
                continue

            # Check for scene header (standalone)
            scene_match = self.SCENE_PATTERN.match(stripped)
            if scene_match:
                scene_num = self._normalize_scene(scene_match.group(1))

                # If we already found our scene, this marks the end
                if scene_start is not None:
                    scene_end = i - 1
                    break

                # Check if this is our target scene (integer comparison)
                if current_act == target_act and scene_num == target_scene:
                    scene_start = i

        # If scene_end not set, scene goes to end of file
        if scene_start is not None and scene_end is None:
            scene_end = len(self.lines) - 1

        if scene_start is None:
            raise ValueError(
                f"Scene {act}.{scene} (Act {self._int_to_roman(act)}, "
                f"Scene {self._int_to_roman(scene)}) not found in {self.play_file}"
            )

        return scene_start, scene_end

    def _find_prologue(self, act: int) -> tuple[int, int]:
        """Find the prologue for a specific act.

        Args:
            act: Act number (1-5), or 0 for opening prologue before Act 1

        Returns:
            Tuple of (start_line, end_line) as 0-indexed line numbers.

        Raises:
            ValueError: If prologue not found.
        """
        current_act = 0  # 0 = before any act header (opening prologue)
        prologue_start = None
        prologue_end = None

        for i, line in enumerate(self.lines):
            stripped = line.strip()

            # Check for act header
            act_match = self.ACT_PATTERN.match(stripped)
            if act_match:
                current_act = self._normalize_act(act_match.group(1))
                continue

            # Check for prologue header
            if self.PROLOGUE_PATTERN.match(stripped):
                # If we already found our prologue, this marks the end
                if prologue_start is not None:
                    prologue_end = i - 1
                    break

                # Check if this is our target prologue
                # act=0 means opening prologue (before any ACT marker)
                # act=N means the prologue right after ACT N header
                if current_act == act:
                    prologue_start = i

            # Scene header also ends the prologue
            scene_match = self.SCENE_PATTERN.match(stripped)
            if scene_match and prologue_start is not None:
                prologue_end = i - 1
                break

        # If prologue_end not set, prologue goes to next major marker
        if prologue_start is not None and prologue_end is None:
            prologue_end = len(self.lines) - 1

        if prologue_start is None:
            if act == 0:
                raise ValueError(f"Opening prologue not found in {self.play_file}")
            raise ValueError(
                f"Prologue for Act {self._int_to_roman(act)} not found in "
                f"{self.play_file}"
            )

        return prologue_start, prologue_end

    def _find_epilogue(self) -> tuple[int, int]:
        """Find the epilogue section.

        Returns:
            Tuple of (start_line, end_line) as 0-indexed line numbers.

        Raises:
            ValueError: If epilogue not found.
        """
        epilogue_start = None

        for i, line in enumerate(self.lines):
            if self.EPILOGUE_PATTERN.match(line.strip()):
                epilogue_start = i
                break

        if epilogue_start is None:
            raise ValueError(f"Epilogue not found in {self.play_file}")

        # Epilogue goes to end of file
        return epilogue_start, len(self.lines) - 1

    def extract_speeches(self, start_line: int, end_line: int) -> list[Speech]:
        """Extract individual speeches from a line range.

        Args:
            start_line: Starting line number (0-indexed)
            end_line: Ending line number (0-indexed)

        Returns:
            List of Speech objects.
        """
        speeches = []
        current_speaker = None
        current_lines = []
        speech_start = None

        for i in range(start_line, end_line + 1):
            line = self.lines[i].rstrip()
            stripped = line.strip()

            # Check for new speaker using cast-list-aware detection
            speaker_name = self._is_speaker_line(stripped) if stripped else None

            # Handle empty lines - preserve them within speeches for proper formatting
            if not stripped:
                # Only add empty line if we're inside a speech
                if current_speaker and current_lines:
                    current_lines.append('')
                continue

            # Check for pure stage directions (lines that are only [bracketed text])
            # Include them in speech text for display, but they won't be analyzed line-by-line
            is_stage_direction = self.STAGE_DIR_PATTERN.match(stripped)

            if speaker_name:
                # Save previous speech if exists
                if current_speaker and current_lines:
                    speech_text = f"{current_speaker}.\n" + "\n".join(current_lines)
                    speeches.append(Speech(
                        speaker=current_speaker,
                        lines=current_lines,
                        text=speech_text,
                        line_start=speech_start,
                        line_end=i - 1
                    ))

                # Start new speech (speaker_name is already uppercase)
                current_speaker = speaker_name
                current_lines = []
                speech_start = i
                continue

            # Add line to current speech (if we have a speaker)
            if current_speaker:
                current_lines.append(line)

        # Don't forget the last speech
        if current_speaker and current_lines:
            speech_text = f"{current_speaker}.\n" + "\n".join(current_lines)
            speeches.append(Speech(
                speaker=current_speaker,
                lines=current_lines,
                text=speech_text,
                line_start=speech_start,
                line_end=end_line
            ))

        # Filter out speeches with no actual dialogue (only stage directions)
        speeches = [s for s in speeches if s.has_dialogue]

        return speeches


class SceneAnalyzer:
    """Analyze an entire scene speech by speech."""

    def __init__(self, play_file: Path, act: int, scene: int,
                 output_dir: Path = None, merge_threshold: int = 0,
                 retry_count: int = 3, retry_delay: int = 30,
                 infer_scenes: bool = False):
        """Initialize scene analyzer.

        Args:
            play_file: Path to play text file.
            act: Act number (integer).
            scene: Scene number (integer).
            output_dir: Directory for output files. Defaults to GLOSSES_DIR.
            merge_threshold: Minimum lines per chunk. Speeches are merged until
                           this threshold is reached. 0 = no merging.
            retry_count: Number of times to retry failed API calls.
            retry_delay: Initial delay in seconds between retries (exponential).
            infer_scenes: If True, infer scene boundaries for minimally-marked
                         First Folio texts using Exeunt/Enter patterns.
        """
        self.play_file = Path(play_file)
        self.act = act
        self.scene = scene
        self.backend = create_backend('claude-code')
        self.output_dir = output_dir or GLOSSES_DIR
        self.merge_threshold = merge_threshold
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.infer_scenes = infer_scenes
        self.db = GlossDatabase()
        self.db.setup()  # Ensure tables exist

        # Parse play
        self.parser = PlayParser(play_file)

        # Extract play name from filename
        self.play_name = self.play_file.stem.replace('_gut', '').replace('_', '-')

    def _merge_speeches_into_chunks(self, speeches: list[Speech]) -> list[SpeechChunk]:
        """Merge consecutive speeches into larger chunks for processing.

        Chunking rules:
        - A single speech (monologue) is NEVER split, regardless of length
        - Multiple speeches are grouped until adding another would exceed threshold
        - Threshold only applies when deciding whether to ADD another speech
        - This ensures monologues stay intact while dialogue gets grouped efficiently

        Args:
            speeches: List of individual Speech objects.

        Returns:
            List of SpeechChunk objects.
        """
        if self.merge_threshold <= 0:
            # No merging - each speech becomes its own chunk
            return [
                SpeechChunk(speeches=[s], text=s.text)
                for s in speeches
            ]

        chunks = []
        current_speeches = []
        current_lines = 0

        for speech in speeches:
            # Monologue rule: A chunk with one speech can exceed threshold
            # (we never split a single character's continuous dialogue)
            # Multi-speech rule: Close chunk before exceeding threshold
            is_monologue = len(current_speeches) == 0
            would_exceed = current_lines + speech.line_count > self.merge_threshold

            if not is_monologue and would_exceed:
                # Close current chunk - multiple speeches would exceed threshold
                combined_text = "\n\n".join(s.text.rstrip() for s in current_speeches)
                chunks.append(SpeechChunk(
                    speeches=current_speeches,
                    text=combined_text
                ))
                current_speeches = []
                current_lines = 0

            # Add speech to current chunk
            # (always succeeds - monologues can exceed threshold)
            current_speeches.append(speech)
            current_lines += speech.line_count

        # Don't forget remaining speeches
        if current_speeches:
            combined_text = "\n\n".join(s.text.rstrip() for s in current_speeches)
            chunks.append(SpeechChunk(
                speeches=current_speeches,
                text=combined_text
            ))

        return chunks

    def _get_metadata(self, speech: Speech) -> dict:
        """Build metadata dict for a speech."""
        return {
            'source_file': str(self.play_file.name),
            'tag': f"{self.play_name}_act{self.act}_scene{self.scene}",
            'line_number': speech.line_start,
            'char_position': 0,
            'character': speech.speaker,
            'act': str(self.act),
            'scene': str(self.scene),
            'play_name': self.play_name,
        }

    def _analyze_speech(self, speech: Speech) -> str:
        """Generate line-by-line analysis for a single speech.

        Args:
            speech: The Speech object to analyze.

        Returns:
            The analysis text.
        """
        # Check cache first
        existing = self.db.get_existing(speech.hash, 'line-by-line')
        if existing:
            logger.info(f"  Cache hit for {speech.speaker} ({speech.line_count} lines)")
            return existing['text']

        logger.info(f"  Generating analysis for {speech.speaker} "
                   f"({speech.line_count} lines)...")

        # Build prompt and generate
        prompt_builder = PromptBuilder(speech.text)
        prompt = prompt_builder.build_line_by_line_prompt()
        raw_analysis = self.backend.generate(prompt)

        # Prepend speaker name only if not already present in the analysis
        speaker_prefix = f"{speech.speaker.upper()}."
        if raw_analysis.lstrip().startswith(speaker_prefix):
            analysis = raw_analysis
        else:
            analysis = f"{speaker_prefix}\n\n{raw_analysis}"

        # Save to database
        metadata = self._get_metadata(speech)

        passage_id = self.db.get_or_create_passage(
            speech.hash, speech.text, metadata
        )

        # Save as gloss type 'line-by-line'
        filename = f"{speech.hash[:8]}_{speech.speaker.lower()}_line-by-line.md"
        self.db.save(
            speech.hash, speech.text, analysis, filename,
            'line-by-line', metadata
        )

        # Also save to addenda for the full analysis
        self.db.save_addendum(speech.hash, "Line-by-line analysis", analysis)

        return analysis

    def _analyze_chunk(self, chunk: SpeechChunk) -> str:
        """Generate line-by-line analysis for a chunk of speeches.

        Args:
            chunk: The SpeechChunk object to analyze.

        Returns:
            The analysis text.

        Raises:
            RuntimeError: If API call fails after all retries exhausted.
        """
        # Check cache first using chunk hash
        existing = self.db.get_existing(chunk.hash, 'line-by-line')
        if existing:
            logger.info(f"  Cache hit for chunk: {chunk.speaker_summary} "
                       f"({chunk.line_count} lines)")
            return existing['text']

        logger.info(f"  Generating analysis for chunk: {chunk.speaker_summary} "
                   f"({chunk.line_count} lines)...")

        # Build prompt and generate with retry logic
        prompt_builder = PromptBuilder(chunk.text)
        prompt = prompt_builder.build_line_by_line_prompt()

        last_error = None
        for attempt in range(self.retry_count + 1):
            try:
                raw_analysis = self.backend.generate(prompt)
                break  # Success, exit retry loop
            except RuntimeError as e:
                last_error = e
                error_msg = str(e).lower()

                # Check if it's a rate limit error
                is_rate_limit = 'rate' in error_msg or 'limit' in error_msg

                if attempt < self.retry_count:
                    # Calculate delay with exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    if is_rate_limit:
                        # Rate limits get longer delays
                        delay = max(delay, 60)

                    logger.warning(
                        f"  API call failed (attempt {attempt + 1}/{self.retry_count + 1}): {e}"
                    )
                    logger.info(f"  Retrying in {delay} seconds...")

                    print_structured_error(
                        ErrorCode.API_RATE_LIMIT if is_rate_limit else ErrorCode.API_FAILURE,
                        str(e),
                        context={
                            "chunk": chunk.speaker_summary,
                            "attempt": f"{attempt + 1}/{self.retry_count + 1}"
                        },
                        suggestion=f"Automatic retry in {delay} seconds",
                        action="Waiting before retry"
                    )

                    time.sleep(delay)
                else:
                    # All retries exhausted
                    logger.error(
                        f"  API call failed after {self.retry_count + 1} attempts: {e}"
                    )
                    raise RuntimeError(
                        f"API call failed after {self.retry_count + 1} attempts: {last_error}"
                    ) from last_error

        # For single-speech chunks, prepend the speaker name only if not present
        # For multi-speech chunks, the raw analysis handles speaker names
        # since the input text includes them before each speech
        if len(chunk.speeches) == 1:
            speaker_prefix = f"{chunk.speeches[0].speaker.upper()}."
            if raw_analysis.lstrip().startswith(speaker_prefix):
                analysis = raw_analysis
            else:
                analysis = f"{speaker_prefix}\n\n{raw_analysis}"
        else:
            analysis = raw_analysis

        # Save to database using first speech's metadata
        first_speech = chunk.speeches[0]
        metadata = self._get_metadata(first_speech)
        metadata['character'] = chunk.speaker_summary

        self.db.get_or_create_passage(chunk.hash, chunk.text, metadata)

        # Save as gloss type 'line-by-line'
        filename = f"{chunk.hash[:8]}_chunk_line-by-line.md"
        self.db.save(
            chunk.hash, chunk.text, analysis, filename,
            'line-by-line', metadata
        )

        # Also save to addenda
        self.db.save_addendum(chunk.hash, "Line-by-line analysis", analysis)

        return analysis

    def _clean_analysis(self, analysis: str) -> str:
        """Remove trailing separators from analysis text.

        Args:
            analysis: Raw analysis text from Claude.

        Returns:
            Cleaned analysis without trailing '---' separators.
        """
        cleaned = analysis.rstrip()
        while cleaned.endswith('---'):
            cleaned = cleaned[:-3].rstrip()
        return cleaned

    def _format_scene_document(self, chunks: list[SpeechChunk],
                                analyses: list[str],
                                scene_header: str) -> str:
        """Format the complete scene analysis as markdown.

        Args:
            chunks: List of SpeechChunk objects.
            analyses: List of analysis strings (parallel to chunks).
            scene_header: The scene header line from the source.

        Returns:
            Formatted markdown document.
        """
        lines = []

        # Header
        lines.append(f"# {self.play_name.replace('-', ' ').title()}")
        lines.append(f"## Act {self.act}, Scene {self.scene}")
        lines.append("")
        lines.append(f"*{scene_header.strip()}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Each chunk with analysis
        speech_num = 1
        for chunk, analysis in zip(chunks, analyses):
            # If single-speech chunk, use simple format
            if len(chunk.speeches) == 1:
                speech = chunk.speeches[0]
                anchor = f"speech-{speech_num}"
                lines.append(f"<a name=\"{anchor}\"></a>")
                lines.append(f"### {speech_num}. {speech.speaker}")
                lines.append("")
                lines.append("#### Original Text")
                lines.append("```")
                lines.append(speech.text)
                lines.append("```")
                lines.append("")
                lines.append("#### Line-by-Line Analysis")
                lines.append("")
                lines.append(self._clean_analysis(analysis))
                lines.append("")
                lines.append("---")
                lines.append("")
                speech_num += 1
            else:
                # Multi-speech chunk
                lines.append(f"### Speeches {speech_num}-"
                            f"{speech_num + len(chunk.speeches) - 1}")
                lines.append("")
                lines.append("#### Original Text")
                lines.append("```")
                for speech in chunk.speeches:
                    anchor = f"speech-{speech_num}"
                    lines.append(f"<!-- {anchor} -->")
                    lines.append(speech.text)
                    lines.append("")
                    speech_num += 1
                lines.append("```")
                lines.append("")
                lines.append("#### Line-by-Line Analysis")
                lines.append("")
                lines.append(self._clean_analysis(analysis))
                lines.append("")
                lines.append("---")
                lines.append("")

        # Footer
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append(f"*Source: {self.play_file.name}*")

        return "\n".join(lines)

    def analyze(self, dry_run: bool = False, status_only: bool = False) -> Path:
        """Analyze the entire scene.

        Args:
            dry_run: If True, just show what would be processed without
                    calling the API.
            status_only: If True, just check cache status and exit with
                        code 0 if all cached, 1 if work needed.

        Returns:
            Path to the generated markdown file.
        """
        # Log what we're analyzing (handle prologues/epilogue specially)
        if self.scene == -1:
            logger.info(f"Analyzing {self.play_name} Epilogue...")
        elif self.scene == 0:
            if self.act == 0:
                logger.info(f"Analyzing {self.play_name} Prologue...")
            else:
                logger.info(f"Analyzing {self.play_name} Act {self.act} Prologue...")
        else:
            logger.info(f"Analyzing {self.play_name} Act {self.act}, "
                       f"Scene {self.scene}...")

        # Find scene boundaries
        start_line, end_line = self.parser.find_scene(
            self.act, self.scene, infer_scenes=self.infer_scenes
        )
        scene_header = self.parser.lines[start_line].strip()
        logger.info(f"Found scene at lines {start_line}-{end_line}: {scene_header}")

        # Extract speeches
        speeches = self.parser.extract_speeches(start_line, end_line)
        logger.info(f"Found {len(speeches)} speeches")

        # Skip if no dialogue found (only stage directions)
        if not speeches:
            logger.info("No dialogue found in this section, skipping")
            if dry_run:
                print(f"\nSkipping: No dialogue found (only stage directions)")
            return None

        # Merge into chunks if threshold is set
        chunks = self._merge_speeches_into_chunks(speeches)
        if self.merge_threshold > 0:
            logger.info(f"Merged into {len(chunks)} chunks "
                       f"(threshold: {self.merge_threshold} lines)")

        # Check cache status for all chunks
        cached_count = 0
        new_chunks = []
        for chunk in chunks:
            if self.db.get_existing(chunk.hash, 'line-by-line'):
                cached_count += 1
            else:
                new_chunks.append(chunk)
        new_count = len(chunks) - cached_count

        # Build scene label for display
        if self.scene == -1:
            scene_label = "Epilogue"
        elif self.scene == 0:
            scene_label = "Prologue" if self.act == 0 else f"Act {self.act} Prologue"
        else:
            scene_label = f"Act {self.act} Scene {self.scene}"

        # Status-only mode: just report and exit
        if status_only:
            if new_count == 0:
                print(f"{scene_label}: {len(chunks)} chunks (all cached)")
                sys.exit(0)
            else:
                print(f"{scene_label}: {len(chunks)} chunks "
                      f"({cached_count} cached, {new_count} to process)")
                sys.exit(1)

        # Show cache summary before processing
        if new_count == 0:
            print(f"{scene_label}: {len(chunks)} chunks (all cached)")
        else:
            print(f"{scene_label}: {len(chunks)} chunks "
                  f"({cached_count} cached, {new_count} to process)")

        if dry_run:
            if self.scene == -1:
                print(f"\nDry run: {self.play_name} Epilogue")
            elif self.scene == 0:
                if self.act == 0:
                    print(f"\nDry run: {self.play_name} Prologue")
                else:
                    print(f"\nDry run: {self.play_name} Act {self.act} Prologue")
            else:
                print(f"\nDry run: {self.play_name} Act {self.act}, Scene {self.scene}")
            print(f"Scene location: lines {start_line}-{end_line}")
            print(f"Total speeches: {len(speeches)}")
            if self.merge_threshold > 0:
                print(f"Merge threshold: {self.merge_threshold} lines")
                print(f"Chunks after merging: {len(chunks)}")
                print("\nChunks to process:")
                for i, chunk in enumerate(chunks, 1):
                    cached = self.db.get_existing(chunk.hash, 'line-by-line')
                    status = "[CACHED]" if cached else "[NEW]"
                    print(f"  {i}. {chunk.speaker_summary}: "
                          f"{chunk.line_count} lines {status}")
            else:
                print("\nSpeeches to process:")
                for i, speech in enumerate(speeches, 1):
                    cached = self.db.get_existing(speech.hash, 'line-by-line')
                    status = "[CACHED]" if cached else "[NEW]"
                    print(f"  {i}. {speech.speaker}: "
                          f"{speech.line_count} lines {status}")
            return None

        # Analyze each chunk
        analyses = []
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)}: "
                       f"{chunk.speaker_summary}")
            analysis = self._analyze_chunk(chunk)
            analyses.append(analysis)

        # Generate output document
        document = self._format_scene_document(chunks, analyses, scene_header)

        # Save to file in play-specific subdirectory
        play_dir = self.output_dir / self.play_name
        play_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename based on act/scene (handle prologues/epilogue specially)
        if self.scene == -1:
            output_filename = "epilogue_line-by-line.md"
        elif self.scene == 0:
            if self.act == 0:
                output_filename = "prologue_line-by-line.md"
            else:
                output_filename = f"act{self.act}_prologue_line-by-line.md"
        else:
            output_filename = f"act{self.act}_scene{self.scene}_line-by-line.md"
        output_path = play_dir / output_filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(document)

        logger.info(f"Saved scene analysis to {output_path}")
        return output_path

    def export_chunks(self, gloss_type: str = 'line-by-line') -> dict:
        """Export chunk data as JSON for external processing.

        Returns a dictionary with scene metadata and chunk information,
        suitable for processing by Claude Code directly without API calls.

        Args:
            gloss_type: Type of gloss for cache lookup (default: line-by-line)

        Returns:
            Dictionary with scene info and chunks ready for processing.
        """
        # Find scene boundaries
        start_line, end_line = self.parser.find_scene(
            self.act, self.scene, infer_scenes=self.infer_scenes
        )
        scene_header = self.parser.lines[start_line].strip()

        # Extract speeches
        speeches = self.parser.extract_speeches(start_line, end_line)

        # Skip if no dialogue
        if not speeches:
            return {
                "play_name": self.play_name,
                "act": self.act,
                "scene": self.scene,
                "scene_header": scene_header,
                "start_line": start_line,
                "end_line": end_line,
                "chunks": [],
                "error": "No dialogue found (only stage directions)"
            }

        # Merge into chunks
        chunks = self._merge_speeches_into_chunks(speeches)

        # Build chunk data
        chunk_data = []
        for i, chunk in enumerate(chunks, 1):
            cached = self.db.get_existing(chunk.hash, gloss_type)
            chunk_info = {
                "index": i,
                "hash": chunk.hash,
                "speaker_summary": chunk.speaker_summary,
                "line_count": chunk.line_count,
                "speech_count": len(chunk.speeches),
                "text": chunk.text,
                "cached": cached is not None,
                "cached_text": cached['text'] if cached else None
            }
            chunk_data.append(chunk_info)

        # Build output directory path
        play_dir = self.output_dir / self.play_name

        # Generate output filename
        if self.scene == -1:
            output_filename = f"epilogue_{gloss_type}.md"
        elif self.scene == 0:
            if self.act == 0:
                output_filename = f"prologue_{gloss_type}.md"
            else:
                output_filename = f"act{self.act}_prologue_{gloss_type}.md"
        else:
            output_filename = f"act{self.act}_scene{self.scene}_{gloss_type}.md"

        return {
            "play_name": self.play_name,
            "play_file": str(self.play_file),
            "act": self.act,
            "scene": self.scene,
            "scene_header": scene_header,
            "start_line": start_line,
            "end_line": end_line,
            "total_speeches": len(speeches),
            "merge_threshold": self.merge_threshold,
            "gloss_type": gloss_type,
            "output_dir": str(play_dir),
            "output_filename": output_filename,
            "chunks": chunk_data
        }


def parse_act_scene_string(act_scene: str) -> tuple[int, int]:
    """Parse 'Act IV, Scene VII', 'Prologue', or 'Epilogue' format to integers.

    Accepts formats like:
    - "Act IV, Scene VII"
    - "Act 4, Scene 7"
    - "act iv scene vii"
    - "Act IV Scene 7"
    - "Prologue" (returns act=0, scene=0 for opening prologue)
    - "Act 2 Prologue" or "Act II Prologue" (returns act=N, scene=0)
    - "Epilogue" (returns act=0, scene=-1)

    Args:
        act_scene: String in "Act N, Scene M", "Prologue", or "Epilogue" format

    Returns:
        Tuple of (act_number, scene_number) as integers.
        For prologues, scene=0. For epilogue, scene=-1.

    Raises:
        ValueError: If format is not recognized
    """
    # Roman numeral conversion
    def roman_to_int(roman: str) -> int:
        values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
        result = 0
        prev = 0
        for char in reversed(roman.upper()):
            curr = values.get(char, 0)
            if curr < prev:
                result -= curr
            else:
                result += curr
            prev = curr
        return result

    # Normalize input
    text = act_scene.strip().upper()

    # Check for "Prologue" or "Scene Prologue" (opening prologue before Act 1)
    if text in ('PROLOGUE', 'SCENE PROLOGUE'):
        return 0, 0

    # Check for "Epilogue" or "Scene Epilogue"
    if text in ('EPILOGUE', 'SCENE EPILOGUE'):
        return 0, -1

    # Check for "Act N Prologue" format
    prologue_pattern = r'ACT\s+([IVXLC]+|\d+)[,\s]+PROLOGUE'
    prologue_match = re.match(prologue_pattern, text)
    if prologue_match:
        act_str = prologue_match.group(1)
        if act_str.isdigit():
            act = int(act_str)
        else:
            act = roman_to_int(act_str)
        return act, 0

    # Pattern: "ACT <num>, SCENE <num>" or "ACT <num> SCENE <num>"
    # Where <num> can be Roman (IV) or Arabic (4)
    pattern = r'ACT\s+([IVXLC]+|\d+)[,\s]+SCENE\s+([IVXLC]+|\d+)'
    match = re.match(pattern, text)

    if not match:
        raise ValueError(
            f"Could not parse '{act_scene}'. "
            "Expected format: 'Act IV, Scene VII', 'Act 4, Scene 7', "
            "'Prologue', 'Act 2 Prologue', or 'Epilogue'"
        )

    act_str, scene_str = match.groups()

    # Convert to integers
    if act_str.isdigit():
        act = int(act_str)
    else:
        act = roman_to_int(act_str)

    if scene_str.isdigit():
        scene = int(scene_str)
    else:
        scene = roman_to_int(scene_str)

    return act, scene


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate line-by-line actor analysis for an entire scene',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Using "Act N, Scene M" format (from <M-a> clipboard)
    python scene_analyzer.py henry_v_gut.txt "Act IV, Scene VII"

    # Using numeric arguments
    python scene_analyzer.py henry_v_gut.txt 4 7

    # Dry run to see what would be processed
    python scene_analyzer.py henry_v_gut.txt "Act IV, Scene VII" --dry-run

    # Merge small speeches into 42-line chunks (fewer Claude Code calls)
    python scene_analyzer.py henry_v_gut.txt 4 7 --merge 42
        """
    )
    parser.add_argument(
        'play_file',
        type=Path,
        help='Path to the play text file'
    )
    parser.add_argument(
        'act_scene',
        nargs='*',
        help='Act and scene: either "Act IV, Scene VII" or two numbers: 4 7 (not required for --validate-translations)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=Path,
        default=None,
        help=f'Output directory (default: {GLOSSES_DIR})'
    )
    parser.add_argument(
        '--merge', '-m',
        type=int,
        default=0,
        metavar='LINES',
        help='Merge speeches into chunks of at least N lines (fewer calls)'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be processed without calling Claude Code'
    )
    parser.add_argument(
        '--status', '-s',
        action='store_true',
        help='Show cache status only (exit code 0 if all cached, 1 if work needed)'
    )
    parser.add_argument(
        '--retry', '-r',
        type=int,
        default=3,
        metavar='N',
        help='Retry failed API calls N times (default: 3)'
    )
    parser.add_argument(
        '--retry-delay',
        type=int,
        default=30,
        metavar='SECONDS',
        help='Initial delay between retries in seconds (default: 30)'
    )
    parser.add_argument(
        '--validate', '-v',
        action='store_true',
        help='Validate scene exists in play file (exit 0 if found, 1 if not)'
    )
    parser.add_argument(
        '--export-chunks',
        action='store_true',
        help='Export chunk data as JSON for external processing (no API calls)'
    )
    parser.add_argument(
        '--save-chunk',
        metavar='HASH',
        help='Save analysis for a specific chunk hash (reads analysis from stdin)'
    )
    parser.add_argument(
        '--build-from-cache',
        action='store_true',
        help='Build markdown from cached analyses (all chunks must be cached)'
    )
    parser.add_argument(
        '--gloss-type',
        default='line-by-line',
        metavar='TYPE',
        help='Gloss type for caching/output (default: line-by-line, also: sounds)'
    )
    parser.add_argument(
        '--infer-scenes',
        action='store_true',
        help='For minimally-marked First Folio texts, infer scene boundaries '
             'from Exeunt/Enter patterns instead of explicit markers'
    )
    parser.add_argument(
        '--line-translations-only',
        action='store_true',
        help='Only save to line_translations table (skip passages/glosses/addenda)'
    )
    parser.add_argument(
        '--validate-translations',
        action='store_true',
        help='Check if DB translations match source file content'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Delete orphaned translations (use with --validate-translations)'
    )

    args = parser.parse_args()

    # Validate translations mode: check DB entries against source file
    if args.validate_translations:
        source_file = str(args.play_file.resolve())
        if not args.play_file.exists():
            print(f"Error: Source file not found: {source_file}", file=sys.stderr)
            sys.exit(1)
        mismatches = validate_line_translations(source_file, fix=args.fix)
        sys.exit(1 if mismatches else 0)

    # Parse act/scene from arguments
    act_scene_args = args.act_scene
    if not act_scene_args:
        print("Error: act_scene argument is required for this mode", file=sys.stderr)
        sys.exit(1)
    if len(act_scene_args) == 1:
        # Single argument: "Act IV, Scene VII" format
        try:
            act, scene = parse_act_scene_string(act_scene_args[0])
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif len(act_scene_args) == 2:
        # Two arguments: numeric act and scene
        try:
            act = int(act_scene_args[0])
            scene = int(act_scene_args[1])
        except ValueError:
            # Maybe it's "Act IV," "Scene VII" as two args
            combined = ' '.join(act_scene_args)
            try:
                act, scene = parse_act_scene_string(combined)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        # Multiple args - try combining them
        combined = ' '.join(act_scene_args)
        try:
            act, scene = parse_act_scene_string(combined)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate play file exists
    if not args.play_file.exists():
        print_structured_error(
            ErrorCode.FILE_ERROR,
            f"Play file not found: {args.play_file}",
            context={"file": str(args.play_file)},
            suggestion="Check the file path is correct",
            action="Fix path and retry"
        )
        sys.exit(1)

    # Build scene label for error context
    if scene == -1:
        scene_label = "Epilogue"
    elif scene == 0:
        scene_label = "Prologue" if act == 0 else f"Act {act} Prologue"
    else:
        scene_label = f"Act {act} Scene {scene}"

    # Validate mode: just check if scene exists
    if args.validate:
        try:
            parser = PlayParser(args.play_file)
            start_line, end_line = parser.find_scene(
                act, scene, infer_scenes=args.infer_scenes
            )
            scene_header = parser.lines[start_line].strip()
            print(f"✓ {scene_label} - found at line {start_line + 1}: {scene_header}")
            sys.exit(0)
        except ValueError as e:
            print(f"✗ {scene_label} - NOT FOUND", file=sys.stderr)
            print_structured_error(
                ErrorCode.SCENE_NOT_FOUND,
                str(e),
                context={
                    "scene": scene_label,
                    "file": str(args.play_file.name)
                },
                suggestion="Scene may not exist in this edition",
                action="Check play structure or regenerate script"
            )
            sys.exit(1)

    # Export chunks mode: output JSON for external processing
    if args.export_chunks:
        try:
            analyzer = SceneAnalyzer(
                play_file=args.play_file,
                act=act,
                scene=scene,
                output_dir=args.output_dir,
                merge_threshold=args.merge,
                retry_count=args.retry,
                retry_delay=args.retry_delay,
                infer_scenes=args.infer_scenes
            )
            chunk_data = analyzer.export_chunks(gloss_type=args.gloss_type)
            print(json.dumps(chunk_data, indent=2))
            sys.exit(0)
        except ValueError as e:
            error_data = {
                "error": str(e),
                "scene_label": scene_label,
                "play_file": str(args.play_file)
            }
            print(json.dumps(error_data, indent=2))
            sys.exit(1)

    # Save chunk mode: save analysis for a specific chunk hash
    if args.save_chunk:
        try:
            # Read analysis from stdin
            analysis = sys.stdin.read()
            if not analysis.strip():
                print("Error: No analysis provided on stdin", file=sys.stderr)
                sys.exit(1)

            analyzer = SceneAnalyzer(
                play_file=args.play_file,
                act=act,
                scene=scene,
                output_dir=args.output_dir,
                merge_threshold=args.merge,
                retry_count=args.retry,
                retry_delay=args.retry_delay,
                infer_scenes=args.infer_scenes
            )

            # Find the chunk with matching hash
            chunk_data = analyzer.export_chunks(gloss_type=args.gloss_type)
            target_chunk = None
            target_chunk_info = None
            for chunk_info in chunk_data['chunks']:
                if chunk_info['hash'] == args.save_chunk:
                    target_chunk_info = chunk_info
                    break

            if not target_chunk_info:
                print(f"Error: Chunk hash {args.save_chunk} not found in scene",
                      file=sys.stderr)
                sys.exit(1)

            # Build metadata
            metadata = {
                'source_file': str(args.play_file.name),
                'tag': f"{analyzer.play_name}_act{act}_scene{scene}",
                'line_number': 0,
                'char_position': 0,
                'character': target_chunk_info['speaker_summary'],
                'act': str(act),
                'scene': str(scene),
                'play_name': analyzer.play_name,
            }

            # Save to database
            chunk_hash = args.save_chunk
            chunk_text = target_chunk_info['text']
            gloss_type = args.gloss_type

            if args.line_translations_only:
                # Only save to line_translations table
                translations = parse_line_translations(analysis)
                if translations:
                    chunk_start_line = chunk_data.get('start_line', 0)
                    scene_end_line = chunk_data.get('end_line')
                    line_count = save_line_translations(
                        translations=translations,
                        source_file=str(args.play_file),
                        chunk_text=chunk_text,
                        play_name=analyzer.play_name,
                        act=str(act),
                        scene=str(scene),
                        chunk_hash=chunk_hash,
                        play_file_lines=analyzer.parser.lines,
                        chunk_start_line=chunk_start_line,
                        scene_end_line=scene_end_line
                    )
                    print(f"Saved {line_count} line translations")
                else:
                    print("No translations parsed from output")
            else:
                # Save to passages/glosses/addenda
                analyzer.db.get_or_create_passage(chunk_hash, chunk_text, metadata)

                filename = f"{chunk_hash[:8]}_chunk_{gloss_type}.md"
                analyzer.db.save(
                    chunk_hash, chunk_text, analysis, filename,
                    gloss_type, metadata
                )

                # Format addendum question based on gloss type
                addendum_label = {
                    'line-by-line': 'Line-by-line analysis',
                    'sounds': 'Sound-pattern analysis',
                }.get(gloss_type, f'{gloss_type} analysis')
                analyzer.db.save_addendum(chunk_hash, addendum_label, analysis)

            print(f"Saved chunk {chunk_hash[:8]} ({target_chunk_info['speaker_summary']})")
            sys.exit(0)

        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Build from cache mode: build markdown from cached analyses
    if args.build_from_cache:
        try:
            analyzer = SceneAnalyzer(
                play_file=args.play_file,
                act=act,
                scene=scene,
                output_dir=args.output_dir,
                merge_threshold=args.merge,
                retry_count=args.retry,
                retry_delay=args.retry_delay,
                infer_scenes=args.infer_scenes
            )

            # Get chunk data to check cache status
            gloss_type = args.gloss_type
            chunk_data = analyzer.export_chunks(gloss_type=gloss_type)

            if not chunk_data['chunks']:
                print("No chunks found in scene", file=sys.stderr)
                sys.exit(1)

            # Verify all chunks are cached
            missing = []
            for chunk_info in chunk_data['chunks']:
                if not chunk_info['cached']:
                    missing.append(f"{chunk_info['hash'][:8]} ({chunk_info['speaker_summary']})")

            if missing:
                print(f"Error: {len(missing)} chunks not cached:", file=sys.stderr)
                for m in missing:
                    print(f"  - {m}", file=sys.stderr)
                sys.exit(1)

            # Build the markdown document from cached analyses
            # Re-create chunk objects for formatting
            start_line, end_line = analyzer.parser.find_scene(
                act, scene, infer_scenes=analyzer.infer_scenes
            )
            scene_header = analyzer.parser.lines[start_line].strip()
            speeches = analyzer.parser.extract_speeches(start_line, end_line)
            chunks = analyzer._merge_speeches_into_chunks(speeches)

            # Get analyses from cache
            analyses = []
            for chunk in chunks:
                cached = analyzer.db.get_existing(chunk.hash, gloss_type)
                analyses.append(cached['text'])

            # Generate document
            document = analyzer._format_scene_document(chunks, analyses, scene_header)

            # Save to file
            play_dir = analyzer.output_dir / analyzer.play_name
            play_dir.mkdir(parents=True, exist_ok=True)
            output_path = play_dir / chunk_data['output_filename']

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(document)

            print(f"Built {output_path} from {len(chunks)} cached chunks")
            sys.exit(0)

        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        analyzer = SceneAnalyzer(
            play_file=args.play_file,
            act=act,
            scene=scene,
            output_dir=args.output_dir,
            merge_threshold=args.merge,
            retry_count=args.retry,
            retry_delay=args.retry_delay,
            infer_scenes=args.infer_scenes
        )

        output_path = analyzer.analyze(
            dry_run=args.dry_run,
            status_only=args.status
        )

        if output_path:
            print(f"\nScene analysis saved to: {output_path}")

    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            print_structured_error(
                ErrorCode.SCENE_NOT_FOUND,
                error_msg,
                context={
                    "scene": scene_label,
                    "file": str(args.play_file.name)
                },
                suggestion="Check play structure - scene may not exist in this edition",
                action="Skip this scene or regenerate script with /analyze-plays"
            )
        else:
            print_structured_error(
                ErrorCode.VALIDATION_ERROR,
                error_msg,
                context={"scene": scene_label},
                suggestion="Check the arguments are correct"
            )
        sys.exit(1)
    except RuntimeError as e:
        # API/backend failures
        error_msg = str(e)
        if "rate" in error_msg.lower() or "limit" in error_msg.lower():
            print_structured_error(
                ErrorCode.API_RATE_LIMIT,
                error_msg,
                context={"scene": scene_label},
                suggestion="Wait a few minutes then retry, or increase --retry-delay",
                action="Retry the scene (retries were exhausted)"
            )
        else:
            print_structured_error(
                ErrorCode.API_FAILURE,
                error_msg,
                context={"scene": scene_label},
                suggestion="Check network connectivity and API status",
                action="Retry the failed scene"
            )
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        logger.exception("Unexpected error")
        print_structured_error(
            ErrorCode.API_FAILURE,
            str(e),
            context={"scene": scene_label},
            suggestion="Check log file for details",
            action="Review error and retry"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
