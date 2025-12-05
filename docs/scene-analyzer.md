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
│   ├── prologue_line-by-line.md          # Opening Prologue
│   ├── act1_scene1_line-by-line.md
│   ├── act1_scene2_line-by-line.md
│   ├── act2_prologue_line-by-line.md     # Act 2 Prologue
│   ├── act2_scene1_line-by-line.md
│   ├── ...
│   └── epilogue_line-by-line.md          # Epilogue
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

### Prologues and Epilogues

Henry V has a unique structure with Chorus prologues before each act:

```bash
# Opening Prologue (before Act 1) - use act=0, scene=0
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt \
    "Prologue"
# Or: ... 0 0

# Act-specific Prologues (e.g., Act 2 Prologue) - use act=N, scene=0
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt \
    "Act 2, Prologue"
# Or: ... 2 0

# Epilogue - use scene=-1
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt \
    "Epilogue"
# Or: ... 0 -1
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

## Analyzing the Entirety of Henry V

Henry V has a unique structure with **Chorus prologues** before each act and
an **Epilogue**. The complete structure:

| Act | Scenes | Notes |
|-----|--------|-------|
| - | Prologue | Opening Prologue (act=0, scene=0) |
| 1 | 1-2 | "ACT FIRST" format |
| 2 | Prologue, 1-4 | |
| 3 | Prologue, 1-7 | |
| 4 | Prologue, 1-8 | Includes Agincourt battle |
| 5 | Prologue, 1-2 | |
| - | Epilogue | (act=0, scene=-1) |

### Complete Script for Henry V

```bash
#!/bin/bash
# analyze_henry_v.sh - Analyze the entirety of Henry V
# Usage: ./analyze_henry_v.sh [--dry-run]

PLAY=~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt
ANALYZER=~/utono/nvim-glosses-qa/python/scene_analyzer.py
MERGE=15
DRY_RUN=""

# Check for --dry-run flag
if [ "$1" = "--dry-run" ] || [ "$1" = "-n" ]; then
    DRY_RUN="--dry-run"
    echo "=== DRY RUN MODE ==="
fi

echo "Analyzing Henry V..."
echo "Play file: $PLAY"
echo "Merge threshold: $MERGE lines"
echo ""

# Opening Prologue (before Act 1)
echo "=== Opening Prologue ==="
python "$ANALYZER" "$PLAY" 0 0 -m $MERGE $DRY_RUN

# Act 1: 2 scenes (no prologue - "ACT FIRST" is the act header)
echo "=== Act 1 ==="
for scene in 1 2; do
    echo "--- Act 1, Scene $scene ---"
    python "$ANALYZER" "$PLAY" 1 $scene -m $MERGE $DRY_RUN
done

# Act 2: Prologue + 4 scenes
echo "=== Act 2 ==="
echo "--- Act 2, Prologue ---"
python "$ANALYZER" "$PLAY" 2 0 -m $MERGE $DRY_RUN
for scene in 1 2 3 4; do
    echo "--- Act 2, Scene $scene ---"
    python "$ANALYZER" "$PLAY" 2 $scene -m $MERGE $DRY_RUN
done

# Act 3: Prologue + 7 scenes
echo "=== Act 3 ==="
echo "--- Act 3, Prologue ---"
python "$ANALYZER" "$PLAY" 3 0 -m $MERGE $DRY_RUN
for scene in 1 2 3 4 5 6 7; do
    echo "--- Act 3, Scene $scene ---"
    python "$ANALYZER" "$PLAY" 3 $scene -m $MERGE $DRY_RUN
done

# Act 4: Prologue + 8 scenes
echo "=== Act 4 ==="
echo "--- Act 4, Prologue ---"
python "$ANALYZER" "$PLAY" 4 0 -m $MERGE $DRY_RUN
for scene in 1 2 3 4 5 6 7 8; do
    echo "--- Act 4, Scene $scene ---"
    python "$ANALYZER" "$PLAY" 4 $scene -m $MERGE $DRY_RUN
done

