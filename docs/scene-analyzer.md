# Scene Analyzer

Generate line-by-line actor analysis for Shakespeare scenes.

## Overview

The `scene_analyzer.py` script processes Shakespeare plays scene by scene,
generating line-by-line actor analysis. Results are cached in the database
and assembled into markdown files organized by play.

**Primary workflow:** Use the `/gloss-play` slash command in Claude Code,
which processes scenes in-session without external API calls.

## Files

- **CLI Script**: `~/utono/nvim-glosses-qa/python/scene_analyzer.py`
- **Slash Commands**:
  - `/gloss-play` - Process a single scene
  - `/analyze-plays` - Generate scripts for full plays

## Quick Start

```bash
# In Claude Code session:
/gloss-play twelfth-night "Act I, Scene II"

# Or with full path:
/gloss-play ~/utono/literature/.../twelfth_night_gut.txt "Act I, Scene II"
```

## Output Structure

```
~/utono/literature/glosses/
├── twelfth-night/
│   ├── act1_scene1_line-by-line.md
│   ├── act1_scene2_line-by-line.md
│   └── ...
├── henry-v/
│   ├── prologue_line-by-line.md
│   ├── act1_scene1_line-by-line.md
│   ├── act2_prologue_line-by-line.md
│   └── ...
└── hamlet/
    └── ...
```

## Claude Code Workflow

The `/gloss-play` command uses a three-step process:

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Export chunks (--export-chunks)                             │
│     → Returns JSON with chunk text and cache status             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. For each non-cached chunk:                                  │
│     a) Claude generates line-by-line analysis in-session        │
│     b) Save with: cat << 'EOF' | ... --save-chunk <HASH>        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. Build markdown (--build-from-cache)                         │
│     → Verifies all chunks cached, writes output file            │
└─────────────────────────────────────────────────────────────────┘
```

### Example Session

```bash
# Step 1: Export chunks
python scene_analyzer.py play.txt "Act I, Scene II" --merge 42 --export-chunks

# Output (JSON):
{
  "play_name": "twelfth-night",
  "act": 1, "scene": 2,
  "chunks": [
    {"hash": "3b4512a4...", "cached": false, "text": "VIOLA.\nWhat country..."},
    {"hash": "8726d7be...", "cached": false, "text": "CAPTAIN.\nA noble..."},
    {"hash": "8a4549f4...", "cached": false, "text": "VIOLA.\nThere is a..."}
  ]
}

# Step 2: For each uncached chunk, generate analysis and save
cat << 'CHUNK_EOF' | python scene_analyzer.py play.txt "Act I, Scene II" \
    --merge 42 --save-chunk 3b4512a4...
VIOLA.

**"What country friends is this?"**

Where am I? What land have we come to? The operative word is
"country" — Viola wakes to disorientation...
CHUNK_EOF

# Output: Saved chunk 3b4512a4 (VIOLA...VIOLA (9 speeches))

# Step 3: Build final markdown
python scene_analyzer.py play.txt "Act I, Scene II" --merge 42 --build-from-cache

# Output: Built .../act1_scene2_line-by-line.md from 3 cached chunks
```

### Benefits

- **No external API calls** — analysis happens in Claude Code session
- **Resume-safe** — cached chunks are skipped on re-run
- **Database-backed** — all analyses stored for reuse
- **Separation of concerns** — Python handles DB/files, Claude handles analysis

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--export-chunks` | | Export chunk data as JSON |
| `--save-chunk HASH` | | Save analysis for chunk (reads stdin) |
| `--build-from-cache` | | Build markdown from cached chunks |
| `--dry-run` | `-n` | Preview without processing |
| `--status` | `-s` | Show cache status |
| `--merge N` | `-m N` | Merge speeches into ~N-line chunks |
| `--validate` | `-v` | Check if scene exists |
| `--output-dir` | `-o` | Override output directory |

## Scene Specification Formats

```bash
# "Act N, Scene M" format (from <M-a> clipboard)
python scene_analyzer.py play.txt "Act IV, Scene VII"

# Numeric arguments
python scene_analyzer.py play.txt 4 7
```

### Prologues and Epilogues

Some plays (notably Henry V) have Chorus prologues:

```bash
# Opening Prologue (before Act 1) - act=0, scene=0
python scene_analyzer.py play.txt "Prologue"
python scene_analyzer.py play.txt 0 0

# Act-specific Prologue (e.g., Act 2 Prologue) - act=N, scene=0
python scene_analyzer.py play.txt "Act 2, Prologue"
python scene_analyzer.py play.txt 2 0

# Epilogue - scene=-1
python scene_analyzer.py play.txt "Epilogue"
python scene_analyzer.py play.txt 0 -1
```

