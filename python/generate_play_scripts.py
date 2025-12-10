#!/usr/bin/env python3
"""
Generate shell scripts for analyzing all Shakespeare plays.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Files to skip (non-plays)
SKIP_FILES = {
    'first-folio.txt',
    'lovers_complaint_gut.txt',
    'passionate_pilgrim_gut.txt',
    'phoenix_and_the_turtle_gut.txt',
    'sonnets_gut.txt',
    'venus_and_adonis_gut.txt',
    'rape_of_lucrece_gut.txt',
    'metadata.txt',
}

def extract_play_name(filename: str) -> str:
    """Extract play name from filename."""
    # Remove _gut.txt or .txt suffix
    name = filename.replace('_gut.txt', '').replace('.txt', '')
    # Replace underscores with hyphens
    return name.replace('_', '-')

def get_play_title(filename: str) -> str:
    """Get readable play title from filename."""
    name = filename.replace('_gut.txt', '').replace('.txt', '')
    # Convert underscores to spaces and title case
    title = name.replace('_', ' ').title()

    # Special cases
    title_map = {
        'Alls Well That Ends Well': "All's Well That Ends Well",
        'As You Like It': 'As You Like It',
        'Comedy Of Errors': 'The Comedy of Errors',
        'Henry Iv Part 1': 'Henry IV, Part 1',
        'Henry Iv Part 2': 'Henry IV, Part 2',
        'Henry V': 'Henry V',
        'Henry Vi Part 1': 'Henry VI, Part 1',
        'Henry Vi Part 2': 'Henry VI, Part 2',
        'Henry Vi Part 3': 'Henry VI, Part 3',
        'Henry Viii': 'Henry VIII',
        'John': 'King John',
        'Lear': 'King Lear',
        'Loves Labours Lost': "Love's Labour's Lost",
        'Measure For Measure': 'Measure for Measure',
        'Merchant Of Venice': 'The Merchant of Venice',
        'Merry Wives Of Windsor': 'The Merry Wives of Windsor',
        'Midsummer Nights Dream': "A Midsummer Night's Dream",
        'Much Ado About Nothing': 'Much Ado About Nothing',
        'Richard Ii': 'Richard II',
        'Richard Iii': 'Richard III',
        'Romeo And Juliet': 'Romeo and Juliet',
        'Taming Of The Shrew': 'The Taming of the Shrew',
        'Tempest': 'The Tempest',
        'The Two Noble Kinsmen': 'The Two Noble Kinsmen',
        'Timon Of Athens': 'Timon of Athens',
        'Tragedy Of Titus Andronicus': 'Titus Andronicus',
        'Troilus And Cressida': 'Troilus and Cressida',
        'Twelfth Night': 'Twelfth Night',
        'Two Gentlemen Of Verona': 'The Two Gentlemen of Verona',
        'Winters Tale': "The Winter's Tale",
    }

    return title_map.get(title, title)

def roman_to_int(roman: str) -> int:
    """Convert roman numeral to integer."""
    roman_map = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
    }
    word_map = {
        'FIRST': 1, 'SECOND': 2, 'THIRD': 3, 'FOURTH': 4, 'FIFTH': 5
    }
    return roman_map.get(roman) or word_map.get(roman)

def analyze_play_structure(filepath: str) -> Dict:
    """Analyze the structure of a play file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    structure = {
        'has_opening_prologue': False,
        'acts': {},
        'has_epilogue': False,
    }

    current_act = None
    act_started = False

    for line in lines:
        line = line.strip()

        # Check for prologue before any act
        if re.match(r'^PROLOGUE\.\s*$', line):
            if not act_started:
                structure['has_opening_prologue'] = True
            elif current_act is not None:
                # Prologue after an act marker
                structure['acts'][current_act]['has_prologue'] = True

        # Check for act marker (with or without period, case insensitive, roman or arabic)
        act_match = re.match(r'^ACT\s+([IVX]+|FIRST|SECOND|THIRD|FOURTH|FIFTH|[0-9]+)\.?\s*$', line, re.IGNORECASE)
        if act_match:
            act_started = True
            act_str = act_match.group(1)
            # Check if it's a number or roman numeral/word
            if act_str.isdigit():
                act_num = int(act_str)
            else:
                act_num = roman_to_int(act_str)
            current_act = act_num
            # Only create act entry if it doesn't exist (some Gutenberg files
            # repeat "ACT I." before each scene)
            if act_num not in structure['acts']:
                structure['acts'][act_num] = {
                    'has_prologue': False,
                    'scenes': []
                }

        # Check for scene marker - support both roman (I, II) and arabic (1, 2), with or without period
        # Case insensitive to handle "Scene I." and "SCENE I."
        scene_match = re.match(r'^SCENE\s+([IVX]+|[0-9]+)\.?', line, re.IGNORECASE)
        if scene_match and current_act is not None:
            scene_str = scene_match.group(1)
            # Check if it's a number or roman numeral
            if scene_str.isdigit():
                scene_num = int(scene_str)
            else:
                scene_num = roman_to_int(scene_str)
            if scene_num and scene_num not in structure['acts'][current_act]['scenes']:
                structure['acts'][current_act]['scenes'].append(scene_num)

        # Check for epilogue
        if re.match(r'^EPILOGUE\.\s*$', line):
            structure['has_epilogue'] = True

    return structure