# Act 5: Prologue + 2 scenes
echo "=== Act 5 ==="
echo "--- Act 5, Prologue ---"
python "$ANALYZER" "$PLAY" 5 0 -m $MERGE $DRY_RUN
for scene in 1 2; do
    echo "--- Act 5, Scene $scene ---"
    python "$ANALYZER" "$PLAY" 5 $scene -m $MERGE $DRY_RUN
done

# Epilogue
echo "=== Epilogue ==="
python "$ANALYZER" "$PLAY" 0 -1 -m $MERGE $DRY_RUN

echo ""
echo "=== Complete ==="
echo "Output directory: ~/utono/literature/glosses/henry-v/"
```

### One-liner (Copy/Paste Ready)

```bash
# Analyze ALL of Henry V (prologues + all scenes + epilogue)
PLAY=~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt && \
ANALYZER=~/utono/nvim-glosses-qa/python/scene_analyzer.py && \
python "$ANALYZER" "$PLAY" 0 0 -m 15 && \
for s in 1 2; do python "$ANALYZER" "$PLAY" 1 $s -m 15; done && \
python "$ANALYZER" "$PLAY" 2 0 -m 15 && \
for s in 1 2 3 4; do python "$ANALYZER" "$PLAY" 2 $s -m 15; done && \
python "$ANALYZER" "$PLAY" 3 0 -m 15 && \
for s in 1 2 3 4 5 6 7; do python "$ANALYZER" "$PLAY" 3 $s -m 15; done && \
python "$ANALYZER" "$PLAY" 4 0 -m 15 && \
for s in 1 2 3 4 5 6 7 8; do python "$ANALYZER" "$PLAY" 4 $s -m 15; done && \
python "$ANALYZER" "$PLAY" 5 0 -m 15 && \
for s in 1 2; do python "$ANALYZER" "$PLAY" 5 $s -m 15; done && \
python "$ANALYZER" "$PLAY" 0 -1 -m 15
```

### Dry Run First (Recommended)

Preview what will be processed before committing:

```bash
# Preview the Opening Prologue
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt \
    0 0 --dry-run

# Preview a specific scene
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt \
    4 7 --dry-run --merge 15
```

### Scene-by-Scene Commands (Individual)

If you prefer to run scenes individually:

```bash
PLAY=~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt
ANALYZER=~/utono/nvim-glosses-qa/python/scene_analyzer.py

# Opening Prologue
python "$ANALYZER" "$PLAY" 0 0 -m 15

# Act 1
python "$ANALYZER" "$PLAY" 1 1 -m 15
python "$ANALYZER" "$PLAY" 1 2 -m 15

# Act 2
python "$ANALYZER" "$PLAY" 2 0 -m 15   # Prologue
python "$ANALYZER" "$PLAY" 2 1 -m 15
python "$ANALYZER" "$PLAY" 2 2 -m 15
python "$ANALYZER" "$PLAY" 2 3 -m 15
python "$ANALYZER" "$PLAY" 2 4 -m 15

# Act 3
python "$ANALYZER" "$PLAY" 3 0 -m 15   # Prologue
python "$ANALYZER" "$PLAY" 3 1 -m 15
python "$ANALYZER" "$PLAY" 3 2 -m 15
python "$ANALYZER" "$PLAY" 3 3 -m 15
python "$ANALYZER" "$PLAY" 3 4 -m 15
python "$ANALYZER" "$PLAY" 3 5 -m 15
python "$ANALYZER" "$PLAY" 3 6 -m 15
python "$ANALYZER" "$PLAY" 3 7 -m 15

# Act 4
python "$ANALYZER" "$PLAY" 4 0 -m 15   # Prologue
python "$ANALYZER" "$PLAY" 4 1 -m 15
python "$ANALYZER" "$PLAY" 4 2 -m 15
python "$ANALYZER" "$PLAY" 4 3 -m 15
python "$ANALYZER" "$PLAY" 4 4 -m 15
python "$ANALYZER" "$PLAY" 4 5 -m 15
python "$ANALYZER" "$PLAY" 4 6 -m 15
python "$ANALYZER" "$PLAY" 4 7 -m 15
python "$ANALYZER" "$PLAY" 4 8 -m 15

# Act 5
python "$ANALYZER" "$PLAY" 5 0 -m 15   # Prologue
python "$ANALYZER" "$PLAY" 5 1 -m 15
python "$ANALYZER" "$PLAY" 5 2 -m 15

