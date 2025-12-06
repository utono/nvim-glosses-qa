#!/usr/bin/env python3
"""
Generate gloss-play shell scripts for all Shakespeare plays.
Analyzes play structure and creates corresponding scripts.
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# Roman numeral conversion
ROMAN_MAP = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
    'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
    'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15
}

WORD_MAP = {
    'FIRST': 1, 'SECOND': 2, 'THIRD': 3, 'FOURTH': 4, 'FIFTH': 5
}

def roman_to_int(s):
    """Convert Roman numeral or Arabic numeral to integer."""
    s = s.strip().upper()
    if s in WORD_MAP:
        return WORD_MAP[s]
    if s in ROMAN_MAP:
        return ROMAN_MAP[s]
    # Try Arabic numeral
    if s.isdigit():
        return int(s)
    # Try parsing as compound Roman numeral
    total = 0
    prev = 0
    for char in reversed(s):
        val = ROMAN_MAP.get(char, 0)
        if val < prev:
            total -= val
        else:
            total += val
        prev = val
    return total if total > 0 else None


def analyze_play_structure(filepath):
    """
    Analyze a play file and return its structure.
    Returns dict with:
      - has_opening_prologue: bool
      - acts: {act_num: {'has_prologue': bool, 'scenes': [scene_nums]}}
      - has_epilogue: bool
    """
    structure = {
        'has_opening_prologue': False,
        'acts': defaultdict(lambda: {'has_prologue': False, 'scenes': []}),
        'has_epilogue': False
    }

    # Patterns for structural markers
    # Match PROLOGUE. at start of line
    prologue_pat = re.compile(r'^PROLOGUE\.?\s*$', re.IGNORECASE)
    # Match ACT I. or ACT FIRST. or Act I. or ACT 1 or ACT 1.
    # May be followed by period, space, SCENE, or end of line
    # "ACT III. SCENE I." case - ACT marker with scene on same line
    act_pat = re.compile(
        r'^ACT\s+([IVX]+|\d+|FIRST|SECOND|THIRD|FOURTH|FIFTH)\.?(?:\s|$)',
        re.IGNORECASE
    )
    # Match SCENE I. or SCENE VII. or SCENE 1. or SCENE 1 (at end of line)
    # Followed by period, space, dash, or end of line
    # Can appear at start of line OR after ACT marker on same line
    scene_pat = re.compile(r'SCENE\s+([IVX]+|\d+)(?:[\.\s\-]|$)', re.IGNORECASE)
    # Match EPILOGUE.
    epilogue_pat = re.compile(r'^EPILOGUE\.?\s*$', re.IGNORECASE)

    current_act = 0
    seen_first_act = False

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()

            # Check for PROLOGUE
            if prologue_pat.match(line):
                if not seen_first_act:
                    structure['has_opening_prologue'] = True
                else:
                    # Act prologue
                    structure['acts'][current_act]['has_prologue'] = True
                continue

            # Check for ACT
            act_match = act_pat.match(line)
            if act_match:
                act_num = roman_to_int(act_match.group(1))
                if act_num:
                    current_act = act_num
                    seen_first_act = True
                    # Ensure act entry exists
                    _ = structure['acts'][current_act]
                # Don't continue - check if SCENE is on same line

            # Check for SCENE (can be at start or after ACT on same line)
            scene_match = scene_pat.search(line)
            if scene_match and current_act > 0:
                scene_num = roman_to_int(scene_match.group(1))
                if scene_num and scene_num not in structure['acts'][current_act]['scenes']:
                    structure['acts'][current_act]['scenes'].append(scene_num)
                continue

            # If we matched an ACT but no SCENE, continue
            if act_match:
                continue

            # Check for EPILOGUE
            if epilogue_pat.match(line):
                structure['has_epilogue'] = True

    # Convert defaultdict to regular dict
    structure['acts'] = dict(structure['acts'])
    return structure


def filename_to_play_name(filename):
    """Convert filename to play-name format."""
    # Remove _gut.txt or .txt suffix
    name = re.sub(r'_gut\.txt$|\.txt$', '', filename)
    # Replace underscores with hyphens
    name = name.replace('_', '-')
    return name


def play_name_to_title(name):
    """Convert play-name to Title Case for display."""
    words = name.replace('-', ' ').split()
    # Handle special cases
    small_words = {'of', 'the', 'and', 'a', 'in', 'for', 'to', 'at'}
    titled = []
    for i, w in enumerate(words):
        if i == 0 or w.lower() not in small_words:
            titled.append(w.capitalize())
        else:
            titled.append(w.lower())
    return ' '.join(titled)


def generate_script(play_path, structure, output_dir):
    """Generate the gloss-play shell script for a play."""
    filename = os.path.basename(play_path)
    play_name = filename_to_play_name(filename)
    play_title = play_name_to_title(play_name)

    # Count total scenes
    total_scenes = 0
    if structure['has_opening_prologue']:
        total_scenes += 1
    for act_num, act_data in sorted(structure['acts'].items()):
        if act_data['has_prologue']:
            total_scenes += 1
        total_scenes += len(act_data['scenes'])
    if structure['has_epilogue']:
        total_scenes += 1

    # Generate status checks
    status_checks = []
    validate_checks = []
    process_sections = []

    # Opening prologue
    if structure['has_opening_prologue']:
        status_checks.append('''
    # Prologue (Opening)
    OUTPUT=$(python "$ANALYZER" "$PLAY" 0 0 --merge "$MERGE" --status 2>/dev/null)
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        CHUNKS=$(echo "$OUTPUT" | grep -oP '\\d+ chunks' | head -1 | grep -oP '\\d+' || echo "?")
        echo "Prologue (Opening): $CHUNKS chunks (cached)"
        ((CACHED++))
    else
        CHUNKS=$(echo "$OUTPUT" | grep -oP '\\d+ chunks' | head -1 | grep -oP '\\d+' || echo "?")
        echo "Prologue (Opening): $CHUNKS chunks (0 cached, $CHUNKS to process)"
        ((PENDING++))
    fi''')

        validate_checks.append('''
    if python "$ANALYZER" "$PLAY" 0 0 --validate 2>/dev/null; then
        ((VALID++))
        echo "  ✓ Prologue (Opening)"
    else
        ((INVALID++))
        echo "  ✗ Prologue (Opening) - NOT FOUND"
    fi''')

        process_sections.append('''
# Opening Prologue
if matches_filter 0 0; then
    echo "--- Prologue (Opening) ---"
    if [ -n "$RESUME_MODE" ]; then
        if python "$ANALYZER" "$PLAY" 0 0 --merge "$MERGE" --status 2>/dev/null; then
            echo "[SKIPPED] Prologue (Opening) - fully cached"
            ((SKIPPED++))
        else
            if python "$ANALYZER" "$PLAY" 0 0 --merge "$MERGE" $DRY_RUN 2>&1 | tee -a "$LOG_FILE"; then
                ((SUCCESSFUL++))
            else
                ((ERRORS++))
                FAILED_SCENES="$FAILED_SCENES
  Prologue (Opening): exit code $?"
                echo "[FAILED] Prologue (Opening)"
            fi
        fi
    else
        if python "$ANALYZER" "$PLAY" 0 0 --merge "$MERGE" $DRY_RUN 2>&1 | tee -a "$LOG_FILE"; then
            ((SUCCESSFUL++))
        else
            ((ERRORS++))
            FAILED_SCENES="$FAILED_SCENES
  Prologue (Opening): exit code $?"
            echo "[FAILED] Prologue (Opening)"
        fi
    fi
fi''')

    # Acts and scenes
    for act_num in sorted(structure['acts'].keys()):
        act_data = structure['acts'][act_num]

        # Act prologue
        if act_data['has_prologue']:
            status_checks.append(f'''
    # Act {act_num} Prologue
    OUTPUT=$(python "$ANALYZER" "$PLAY" {act_num} 0 --merge "$MERGE" --status 2>/dev/null)
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        CHUNKS=$(echo "$OUTPUT" | grep -oP '\\d+ chunks' | head -1 | grep -oP '\\d+' || echo "?")
        echo "Act {act_num} Prologue: $CHUNKS chunks (cached)"
        ((CACHED++))
    else
        CHUNKS=$(echo "$OUTPUT" | grep -oP '\\d+ chunks' | head -1 | grep -oP '\\d+' || echo "?")
        echo "Act {act_num} Prologue: $CHUNKS chunks (0 cached, $CHUNKS to process)"
        ((PENDING++))
    fi''')

            validate_checks.append(f'''
    if python "$ANALYZER" "$PLAY" {act_num} 0 --validate 2>/dev/null; then
        ((VALID++))
        echo "  ✓ Act {act_num} Prologue"
    else
        ((INVALID++))
        echo "  ✗ Act {act_num} Prologue - NOT FOUND"
    fi''')

            process_sections.append(f'''
# Act {act_num} Prologue
if matches_filter {act_num} 0; then
    echo "--- Act {act_num}, Prologue ---"
    if [ -n "$RESUME_MODE" ]; then
        if python "$ANALYZER" "$PLAY" {act_num} 0 --merge "$MERGE" --status 2>/dev/null; then
            echo "[SKIPPED] Act {act_num}, Prologue - fully cached"
            ((SKIPPED++))
        else
            if python "$ANALYZER" "$PLAY" {act_num} 0 --merge "$MERGE" $DRY_RUN 2>&1 | tee -a "$LOG_FILE"; then
                ((SUCCESSFUL++))
            else
                ((ERRORS++))
                FAILED_SCENES="$FAILED_SCENES
  Act {act_num} Prologue: exit code $?"
                echo "[FAILED] Act {act_num}, Prologue"
            fi
        fi
    else
        if python "$ANALYZER" "$PLAY" {act_num} 0 --merge "$MERGE" $DRY_RUN 2>&1 | tee -a "$LOG_FILE"; then
            ((SUCCESSFUL++))
        else
            ((ERRORS++))
            FAILED_SCENES="$FAILED_SCENES
  Act {act_num} Prologue: exit code $?"
            echo "[FAILED] Act {act_num}, Prologue"
        fi
    fi
fi''')

        # Scenes
        for scene_num in sorted(act_data['scenes']):
            status_checks.append(f'''
    # Act {act_num} Scene {scene_num}
    OUTPUT=$(python "$ANALYZER" "$PLAY" {act_num} {scene_num} --merge "$MERGE" --status 2>/dev/null)
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        CHUNKS=$(echo "$OUTPUT" | grep -oP '\\d+ chunks' | head -1 | grep -oP '\\d+' || echo "?")
        echo "Act {act_num} Scene {scene_num}: $CHUNKS chunks (cached)"
        ((CACHED++))
    else
        CHUNKS=$(echo "$OUTPUT" | grep -oP '\\d+ chunks' | head -1 | grep -oP '\\d+' || echo "?")
        echo "Act {act_num} Scene {scene_num}: $CHUNKS chunks (0 cached, $CHUNKS to process)"
        ((PENDING++))
    fi''')

            validate_checks.append(f'''
    if python "$ANALYZER" "$PLAY" {act_num} {scene_num} --validate 2>/dev/null; then
        ((VALID++))
        echo "  ✓ Act {act_num} Scene {scene_num}"
    else
        ((INVALID++))
        echo "  ✗ Act {act_num} Scene {scene_num} - NOT FOUND"
    fi''')

            process_sections.append(f'''
# Act {act_num}, Scene {scene_num}
if matches_filter {act_num} {scene_num}; then
    echo "--- Act {act_num}, Scene {scene_num} ---"
    if [ -n "$RESUME_MODE" ]; then
        if python "$ANALYZER" "$PLAY" {act_num} {scene_num} --merge "$MERGE" --status 2>/dev/null; then
            echo "[SKIPPED] Act {act_num}, Scene {scene_num} - fully cached"
            ((SKIPPED++))
        else
            if python "$ANALYZER" "$PLAY" {act_num} {scene_num} --merge "$MERGE" $DRY_RUN 2>&1 | tee -a "$LOG_FILE"; then
                ((SUCCESSFUL++))
            else
                ((ERRORS++))
                FAILED_SCENES="$FAILED_SCENES
  Act {act_num} Scene {scene_num}: exit code $?"
                echo "[FAILED] Act {act_num}, Scene {scene_num}"
            fi
        fi
    else
        if python "$ANALYZER" "$PLAY" {act_num} {scene_num} --merge "$MERGE" $DRY_RUN 2>&1 | tee -a "$LOG_FILE"; then
            ((SUCCESSFUL++))
        else
            ((ERRORS++))
            FAILED_SCENES="$FAILED_SCENES
  Act {act_num} Scene {scene_num}: exit code $?"
            echo "[FAILED] Act {act_num}, Scene {scene_num}"
        fi
    fi
fi''')

    # Epilogue
    if structure['has_epilogue']:
        status_checks.append('''
    # Epilogue
    OUTPUT=$(python "$ANALYZER" "$PLAY" Epilogue --merge "$MERGE" --status 2>/dev/null)
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        CHUNKS=$(echo "$OUTPUT" | grep -oP '\\d+ chunks' | head -1 | grep -oP '\\d+' || echo "?")
        echo "Epilogue: $CHUNKS chunks (cached)"
        ((CACHED++))
    else
        CHUNKS=$(echo "$OUTPUT" | grep -oP '\\d+ chunks' | head -1 | grep -oP '\\d+' || echo "?")
        echo "Epilogue: $CHUNKS chunks (0 cached, $CHUNKS to process)"
        ((PENDING++))
    fi''')

        validate_checks.append('''
    if python "$ANALYZER" "$PLAY" Epilogue --validate 2>/dev/null; then
        ((VALID++))
        echo "  ✓ Epilogue"
    else
        ((INVALID++))
        echo "  ✗ Epilogue - NOT FOUND"
    fi''')

        process_sections.append('''
# Epilogue (only processed if no filter, or filter matches special epilogue marker)
if [ -z "$FILTER_ACT" ]; then
    echo "--- Epilogue ---"
    if [ -n "$RESUME_MODE" ]; then
        if python "$ANALYZER" "$PLAY" Epilogue --merge "$MERGE" --status 2>/dev/null; then
            echo "[SKIPPED] Epilogue - fully cached"
            ((SKIPPED++))
        else
            if python "$ANALYZER" "$PLAY" Epilogue --merge "$MERGE" $DRY_RUN 2>&1 | tee -a "$LOG_FILE"; then
                ((SUCCESSFUL++))
            else
                ((ERRORS++))
                FAILED_SCENES="$FAILED_SCENES
  Epilogue: exit code $?"
                echo "[FAILED] Epilogue"
            fi
        fi
    else
        if python "$ANALYZER" "$PLAY" Epilogue --merge "$MERGE" $DRY_RUN 2>&1 | tee -a "$LOG_FILE"; then
            ((SUCCESSFUL++))
        else
            ((ERRORS++))
            FAILED_SCENES="$FAILED_SCENES
  Epilogue: exit code $?"
            echo "[FAILED] Epilogue"
        fi
    fi
fi''')

    # Build structure description
    acts_desc = ', '.join(str(a) for a in sorted(structure['acts'].keys()))

    script = f'''#!/bin/bash
# gloss-play_{play_name}.sh - Analyze the entirety of {play_title}
# Generated by /analyze-plays command
#
# Usage: ./gloss-play_{play_name}.sh [OPTIONS] [FILTER]
#
# Options:
#   --status, -s    Show cache status for all scenes (what's done vs pending)
#   --dry-run, -n   Preview without API calls
#   --resume, -R    Skip scenes that are fully cached (resume interrupted run)
#   --validate, -V  Validate all scenes exist in play file before processing
#
# Filter (optional):
#   "Act I, Scene V"  - Process only Act 1, Scene 5
#   "Act I"           - Process all scenes in Act 1
#   "1 5" or "1.5"    - Process Act 1, Scene 5 (shorthand)
#
# Structure discovered:
#   - Opening Prologue: {"yes" if structure['has_opening_prologue'] else "no"}
#   - Acts: {acts_desc if acts_desc else "none detected"}
#   - Epilogue: {"yes" if structure['has_epilogue'] else "no"}
#   - Total output files: {total_scenes}

PLAY="{play_path}"
ANALYZER=~/utono/nvim-glosses-qa/python/scene_analyzer.py
MERGE=42
LOG_FILE=~/utono/nvim-glosses-qa/logs/scene_analyzer.log
DRY_RUN=""
STATUS_ONLY=""
RESUME_MODE=""
VALIDATE_MODE=""
FILTER_ACT=""
FILTER_SCENE=""

# Roman numeral conversion function
roman_to_int() {{
    local roman="$1"
    case "${{roman^^}}" in
        I) echo 1 ;; II) echo 2 ;; III) echo 3 ;; IV) echo 4 ;; V) echo 5 ;;
        VI) echo 6 ;; VII) echo 7 ;; VIII) echo 8 ;; IX) echo 9 ;; X) echo 10 ;;
        FIRST) echo 1 ;; SECOND) echo 2 ;; THIRD) echo 3 ;; FOURTH) echo 4 ;; FIFTH) echo 5 ;;
        *) echo "$roman" ;;  # Assume it's already a number
    esac
}}

# Parse command line arguments
for arg in "$@"; do
    case $arg in
        --status|-s)
            STATUS_ONLY="--status"
            ;;
        --dry-run|-n)
            DRY_RUN="--dry-run"
            ;;
        --resume|-R)
            RESUME_MODE="1"
            ;;
        --validate|-V)
            VALIDATE_MODE="1"
            ;;
        *)
            # Not a flag - treat as filter argument
            if [ -z "$FILTER_ACT" ]; then
                FILTER_ARG="$arg"
            fi
            ;;
    esac
done

# Parse filter argument if provided
if [ -n "$FILTER_ARG" ]; then
    # Handle formats: "Act I, Scene V", "Act 1 Scene 5", "1 5", "1.5", "Act I"
    # Extract act number
    if [[ "$FILTER_ARG" =~ [Aa][Cc][Tt][[:space:]]+([IVXivx]+|[0-9]+|FIRST|SECOND|THIRD|FOURTH|FIFTH) ]]; then
        FILTER_ACT=$(roman_to_int "${{BASH_REMATCH[1]}}")
    elif [[ "$FILTER_ARG" =~ ^([0-9]+)[[:space:].,:]+([0-9]+)$ ]]; then
        # Format: "1 5" or "1.5" or "1:5"
        FILTER_ACT="${{BASH_REMATCH[1]}}"
        FILTER_SCENE="${{BASH_REMATCH[2]}}"
    elif [[ "$FILTER_ARG" =~ ^([0-9]+)$ ]]; then
        # Just an act number
        FILTER_ACT="${{BASH_REMATCH[1]}}"
    fi

    # Extract scene number (if not already set)
    if [ -z "$FILTER_SCENE" ] && [[ "$FILTER_ARG" =~ [Ss][Cc][Ee][Nn][Ee][[:space:]]+([IVXivx]+|[0-9]+) ]]; then
        FILTER_SCENE=$(roman_to_int "${{BASH_REMATCH[1]}}")
    fi

    if [ -n "$FILTER_ACT" ]; then
        if [ -n "$FILTER_SCENE" ]; then
            echo "Filter: Act $FILTER_ACT, Scene $FILTER_SCENE only"
        else
            echo "Filter: Act $FILTER_ACT (all scenes)"
        fi
    else
        echo "Warning: Could not parse filter '$FILTER_ARG' - processing all scenes"
        FILTER_ARG=""
    fi
fi

# Function to check if scene matches filter
matches_filter() {{
    local act=$1
    local scene=$2

    # No filter = process everything
    if [ -z "$FILTER_ACT" ]; then
        return 0
    fi

    # Check act match
    if [ "$act" != "$FILTER_ACT" ]; then
        return 1
    fi

    # If no scene filter, match all scenes in the act
    if [ -z "$FILTER_SCENE" ]; then
        return 0
    fi

    # Check scene match
    if [ "$scene" = "$FILTER_SCENE" ]; then
        return 0
    fi

    return 1
}}

# Status mode: check cache status for all scenes
if [ -n "$STATUS_ONLY" ]; then
    echo "=== {play_title} - Cache Status ==="
    echo ""
    CACHED=0
    PENDING=0
{''.join(status_checks)}

    echo ""
    echo "=== Summary ==="
    echo "Cached: $CACHED scenes"
    echo "Pending: $PENDING scenes"
    if [ "$PENDING" -eq 0 ]; then
        echo "All scenes cached - nothing to process"
    else
        echo "Run without --status to process pending scenes"
    fi
    exit 0
fi

# Validate mode: check all scenes exist before processing
if [ -n "$VALIDATE_MODE" ]; then
    echo "=== {play_title} - Validating Script ==="
    echo ""
    VALID=0
    INVALID=0
{''.join(validate_checks)}

    echo ""
    echo "=== Validation Summary ==="
    echo "Found: $VALID scenes"
    echo "Missing: $INVALID scenes"
    if [ "$INVALID" -eq 0 ]; then
        echo "All scenes validated - script is correct"
        exit 0
    else
        echo ""
        echo "[CLAUDE_ACTION_REQUIRED]"
        echo "$INVALID scene(s) not found in play file."
        echo "Script may need regeneration with /analyze-plays"
        exit 1
    fi
fi

if [ -n "$DRY_RUN" ]; then
    echo "=== DRY RUN MODE ==="
fi

if [ -n "$RESUME_MODE" ]; then
    echo "=== RESUME MODE ==="
    echo "Checking cache status before each scene..."
    echo ""
fi

# Clear log file at start of run (unless resuming - append instead)
mkdir -p "$(dirname "$LOG_FILE")"
if [ -n "$RESUME_MODE" ]; then
    echo "" >> "$LOG_FILE"
    echo "=== Resuming at $(date) ===" >> "$LOG_FILE"
else
    > "$LOG_FILE"
    echo "Log cleared: $LOG_FILE"
fi

# Error tracking
ERRORS=0
FAILED_SCENES=""
SUCCESSFUL=0
SKIPPED=0
TOTAL_SCENES={total_scenes}

echo "Analyzing {play_title}..."
echo "Play file: $PLAY"
echo "Merge threshold: $MERGE lines"
echo "Log file: $LOG_FILE"
echo "Total scenes: $TOTAL_SCENES"
echo ""
{''.join(process_sections)}

# Summary
echo ""
echo "=== ANALYSIS SUMMARY ==="
echo "Play: {play_title}"
echo "Total scenes: $TOTAL_SCENES"
echo "Successful: $SUCCESSFUL"
if [ -n "$RESUME_MODE" ]; then
    echo "Skipped (cached): $SKIPPED"
fi
echo "Failed: $ERRORS"

if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo "[FAILED SCENES]"
    echo "$FAILED_SCENES"
    echo ""
    echo "[CLAUDE_ACTION_REQUIRED]"
    echo "$ERRORS scene(s) failed. Review errors above and in log file:"
    echo "  $LOG_FILE"
    echo ""
    echo "Suggested actions:"
    echo "1. Check log file for detailed error messages"
    echo "2. Run failed scenes individually to diagnose"
    echo "3. Use --resume to retry only failed/pending scenes"
    exit 1
else
    echo ""
    if [ -n "$RESUME_MODE" ] && [ "$SKIPPED" -gt 0 ]; then
        echo "Resume complete! $SKIPPED scenes were already cached."
    else
        echo "All scenes processed successfully!"
    fi
    echo "Output directory: ~/utono/literature/glosses/{play_name}/"
    exit 0
fi
'''

    script_path = os.path.join(output_dir, f'gloss-play_{play_name}.sh')
    with open(script_path, 'w') as f:
        f.write(script)
    os.chmod(script_path, 0o755)

    return {
        'name': play_name,
        'title': play_title,
        'acts': len(structure['acts']),
        'scenes': sum(len(a['scenes']) for a in structure['acts'].values()),
        'prologues': (1 if structure['has_opening_prologue'] else 0) +
                     sum(1 for a in structure['acts'].values() if a['has_prologue']),
        'epilogue': structure['has_epilogue'],
        'total': total_scenes,
        'script': script_path
    }


def main():
    gutenberg_dir = os.path.expanduser(
        '~/utono/literature/shakespeare-william/gutenberg'
    )
    output_dir = os.path.expanduser('~/utono/nvim-glosses-qa/scripts')

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Non-play files to skip
    skip_files = {
        'metadata.txt', 'first-folio.txt', 'sonnets_gut.txt',
        'lovers_complaint_gut.txt', 'passionate_pilgrim_gut.txt',
        'phoenix_and_the_turtle_gut.txt', 'rape_of_lucrece_gut.txt',
        'venus_and_adonis_gut.txt'
    }

    results = []

    # Process all .txt files
    for filename in sorted(os.listdir(gutenberg_dir)):
        if not filename.endswith('.txt'):
            continue
        if filename in skip_files:
            continue

        filepath = os.path.join(gutenberg_dir, filename)

        # Analyze structure
        structure = analyze_play_structure(filepath)

        # Skip if no acts found (not a play)
        if not structure['acts']:
            print(f"Skipping {filename} - no act structure found")
            continue

        # Generate script
        result = generate_script(filepath, structure, output_dir)
        results.append(result)
        print(f"Generated: gloss-play_{result['name']}.sh "
              f"({result['total']} scenes)")

    # Print summary
    print("\n" + "=" * 60)
    print(f"Generated {len(results)} scripts")
    print("=" * 60)

    total_files = sum(r['total'] for r in results)
    print(f"\nTotal output files across all plays: {total_files}")

    return results


if __name__ == '__main__':
    main()
