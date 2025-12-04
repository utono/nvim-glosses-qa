# Scene Analyzer

Generate line-by-line actor analysis for entire Shakespeare scenes.

## Overview

The `scene_analyzer.py` script processes Shakespeare plays scene by scene,
generating line-by-line actor analysis for each speech. Results are cached
in the database and aggregated into markdown files organized by play.

## Files

- **CLI Script**: `~/utono/nvim-glosses-qa/python/scene_analyzer.py`
- **Slash Command**: `~/.config/nvim-glosses-qa/.claude/commands/scene.md`

## Output Structure

```
~/utono/literature/glosses/
├── henry-v/
│   ├── act1_scene1_line-by-line.md
│   ├── act1_scene2_line-by-line.md
│   ├── act4_scene7_line-by-line.md
│   └── ...
├── hamlet/
│   ├── act1_scene1_line-by-line.md
│   └── ...
└── macbeth/
    └── ...
```

## Usage

### Basic Usage

```bash
# Using "Act N, Scene M" format (from <M-a> clipboard)
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt \
    "Act IV, Scene VII"

# Using numeric arguments
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt 4 7
```

### Dry Run (Preview)

```bash
# See what would be processed without calling Claude Code
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt \
    "Act IV, Scene VII" --dry-run
```

### Merge Small Speeches (Recommended)

```bash
# Merge speeches into chunks of ~15 lines (reduces Claude Code calls)
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt \
    "Act IV, Scene VII" --merge 15
```

Example: Act 4, Scene 7 of Henry V has 53 speeches. With `--merge 15`, this
becomes ~10 chunks - reducing Claude Code calls by ~80%.

**Note:** Speeches are never split across chunks. Each character's dialogue
stays intact. Chunks close when adding the next speech would exceed the
threshold. A speech longer than the threshold becomes its own chunk.

### Workflow with `<M-a>`

1. In Neovim, navigate to the scene you want to analyze
2. Press `<M-a>` to copy "Act IV, Scene VII" to system clipboard
3. Paste into command: `python scene_analyzer.py play.txt "Act IV, Scene VII"`

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--dry-run` | `-n` | Preview without calling Claude Code |
| `--merge N` | `-m N` | Merge speeches into ~N-line chunks (never splits) |
| `--backend` | `-b` | `api` or `claude-code` (default: claude-code) |
| `--output-dir` | `-o` | Override output directory |

## Processing an Entire Play

To analyze all scenes in a play, loop through acts and scenes:

### Henry V (5 acts)

```bash
PLAY=~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt

# Act 1: Scenes 1-2, Prologue
for scene in 1 2; do
    python ~/utono/nvim-glosses-qa/python/scene_analyzer.py "$PLAY" 1 $scene -m 15
done

# Act 2: Scenes 1-4, Prologue
for scene in 1 2 3 4; do
    python ~/utono/nvim-glosses-qa/python/scene_analyzer.py "$PLAY" 2 $scene -m 15
done

# Act 3: Scenes 1-7, Prologue
for scene in 1 2 3 4 5 6 7; do
    python ~/utono/nvim-glosses-qa/python/scene_analyzer.py "$PLAY" 3 $scene -m 15
done

# Act 4: Scenes 1-8, Prologue
for scene in 1 2 3 4 5 6 7 8; do
    python ~/utono/nvim-glosses-qa/python/scene_analyzer.py "$PLAY" 4 $scene -m 15
done

# Act 5: Scenes 1-2, Prologue, Epilogue
for scene in 1 2; do
    python ~/utono/nvim-glosses-qa/python/scene_analyzer.py "$PLAY" 5 $scene -m 15
done
```

### Generic Loop (All Plays)

For plays with unknown scene counts, use error suppression:

```bash
PLAY=~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt

for act in 1 2 3 4 5; do
    for scene in 1 2 3 4 5 6 7 8 9 10; do
        python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
            "$PLAY" $act $scene --merge 15 2>/dev/null || true
    done