# Epilogue
python "$ANALYZER" "$PLAY" 0 -1 -m 15
```

### Expected Output Files

After full analysis, you'll have:

```
~/utono/literature/glosses/henry-v/
├── prologue_line-by-line.md           # Opening Prologue
├── act1_scene1_line-by-line.md
├── act1_scene2_line-by-line.md
├── act2_prologue_line-by-line.md
├── act2_scene1_line-by-line.md
├── act2_scene2_line-by-line.md
├── act2_scene3_line-by-line.md
├── act2_scene4_line-by-line.md
├── act3_prologue_line-by-line.md
├── act3_scene1_line-by-line.md
├── act3_scene2_line-by-line.md
├── act3_scene3_line-by-line.md
├── act3_scene4_line-by-line.md
├── act3_scene5_line-by-line.md
├── act3_scene6_line-by-line.md
├── act3_scene7_line-by-line.md
├── act4_prologue_line-by-line.md
├── act4_scene1_line-by-line.md
├── act4_scene2_line-by-line.md
├── act4_scene3_line-by-line.md
├── act4_scene4_line-by-line.md
├── act4_scene5_line-by-line.md
├── act4_scene6_line-by-line.md
├── act4_scene7_line-by-line.md
├── act4_scene8_line-by-line.md
├── act5_prologue_line-by-line.md
├── act5_scene1_line-by-line.md
├── act5_scene2_line-by-line.md
└── epilogue_line-by-line.md
```

**Total: 28 files** (1 opening prologue + 5 act prologues + 21 scenes +
1 epilogue)

## Processing an Entire Play (Generic)

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

Run: `./analyze_play.sh ~/path/to/hamlet_gut.txt`

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
| Act (ordinal) | `^ACT\s+(FIRST\|SECOND\|...)` | "ACT FIRST." |
| Scene markers | `^SCENE\s+[IVX]+\.\s*(.*)$` | "SCENE VII. Another..." |
| Prologue | `^PROLOGUE\.\s*$` | "PROLOGUE." |
| Epilogue | `^EPILOGUE\.\s*$` | "EPILOGUE." |
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

## Slash Commands

### `/scene` - Analyze a Single Scene

In Claude Code with nvim-glosses-qa config:

```
/scene henry_v_gut.txt 4 7
/scene henry_v_gut.txt 4 7 --merge 15
/scene henry_v_gut.txt 4 7 --dry-run
```

### `/analyze-play` - Generate Full-Play Analysis Script

Automatically discovers the structure of a Shakespeare play and generates a
tailored shell script to analyze all acts, scenes, prologues, and epilogues.

**Usage:**

```
/analyze-play ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt
/analyze-play ~/utono/literature/shakespeare-william/gutenberg/hamlet_gut.txt
```

**What it does:**

1. Reads the play file and identifies all structural markers
2. Detects opening prologues, act prologues, scenes, and epilogues
3. Generates a custom shell script for that specific play
4. Saves the script to `~/utono/nvim-glosses-qa/scripts/analyze_{play}.sh`

**Example output for Henry V:**

```
## Play Structure: Henry V

| Act | Content |
|-----|---------|
| - | Opening Prologue |
| 1 | 2 scenes |
| 2 | Prologue + 4 scenes |
| 3 | Prologue + 7 scenes |
| 4 | Prologue + 8 scenes |
| 5 | Prologue + 2 scenes |
| - | Epilogue |

**Total output files:** 28

Script saved to: ~/utono/nvim-glosses-qa/scripts/analyze_henry-v.sh
```

**Running the generated script:**

```bash
# Preview what will be processed (recommended first)
~/utono/nvim-glosses-qa/scripts/analyze_henry-v.sh --dry-run

# Run the full analysis
~/utono/nvim-glosses-qa/scripts/analyze_henry-v.sh
```

**Benefits over manual scripting:**

- Automatically handles plays with different structures
- Detects prologues that appear before acts vs. between acts
- Correctly identifies epilogues
- Generates accurate scene counts per act
- Uses consistent `--merge 15` threshold for efficiency

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