## Generating Full-Play Scripts

Use `/analyze-plays` to discover play structure and generate scripts:

```bash
# Single play
/analyze-plays ~/utono/literature/.../henry_v_gut.txt

# All plays
/analyze-plays ~/utono/literature/shakespeare-william/gutenberg/*.txt
```

**Output:**
- Scripts saved to `~/utono/nvim-glosses-qa/scripts/gloss-play_{play}.sh`
- Each script defines `PLAY_FILE` for use with `/gloss-play`

## Merging Speeches

The `--merge N` option combines small speeches into larger chunks:

```bash
# Without merge: Act 4 Scene 7 = 53 separate speeches
# With --merge 42: ~10 chunks (80% fewer processing steps)
python scene_analyzer.py play.txt "Act IV, Scene VII" --merge 42
```

**Rules:**
- Speeches are never split across chunks
- Each character's dialogue stays intact
- Chunks close when adding the next speech would exceed threshold
- A speech longer than threshold becomes its own chunk

## Architecture

### Processing Flow

1. **Parse play file** — Locate act/scene boundaries
2. **Extract speeches** — Each character's continuous dialogue = one unit
3. **Optionally merge** — Combine small speeches into larger chunks
4. **Check cache** — Skip units already in database (by content hash)
5. **Generate analysis** — Claude analyzes each uncached unit
6. **Save to database** — Store each unit for future reuse
7. **Write markdown** — Assemble all analyses into scene file

### Text Pattern Recognition

| Element | Pattern | Example |
|---------|---------|---------|
| Act markers | `^ACT\s+[IVX]+\.\s*$` | "ACT IV." |
| Act (ordinal) | `^ACT\s+(FIRST\|SECOND\|...)` | "ACT FIRST." |
| Scene markers | `^SCENE\s+[IVX]+\.\s*(.*)$` | "SCENE VII. Another..." |
| Prologue | `^PROLOGUE\.\s*$` | "PROLOGUE." |
| Epilogue | `^EPILOGUE\.\s*$` | "EPILOGUE." |
| Speaker names | `^([A-Z][A-Za-z\s]+)\.\s*$` | "KING HENRY." |
| Stage directions | `^\[.*\]\s*$` | "[Exit]" |

### Hybrid Storage

- **Database** (`~/utono/literature/gloss.db`): Granular, searchable cache
- **Markdown files**: Human-readable, organized by play/act/scene

## Play File Locations

```
~/utono/literature/shakespeare-william/gutenberg/
├── henry_v_gut.txt
├── hamlet_gut.txt
├── macbeth_gut.txt
├── twelfth_night_gut.txt
├── romeo_juliet_gut.txt
└── ...
```

## Henry V Structure Reference

Henry V has Chorus prologues before each act:

| Section | Specification | Output File |
|---------|---------------|-------------|
| Opening Prologue | `"Prologue"` or `0 0` | `prologue_line-by-line.md` |
| Act 1, Scene 1 | `"Act I, Scene I"` or `1 1` | `act1_scene1_line-by-line.md` |
| Act 2 Prologue | `"Act 2, Prologue"` or `2 0` | `act2_prologue_line-by-line.md` |
| Act 2, Scene 1 | `"Act II, Scene I"` or `2 1` | `act2_scene1_line-by-line.md` |
| ... | ... | ... |
| Epilogue | `"Epilogue"` or `0 -1` | `epilogue_line-by-line.md` |

**Total for Henry V:** 28 files (1 opening prologue + 5 act prologues +
21 scenes + 1 epilogue)

## Example Output Format

Each gloss provides for every line:
- The line in **bold**
- Literal meaning (1-2 sentences)
- Operative word(s) with explanation
- Acting insight (breath, emphasis, physical note)

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

## Troubleshooting

### Scene Not Found

```
Error: Scene 4.9 (Act IV, Scene IX) not found in play.txt
```

Use `--validate` or `--dry-run` to verify scene numbers.

### Check Cache Status

```bash
python scene_analyzer.py play.txt "Act IV, Scene VII" --status
```

### Build Fails with Missing Chunks

```
Error: 3 chunks not cached:
  - 54344567 (CLOWN...OLIVIA)
  - ed3ff572 (CLOWN...MALVOLIO)
```

Use `--export-chunks` to see which chunks need processing, then save each
with `--save-chunk` before rebuilding.

### Partial Scene Recovery

If interrupted mid-scene:
1. Re-run `/gloss-play` with same arguments
2. Cached chunks are skipped automatically
3. Only remaining chunks are processed
