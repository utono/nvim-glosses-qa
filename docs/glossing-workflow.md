# Glossing Workflow

This document describes the process for creating line-by-line glosses of
Shakespeare plays using the `/gloss-play` slash command.

## Overview

The `/gloss-play` command processes a single scene at a time, generating
line-by-line actor-focused glosses directly in the Claude Code session.

**Key features:**
- In-session processing (no external API calls)
- Chunk-based caching (resume-safe)
- Automatic speaker attribution
- Database-backed storage

## Quick Start

```bash
# By file path + scene
/gloss-play ~/utono/literature/.../twelfth_night_gut.txt "Act I, Scene II"

# By play name + scene (requires generated script)
/gloss-play twelfth-night "Act I, Scene II"
```

## How It Works

### 1. Export Chunks

The command runs `scene_analyzer.py --export-chunks` to get scene data as JSON:

```json
{
  "play_name": "twelfth-night",
  "act": 1, "scene": 2,
  "chunks": [
    {"hash": "3b4512a4...", "cached": false, "text": "VIOLA.\nWhat country..."},
    {"hash": "8726d7be...", "cached": true, "cached_text": "..."}
  ]
}
```

### 2. Process Each Chunk

For each chunk where `cached: false`:
- Generate line-by-line analysis following the prompt guidelines
- Save to database with `--save-chunk <HASH>`

Cached chunks are skipped automatically.

### 3. Build Markdown

After all chunks are processed:
```bash
scene_analyzer.py ... --build-from-cache
```

This assembles the final markdown file from all cached chunks.

## Command Syntax

```
/gloss-play <play-file-or-name> "<Act N, Scene M>"
```

**Format detection:**
- Contains `/` or ends with `.txt` → direct file path
- Otherwise → play name (looks up script for file path)

### Examples

```bash
# Full file path
/gloss-play ~/utono/literature/shakespeare-william/gutenberg/hamlet_gut.txt \
    "Act III, Scene I"

# Play name (requires gloss-play_hamlet.sh to exist)
/gloss-play hamlet "Act III, Scene I"

# Twelfth Night opening
/gloss-play twelfth-night "Act I, Scene I"
```

## Scene Analyzer Flags

| Flag | Purpose |
|------|---------|
| `--export-chunks` | Export chunk data as JSON |
| `--save-chunk HASH` | Save analysis for chunk (reads from stdin) |
| `--build-from-cache` | Build markdown from all cached chunks |
| `--dry-run` | Preview chunks without processing |
| `--status` | Show cache status only |
| `--merge N` | Merge speeches into N-line chunks (default: 42) |

## Typical Session

```bash
# Process Act I, Scene II of Twelfth Night
/gloss-play twelfth-night "Act I, Scene II"

# Output:
# Processed 3 chunks (all new, none cached)
# Output: ~/utono/literature/glosses/twelfth-night/act1_scene2_line-by-line.md
```

If interrupted, re-running the same command skips cached chunks:

```bash
# Re-run after interruption
/gloss-play twelfth-night "Act I, Scene II"

# Output:
# Processed 3 chunks (2 cached, 1 new)
```

## Generating Play Scripts

Before using the play name shorthand, generate scripts with `/analyze-plays`:

```bash
# Generate scripts for all plays
/analyze-plays ~/utono/literature/shakespeare-william/gutenberg/*.txt

# Generate for single play
/analyze-plays ~/utono/literature/.../twelfth_night_gut.txt
```

Scripts are saved to `~/utono/nvim-glosses-qa/scripts/`:
- `gloss-play_twelfth-night.sh`
- `gloss-play_hamlet.sh`
- etc.

The `/gloss-play` command extracts `PLAY_FILE` from these scripts when you
use the play name format.

## Output Format

Each gloss provides for every line:
- The line in **bold**
- Literal meaning (1-2 sentences)
- Operative word(s) with explanation
- Acting insight (breath, emphasis, physical note)

Speaker names appear in ALL CAPS before their lines when speakers change.

### Example Output

```markdown
VIOLA.

**"What country friends is this?"**

Where am I? What land have we come to? The operative word is
"country" — Viola wakes to disorientation, the shore alien and
unnamed. "Friends" reaches toward the sailors, her only companions
in this strange place. Let the line hang as genuine inquiry.

CAPTAIN.

**"This is Illyria lady."**

We are in Illyria, my lady. "Illyria" lands as the operative —
a name that locates and yet remains exotic, half-mythical.
The Captain's answer is plain, almost flat — a serviceable
response to a shipwrecked noblewoman.
```

## File Locations

| Item | Path |
|------|------|
| Play source files | `~/utono/literature/shakespeare-william/gutenberg/` |
| Generated scripts | `~/utono/nvim-glosses-qa/scripts/` |
| Output glosses | `~/utono/literature/glosses/<play-name>/` |
| Gloss database | `~/utono/literature/gloss.db` |

## Processing Full Plays

To process an entire play, run `/gloss-play` for each scene sequentially:

```bash
/gloss-play hamlet "Act I, Scene I"
/gloss-play hamlet "Act I, Scene II"
/gloss-play hamlet "Act I, Scene III"
# ... etc.
```

The caching system ensures you can stop and resume at any point without
re-processing completed scenes or chunks.

## Troubleshooting

**"Script not found" error:**
Run `/analyze-plays` first to generate the play script.

**Chunk save fails:**
Check that the chunk hash matches exactly. The hash is shown in the
`--export-chunks` JSON output.

**Partial scene:**
If interrupted mid-scene, re-run the same command. Cached chunks are
skipped; only remaining chunks are processed.

**Check scene status:**
```bash
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    "<play-file>" "<act/scene>" --merge 42 --status
```
