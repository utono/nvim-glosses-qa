# Glossing Workflow

This document describes the two-step process for creating line-by-line
glosses of Shakespeare plays.

## Overview

1. **Generate scripts** - Run `/analyze-plays` to create shell scripts
2. **Run scripts** - Run `/gloss-play` to execute the analysis

## Step 1: Generate Analysis Scripts

Use the `/analyze-plays` slash command to scan play files and generate
shell scripts that will process each scene.

### Usage

```bash
# Single play
/analyze-plays ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt

# All plays in directory
/analyze-plays ~/utono/literature/shakespeare-william/gutenberg/*.txt

# Multiple specific plays
/analyze-plays ~/utono/.../hamlet_gut.txt ~/utono/.../macbeth_gut.txt
```

### What It Does

1. Reads each play file to discover its structure
2. Identifies all acts, scenes, prologues, and epilogues
3. Generates a shell script for each play
4. Makes scripts executable

### Output

Scripts are saved to `~/utono/nvim-glosses-qa/scripts/` with names like:
- `gloss-play_henry-v.sh`
- `gloss-play_hamlet.sh`
- `gloss-play_macbeth.sh`

## Step 2: Run Analysis Scripts

Use the `/gloss-play` slash command to execute the generated scripts.

### Usage

```bash
# By play name (looks up script automatically)
/gloss-play henry-v

# By full path to script
/gloss-play ~/utono/nvim-glosses-qa/scripts/gloss-play_henry-v.sh
```

### Auto-Resume Feature

When run without flags, `/gloss-play` automatically:
1. Checks cache status for the play
2. If cached scenes exist, adds `--resume` flag automatically
3. Reports: "Found N cached scenes, M pending. Using --resume."

This means you can always just run `/gloss-play henry-v` and it will
efficiently skip already-processed scenes.

### Available Flags

| Flag | Purpose |
|------|---------|
| `--dry-run` | Preview what will be processed without API calls |
| `--status` | Show cache status (what's done vs pending) |
| `--validate` | Verify all scenes exist before processing |
| `--resume` | Skip fully-cached scenes (explicit, bypasses auto-detect) |

### Examples

```bash
# Preview before running
/gloss-play henry-v --dry-run

# Check progress
/gloss-play henry-v --status

# Validate script correctness
/gloss-play henry-v --validate

# Resume after interruption
/gloss-play henry-v --resume
```

### Output Location

Glosses are saved to `~/utono/literature/glosses/<play-name>/`:
- `act1_scene1_line-by-line.md`
- `act1_scene2_line-by-line.md`
- etc.

## Typical Workflow

```bash
# 1. Generate scripts for all plays (one-time setup)
/analyze-plays ~/utono/literature/shakespeare-william/gutenberg/*.txt

# 2. Preview what Henry V will process
/gloss-play henry-v --dry-run

# 3. Run the analysis (auto-resumes if previously started)
/gloss-play henry-v

# 4. Check final status
/gloss-play henry-v --status
```

Note: Step 3 automatically detects cached scenes and uses `--resume` mode,
so you can safely re-run `/gloss-play henry-v` after any interruption.

## Error Handling

Scripts track errors and report them at completion:
- `[FAILED]` markers indicate scene failures
- `[CLAUDE_ACTION_REQUIRED]` indicates intervention needed
- `[SKIPPED]` markers (in resume mode) show cached scenes

### Recovery

1. **Check status**: `/gloss-play <name> --status`
2. **Resume**: `/gloss-play <name> --resume`
3. **Check logs**: `~/utono/nvim-glosses-qa/logs/scene_analyzer.log`

## File Locations

| Item | Path |
|------|------|
| Play source files | `~/utono/literature/shakespeare-william/gutenberg/` |
| Generated scripts | `~/utono/nvim-glosses-qa/scripts/` |
| Output glosses | `~/utono/literature/glosses/<play-name>/` |
| Log file | `~/utono/nvim-glosses-qa/logs/scene_analyzer.log` |
| Gloss database | `~/utono/literature/gloss.db` |

## Notes

- Caching means reruns skip already-processed chunks
- Safe to stop and restart - use `--resume` for efficient restart
- Use `--validate` after script generation to catch errors early
- Each scene is processed in chunks (speeches merged by line count)
- Default merge threshold is 42 lines
