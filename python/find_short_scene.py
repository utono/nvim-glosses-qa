#!/usr/bin/env python3
"""Find the shortest scene(s) in a Shakespeare play.

Parses a play file and reports all scenes ordered by line count,
highlighting the shortest for quick rehearsal or study.

Usage:
    python find_short_scene.py <play_file>
    python find_short_scene.py <play_file> --top 5
    python find_short_scene.py <play_file> --all
"""

import argparse
import logging
import sys
from pathlib import Path

# Suppress scene_analyzer logging before import
logging.getLogger('scene_analyzer').setLevel(logging.WARNING)

# Import PlayParser from scene_analyzer (same directory)
from scene_analyzer import PlayParser


def find_all_scenes(play_file: Path) -> list[dict]:
    """Find all scenes in a play file with their line counts.

    Args:
        play_file: Path to the play text file.

    Returns:
        List of dicts with scene info: {act, scene, start_line, end_line,
        line_count, speech_count, header}
    """
    parser = PlayParser(play_file)
    scenes = []

    # Track current act
    current_act = 0

    # Scan for all act/scene markers
    for i, line in enumerate(parser.lines):
        stripped = line.strip()

        # Check for combined ACT + SCENE on same line
        combined_match = parser.ACT_SCENE_COMBINED_PATTERN.match(stripped)
        if combined_match:
            act = parser._normalize_act(combined_match.group(1))
            scene = parser._normalize_scene(combined_match.group(2))
            scenes.append({
                'act': act,
                'scene': scene,
                'header': stripped,
                'start_line': i,
                'end_line': None  # Will be set later
            })
            current_act = act
            continue

        # Check for act header
        act_match = parser.ACT_PATTERN.match(stripped)
        if act_match:
            current_act = parser._normalize_act(act_match.group(1))
            continue

        # Check for scene header
        scene_match = parser.SCENE_PATTERN.match(stripped)
        if scene_match and current_act > 0:
            scene_num = parser._normalize_scene(scene_match.group(1))
            scenes.append({
                'act': current_act,
                'scene': scene_num,
                'header': stripped,
                'start_line': i,
                'end_line': None
            })

        # Check for prologue
        if parser.PROLOGUE_PATTERN.match(stripped):
            scenes.append({
                'act': current_act,
                'scene': 0,
                'header': stripped,
                'start_line': i,
                'end_line': None
            })

        # Check for epilogue
        if parser.EPILOGUE_PATTERN.match(stripped):
            scenes.append({
                'act': 0,
                'scene': -1,
                'header': stripped,
                'start_line': i,
                'end_line': None
            })

    # Set end lines (each scene ends when the next begins)
    for i, scene in enumerate(scenes):
        if i + 1 < len(scenes):
            scene['end_line'] = scenes[i + 1]['start_line'] - 1
        else:
            scene['end_line'] = len(parser.lines) - 1

    # Calculate line counts and extract speeches
    for scene in scenes:
        scene['line_count'] = scene['end_line'] - scene['start_line'] + 1

        # Extract speeches to get speech count
        speeches = parser.extract_speeches(scene['start_line'], scene['end_line'])
        scene['speech_count'] = len(speeches)

        # Calculate dialogue lines (excluding blank lines and headers)
        dialogue_lines = 0
        for s in speeches:
            dialogue_lines += len([ln for ln in s.lines if ln.strip()])
        scene['dialogue_lines'] = dialogue_lines

    return scenes


def format_scene_label(scene: dict) -> str:
    """Format a scene as 'Act N, Scene M' or special labels."""
    if scene['scene'] == -1:
        return "Epilogue"
    if scene['scene'] == 0:
        if scene['act'] == 0:
            return "Prologue"
        return f"Act {scene['act']} Prologue"
    return f"Act {scene['act']}, Scene {scene['scene']}"


def main():
    """CLI entry point."""
    arg_parser = argparse.ArgumentParser(
        description='Find the shortest scene(s) in a Shakespeare play',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python find_short_scene.py twelfth_night_gut.txt
    python find_short_scene.py hamlet_gut.txt --top 5
    python find_short_scene.py henry_v_gut.txt --all
        """
    )
    arg_parser.add_argument(
        'play_file',
        type=Path,
        help='Path to the play text file'
    )
    arg_parser.add_argument(
        '--top', '-t',
        type=int,
        default=3,
        metavar='N',
        help='Show top N shortest scenes (default: 3)'
    )
    arg_parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Show all scenes sorted by length'
    )
    arg_parser.add_argument(
        '--by-dialogue', '-d',
        action='store_true',
        help='Sort by dialogue lines instead of total lines'
    )

    args = arg_parser.parse_args()

    # Validate play file exists
    if not args.play_file.exists():
        print(f"Error: Play file not found: {args.play_file}", file=sys.stderr)
        sys.exit(1)

    # Find all scenes
    try:
        scenes = find_all_scenes(args.play_file)
    except Exception as e:
        print(f"Error parsing play: {e}", file=sys.stderr)
        sys.exit(1)

    if not scenes:
        print("No scenes found in play file", file=sys.stderr)
        sys.exit(1)

    # Sort by line count (or dialogue lines)
    sort_key = 'dialogue_lines' if args.by_dialogue else 'line_count'
    scenes_sorted = sorted(scenes, key=lambda s: s[sort_key])

    # Determine how many to show
    show_count = len(scenes_sorted) if args.all else min(args.top, len(scenes))

    # Extract play name from filename
    play_name = args.play_file.stem.replace('_gut', '').replace('_', ' ').title()

    # Print header
    print(f"\n{play_name} - {len(scenes)} scenes found")
    print("=" * 60)

    if args.by_dialogue:
        print(f"{'Scene':<25} {'Dialogue':<10} {'Total':<10} {'Speeches':<8}")
    else:
        print(f"{'Scene':<25} {'Lines':<10} {'Dialogue':<10} {'Speeches':<8}")
    print("-" * 60)

    # Print scenes
    for i, scene in enumerate(scenes_sorted[:show_count]):
        label = format_scene_label(scene)
        if args.by_dialogue:
            print(f"{label:<25} {scene['dialogue_lines']:<10} "
                  f"{scene['line_count']:<10} {scene['speech_count']:<8}")
        else:
            print(f"{label:<25} {scene['line_count']:<10} "
                  f"{scene['dialogue_lines']:<10} {scene['speech_count']:<8}")

        # Mark the shortest
        if i == 0:
            print(f"  ^ SHORTEST")

    print()

    # Print the shortest scene details
    shortest = scenes_sorted[0]
    print(f"Shortest scene: {format_scene_label(shortest)}")
    print(f"  Lines: {shortest['start_line'] + 1}-{shortest['end_line'] + 1} "
          f"({shortest['line_count']} lines, "
          f"{shortest['dialogue_lines']} dialogue)")
    print(f"  Speeches: {shortest['speech_count']}")
    print(f"  Header: {shortest['header']}")


if __name__ == "__main__":
    main()