done
```

### Batch Script

Create `~/utono/nvim-glosses-qa/python/analyze_play.sh`:

```bash
#!/bin/bash
# Usage: ./analyze_play.sh <play_file>

PLAY="$1"
MERGE=15

if [ -z "$PLAY" ]; then
    echo "Usage: $0 <play_file>"
    exit 1
fi

for act in 1 2 3 4 5; do
    for scene in 1 2 3 4 5 6 7 8 9 10; do
        echo "Trying Act $act, Scene $scene..."
        python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
            "$PLAY" $act $scene --merge $MERGE 2>/dev/null
    done
done

echo "Done processing $PLAY"
```

Make executable: `chmod +x ~/utono/nvim-glosses-qa/python/analyze_play.sh`

Run: `./analyze_play.sh ~/utono/literature/shakespeare-william/gutenberg/hamlet_gut.txt`

## Architecture

### Processing Flow

1. **Parse play file** - Locate act/scene boundaries using Roman numerals
2. **Extract speeches** - Each character's continuous dialogue = one unit
3. **Optionally merge** - Combine small speeches into larger chunks
4. **Check cache** - Skip units already in database (by content hash)
5. **Generate analysis** - Call Claude for each uncached unit
6. **Save to database** - Store each unit for future reuse
7. **Write markdown** - Aggregate all analyses into scene file

### Text Pattern Recognition

The parser uses regex patterns to identify structural elements:

| Element | Pattern | Example |
|---------|---------|---------|
| Act markers | `^ACT\s+[IVX]+\.\s*$` | "ACT IV." |
| Scene markers | `^SCENE\s+[IVX]+\.\s*(.*)$` | "SCENE VII. Another part..." |
| Speaker names | `^([A-Z][A-Z\s]+)\.\s*$` | "KING HENRY." |
| Stage directions | `^\[.*\]\s*$` | "[Exit]" |

**Dialogue lines:** Everything after a speaker name that isn't a stage
direction, new speaker, or act/scene marker is treated as dialogue belonging
to that speaker.

### Hybrid Storage

- **Database** (`~/utono/literature/gloss.db`): Granular, searchable cache
- **Markdown files**: Human-readable, organized by play/act/scene

### Caching Benefits

- Re-running skips cached speeches (shows `[CACHED]`)
- Partial runs resume where they left off
- Different merge thresholds create separate cache entries

## Play File Locations

Shakespeare plays (Gutenberg format):

```
~/utono/literature/shakespeare-william/gutenberg/
├── henry_v_gut.txt
├── hamlet_gut.txt
├── macbeth_gut.txt
├── midsummer_gut.txt
├── othello_gut.txt
├── romeo_juliet_gut.txt
└── ...
```

## Slash Command (nvim-glosses-qa)

In Claude Code with nvim-glosses-qa config:

```
/scene henry_v_gut.txt 4 7
/scene henry_v_gut.txt 4 7 --merge 15
/scene henry_v_gut.txt 4 7 --dry-run
```

## Example Output

Each scene file contains:

1. **Header** - Play name, act/scene, location
2. **Table of Contents** - All speakers with line counts
3. **Speech Analyses** - For each speech:
   - Original text (code block)
   - Line-by-line analysis (meaning, operative words, acting insight)
4. **Footer** - Generation timestamp, source file

## Troubleshooting

### Scene Not Found

```
Error: Scene 4.9 (Act IV, Scene IX) not found in henry_v_gut.txt
```

The scene doesn't exist. Use `--dry-run` to verify scene numbers.

### Claude Code Errors

If Claude Code backend fails, you can try the direct API as a fallback:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    play.txt 4 7 --backend api --merge 15
```

### Check Cache Status

```bash
# Preview which speeches are cached
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py play.txt 4 7 --dry-run
```

Output shows `[CACHED]` or `[NEW]` for each speech/chunk.