def generate_script(play_file: str, structure: Dict, output_dir: str) -> str:
    """Generate shell script for analyzing a play."""
    filename = os.path.basename(play_file)
    play_name = extract_play_name(filename)
    play_title = get_play_title(filename)

    # Calculate total scenes
    total_scenes = 0
    if structure['has_opening_prologue']:
        total_scenes += 1
    for act_data in structure['acts'].values():
        if act_data['has_prologue']:
            total_scenes += 1
        total_scenes += len(act_data['scenes'])
    if structure['has_epilogue']:
        total_scenes += 1

    # Generate status checks
    status_checks = []
    validate_checks = []

    if structure['has_opening_prologue']:
        status_checks.append('if python "$ANALYZER" "$PLAY" 0 0 --merge "$MERGE" --status 2>/dev/null; then\n    ((CACHED++))\nelse\n    ((PENDING++))\nfi')
        validate_checks.append('if python "$ANALYZER" "$PLAY" 0 0 --validate 2>/dev/null; then\n    ((VALID++))\nelse\n    ((INVALID++))\n    echo "  ✗ Prologue (Opening) - NOT FOUND"\nfi')

    for act_num in sorted(structure['acts'].keys()):
        act_data = structure['acts'][act_num]
        if act_data['has_prologue']:
            status_checks.append(f'if python "$ANALYZER" "$PLAY" {act_num} 0 --merge "$MERGE" --status 2>/dev/null; then\n    ((CACHED++))\nelse\n    ((PENDING++))\nfi')
            validate_checks.append(f'if python "$ANALYZER" "$PLAY" {act_num} 0 --validate 2>/dev/null; then\n    ((VALID++))\nelse\n    ((INVALID++))\n    echo "  ✗ Act {act_num}, Prologue - NOT FOUND"\nfi')

        for scene_num in act_data['scenes']:
            status_checks.append(f'if python "$ANALYZER" "$PLAY" {act_num} {scene_num} --merge "$MERGE" --status 2>/dev/null; then\n    ((CACHED++))\nelse\n    ((PENDING++))\nfi')
            validate_checks.append(f'if python "$ANALYZER" "$PLAY" {act_num} {scene_num} --validate 2>/dev/null; then\n    ((VALID++))\nelse\n    ((INVALID++))\n    echo "  ✗ Act {act_num}, Scene {scene_num} - NOT FOUND"\nfi')

    if structure['has_epilogue']:
        status_checks.append('if python "$ANALYZER" "$PLAY" Epilogue --merge "$MERGE" --status 2>/dev/null; then\n    ((CACHED++))\nelse\n    ((PENDING++))\nfi')
        validate_checks.append('if python "$ANALYZER" "$PLAY" Epilogue --validate 2>/dev/null; then\n    ((VALID++))\nelse\n    ((INVALID++))\n    echo "  ✗ Epilogue - NOT FOUND"\nfi')

    status_checks_str = '\n\n    '.join(status_checks)
    validate_checks_str = '\n\n    '.join(validate_checks)

    # Generate opening prologue section
    opening_prologue = ''
    if structure['has_opening_prologue']:
        opening_prologue = '''# Opening Prologue
echo "--- Prologue (Opening) ---"
if [ -n "$RESUME_MODE" ] && python "$ANALYZER" "$PLAY" 0 0 --merge "$MERGE" --status 2>/dev/null; then
    echo "[SKIPPED] Prologue (Opening) - fully cached"
    ((SKIPPED++))
elif python "$ANALYZER" "$PLAY" 0 0 --merge "$MERGE" $DRY_RUN; then
    ((SUCCESSFUL++))
else
    ((ERRORS++))
    FAILED_SCENES="$FAILED_SCENES
  Prologue: exit code $?"
    echo "[FAILED] Prologue (Opening)"
fi
echo ""
'''

    # Generate act sections
    act_sections = []
    for act_num in sorted(structure['acts'].keys()):
        act_data = structure['acts'][act_num]
        act_section = f'# Act {act_num}\n'

        if act_data['has_prologue']:
            act_section += f'''echo "--- Act {act_num}, Prologue ---"
if [ -n "$RESUME_MODE" ] && python "$ANALYZER" "$PLAY" {act_num} 0 --merge "$MERGE" --status 2>/dev/null; then
    echo "[SKIPPED] Act {act_num}, Prologue - fully cached"
    ((SKIPPED++))
elif python "$ANALYZER" "$PLAY" {act_num} 0 --merge "$MERGE" $DRY_RUN; then
    ((SUCCESSFUL++))
else
    ((ERRORS++))
    FAILED_SCENES="$FAILED_SCENES
  Act {act_num} Prologue: exit code $?"
    echo "[FAILED] Act {act_num}, Prologue"
fi
echo ""
'''

        for scene_num in act_data['scenes']:
            act_section += f'''echo "--- Act {act_num}, Scene {scene_num} ---"
if [ -n "$RESUME_MODE" ] && python "$ANALYZER" "$PLAY" {act_num} {scene_num} --merge "$MERGE" --status 2>/dev/null; then
    echo "[SKIPPED] Act {act_num}, Scene {scene_num} - fully cached"
    ((SKIPPED++))
elif python "$ANALYZER" "$PLAY" {act_num} {scene_num} --merge "$MERGE" $DRY_RUN; then
    ((SUCCESSFUL++))
else
    ((ERRORS++))
    FAILED_SCENES="$FAILED_SCENES
  Act {act_num} Scene {scene_num}: exit code $?"
    echo "[FAILED] Act {act_num}, Scene {scene_num}"
fi
echo ""
'''

        act_sections.append(act_section)

    act_sections_str = '\n'.join(act_sections)

    # Generate epilogue section
    epilogue_section = ''
    if structure['has_epilogue']:
        epilogue_section = '''# Epilogue
echo "--- Epilogue ---"
if [ -n "$RESUME_MODE" ] && python "$ANALYZER" "$PLAY" Epilogue --merge "$MERGE" --status 2>/dev/null; then
    echo "[SKIPPED] Epilogue - fully cached"
    ((SKIPPED++))
elif python "$ANALYZER" "$PLAY" Epilogue --merge "$MERGE" $DRY_RUN; then
    ((SUCCESSFUL++))
else
    ((ERRORS++))
    FAILED_SCENES="$FAILED_SCENES
  Epilogue: exit code $?"
    echo "[FAILED] Epilogue"
fi
echo ""
'''

    # Build structure summary
    acts_list = ', '.join(str(a) for a in sorted(structure['acts'].keys()))
    prologues_count = (1 if structure['has_opening_prologue'] else 0) + \
                      sum(1 for a in structure['acts'].values() if a['has_prologue'])

    script_content = f'''#!/bin/bash
# gloss-play_{play_name}.sh - Analyze the entirety of {play_title}
# Generated by /analyze-plays command
#
# Usage: ./gloss-play_{play_name}.sh [--status] [--dry-run] [--resume] [--validate]
#
# Options:
#   --status, -s    Show cache status for all scenes (what's done vs pending)
#   --dry-run, -n   Preview without API calls
#   --resume, -R    Skip scenes that are fully cached (resume interrupted run)
#   --validate, -V  Validate all scenes exist in play file before processing
#
# Structure discovered:
#   - Opening Prologue: {'yes' if structure['has_opening_prologue'] else 'no'}
#   - Acts: {acts_list}
#   - Prologues: {prologues_count}
#   - Epilogue: {'yes' if structure['has_epilogue'] else 'no'}
#   - Total output files: {total_scenes}

PLAY="{play_file}"
ANALYZER=~/utono/nvim-glosses-qa/python/scene_analyzer.py
MERGE=42
LOG_FILE=~/utono/nvim-glosses-qa/logs/scene_analyzer.log
DRY_RUN=""
STATUS_ONLY=""
RESUME_MODE=""
VALIDATE_MODE=""

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
    esac
done

# Status mode: check cache status for all scenes
if [ -n "$STATUS_ONLY" ]; then
    echo "=== {play_title} - Cache Status ==="
    echo ""
    CACHED=0
    PENDING=0

    {status_checks_str}

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

    {validate_checks_str}

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

{opening_prologue}
{act_sections_str}
{epilogue_section}
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

    # Write script file
    script_path = os.path.join(output_dir, f'gloss-play_{play_name}.sh')
    with open(script_path, 'w') as f:
        f.write(script_content)

    # Make executable
    os.chmod(script_path, 0o755)

    return script_path

def main():
    gutenberg_dir = Path.home() / 'utono' / 'literature' / 'shakespeare-william' / 'gutenberg'
    output_dir = Path.home() / 'utono' / 'nvim-glosses-qa' / 'scripts'

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all play files
    play_files = sorted(gutenberg_dir.glob('*.txt'))

    # Filter out non-play files
    play_files = [f for f in play_files if f.name not in SKIP_FILES]

    results = []
    total_scenes = 0

    for play_file in play_files:
        print(f"Analyzing {play_file.name}...")
        structure = analyze_play_structure(str(play_file))

        # Calculate stats
        num_acts = len(structure['acts'])
        num_scenes = sum(len(act_data['scenes']) for act_data in structure['acts'].values())
        num_prologues = (1 if structure['has_opening_prologue'] else 0) + \
                        sum(1 for a in structure['acts'].values() if a['has_prologue'])
        num_files = num_scenes + num_prologues + (1 if structure['has_epilogue'] else 0)

        # Generate script
        script_path = generate_script(str(play_file), structure, str(output_dir))

        play_name = extract_play_name(play_file.name)
        play_title = get_play_title(play_file.name)

        results.append({
            'title': play_title,
            'acts': num_acts,
            'scenes': num_scenes,
            'prologues': num_prologues,
            'epilogue': 'Yes' if structure['has_epilogue'] else 'No',
            'files': num_files,
            'script': f'gloss-play_{play_name}.sh'
        })

        total_scenes += num_files

    # Print summary table
    print(f"\n## Plays Analyzed: {len(results)} files processed\n")
    print("| Play | Acts | Scenes | Prologues | Epilogue | Files | Script |")
    print("|------|------|--------|-----------|----------|-------|--------|")

    for r in results:
        print(f"| {r['title']} | {r['acts']} | {r['scenes']} | {r['prologues']} | {r['epilogue']} | {r['files']} | {r['script']} |")

    print(f"\n**Total output files across all plays:** {total_scenes}")
    print(f"\n## Generated Scripts\n")
    print(f"Scripts saved to: `{output_dir}/`")
    print(f"\nAll scripts are executable and ready to run.")

if __name__ == '__main__':
    main()
