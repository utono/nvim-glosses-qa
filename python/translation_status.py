#!/usr/bin/env python3
"""
Check which scenes in a play already have translations in the database.

Usage:
    python translation_status.py <play-file>
"""

import os
import sqlite3
import sys
from pathlib import Path

# Import from sibling module
sys.path.insert(0, str(Path(__file__).parent))
from generate_play_scripts import analyze_play_structure, get_play_title


def get_cached_scenes(db_path: str, source_file: str) -> dict:
    """Query database for existing translations by act/scene."""
    cached = {}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT act, scene, COUNT(*) as lines
            FROM line_translations
            WHERE source_file = ?
            GROUP BY act, scene
        ''', (source_file,))
        for act, scene, count in cursor.fetchall():
            cached[(str(act), str(scene))] = count
        conn.close()
    except sqlite3.Error:
        pass
    return cached


def print_translation_status(filepath: str, db_path: str = None):
    """Print translation status for all scenes in a play."""
    if db_path is None:
        db_path = os.path.expanduser('~/utono/literature/gloss.db')

    filepath = os.path.expanduser(filepath)
    structure = analyze_play_structure(filepath)
    title = get_play_title(os.path.basename(filepath))
    cached_scenes = get_cached_scenes(db_path, filepath)

    def is_cached(act, scene):
        return cached_scenes.get((str(act), str(scene)), 0)

    print(f'# {title}')
    print()
    print('Legend: ✓ = translated, · = pending')
    print()

    total_cached = 0
    total_scenes = 0

    # Handle opening prologue
    if structure['has_opening_prologue']:
        count = is_cached(0, 0)
        mark = '✓' if count else '·'
        line_info = f' ({count} lines)' if count else ''
        print(f'Prologue  {mark}{line_info}')
        total_scenes += 1
        if count:
            total_cached += 1

    # Process each act
    for act_num in sorted(structure['acts'].keys()):
        act_data = structure['acts'][act_num]
        scenes_in_act = []
        act_cached = 0
        act_total = 0

        # Check for act prologue
        if act_data['has_prologue']:
            count = is_cached(act_num, 0)
            scenes_in_act.append(('P', count))
            act_total += 1
            if count:
                act_cached += 1

        # Check each scene
        for scene_num in act_data['scenes']:
            count = is_cached(act_num, scene_num)
            scenes_in_act.append((str(scene_num), count))
            act_total += 1
            if count:
                act_cached += 1

        # Build scene display string
        scene_parts = []
        for sc, count in scenes_in_act:
            mark = '✓' if count else '·'
            scene_parts.append(f'{sc}{mark}')

        scene_str = ' '.join(scene_parts)
        status = f'[{act_cached}/{act_total}]'

        # Show line counts for translated scenes
        translated = [(sc, c) for sc, c in scenes_in_act if c]
        if translated:
            counts = ', '.join([f'Sc {sc}: {c}' for sc, c in translated])
            print(f'Act {act_num}  {status:7} {scene_str}')
            print(f'         └─ {counts} lines')
        else:
            print(f'Act {act_num}  {status:7} {scene_str}')

        total_cached += act_cached
        total_scenes += act_total

    # Handle epilogue
    if structure['has_epilogue']:
        count = is_cached(6, 0)
        mark = '✓' if count else '·'
        line_info = f' ({count} lines)' if count else ''
        print(f'Epilogue  {mark}{line_info}')
        total_scenes += 1
        if count:
            total_cached += 1

    print()
    print(f'Total: {total_cached}/{total_scenes} scenes translated')


def main():
    if len(sys.argv) < 2:
        print("Usage: python translation_status.py <play-file>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(os.path.expanduser(filepath)):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    print_translation_status(filepath, db_path)


if __name__ == '__main__':
    main()
