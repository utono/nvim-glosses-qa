Generate line-by-line glosses for a play, act, or specific scene.

**Arguments: $ARGUMENTS**

## Argument Formats

### Format 1: Play name with optional act/scene filter
```
/gloss-play <play-name> ["Act N" | "Act N, Scene M"] [--flags]
```

Examples:
```
# Entire play
/gloss-play hamlet

# Single act (all scenes in that act)
/gloss-play hamlet "Act III"
/gloss-play henry-v "Act 4"

# Single scene
/gloss-play hamlet "Act III, Scene I"
/gloss-play twelfth-night "Act I, Scene V"

# With flags
/gloss-play macbeth --status
/gloss-play hamlet "Act III" --dry-run
```

### Format 2: Direct play file with optional act/scene filter
```
/gloss-play <play-file-path> ["Act N" | "Act N, Scene M"]
```

Examples:
```
# Entire play
/gloss-play ~/utono/literature/.../romeo_and_juliet_gut.txt

# Single act
/gloss-play ~/utono/literature/.../hamlet_gut.txt "Act III"

# Single scene
/gloss-play ~/utono/literature/.../romeo_and_juliet_gut.txt "Act II, Scene II"
/gloss-play ~/utono/literature/.../henry_v_gut.txt "Act 4, Scene 7"
```

## What This Does

**For specific scene:**
1. Parses the act and scene from the specification
2. Runs scene_analyzer.py directly for that single scene
3. Generates line-by-line glosses for actor rehearsal

**For specific act (all scenes):**
1. Parses the act number from the specification
2. Queries the play file to find all scenes in that act
3. Runs scene_analyzer.py for each scene in sequence
4. Reports results for all scenes

**For entire play:**
1. Determines script path from play name or file
2. Checks cache status (if no flags provided)
3. Auto-adds `--resume` if cached scenes exist
4. Runs the script with flags
5. Reports results

## Parsing the Act/Scene Specification

Accept flexible formats:

**Act-only (all scenes in act):**

| Input | Act | Scene |
|-------|-----|-------|
| `"Act III"` | 3 | all |
| `"Act 4"` | 4 | all |
| `"act 1"` | 1 | all |

**Specific scene:**

| Input | Act | Scene |
|-------|-----|-------|
| `"Act II, Scene II"` | 2 | 2 |
| `"Act 2, Scene 2"` | 2 | 2 |
| `"Act III Scene I"` | 3 | 1 |
| `"Act 4 Scene 7"` | 4 | 7 |
| `"act 1 scene 5"` | 1 | 5 |

Roman numerals: I=1, II=2, III=3, IV=4, V=5, VI=6, VII=7

**Detection logic:** If input contains "Scene" → specific scene; otherwise → act-only

## Steps to Execute

### Step 1: Parse arguments

**Identify format:**

- First arg contains `/` or ends with `.txt` → Format 2 (direct file path)
- Otherwise → Format 1 (play name)

**Identify mode:**

- Second arg contains "Scene" → **single scene mode**
- Second arg contains "Act" but not "Scene" → **act-only mode**
- No act/scene arg (or only flags) → **entire play mode**

**Examples:**
```
hamlet                        → Format 1, entire play
hamlet "Act III"              → Format 1, act-only (act 3)
hamlet "Act III, Scene I"     → Format 1, single scene
hamlet --status               → Format 1, entire play with flag
~/path/play.txt               → Format 2, entire play
~/path/play.txt "Act 2"       → Format 2, act-only (act 2)
~/path/play.txt "Act 2 Sc 3"  → Format 2, single scene
```

### Step 2: Resolve play file path

**For Format 1 (play name):**
```bash
# Find the play file from the gloss script
SCRIPT=~/utono/nvim-glosses-qa/scripts/gloss-play_<play-name>.sh
# Extract PLAY_FILE from script: grep "^PLAY_FILE=" "$SCRIPT"
```

**For Format 2 (direct path):**
- Use the provided path directly

Verify the play file exists before proceeding.

### Step 3: Parse act/scene specification

Convert Roman numerals to Arabic: I=1, II=2, III=3, IV=4, V=5, VI=6, VII=7

**For single scene mode:**
- Extract act number and scene number

**For act-only mode:**
- Extract act number
- Find all scenes in that act:
```bash
rg "^SCENE [IVXLC]+\." "<play-file>" | rg "ACT <N>" -A1 | \
    rg "^SCENE" | sed 's/SCENE //' | cut -d'.' -f1
```
  Or parse the script for scene numbers in that act.

### Step 4: Execute based on mode

**Single scene mode:**
```bash
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    "<play-file>" <act> <scene> --merge 42
```

**Act-only mode:**
For each scene in the act:
```bash
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    "<play-file>" <act> <scene> --merge 42
```
Run sequentially, report progress after each scene.

**Entire play mode:**
1. Check if script exists:
   `~/utono/nvim-glosses-qa/scripts/gloss-play_<play-name>.sh`
2. If no flags provided, check cache status:
   ```bash
   <script-path> --status
   ```
3. Auto-add `--resume` if cached scenes exist
4. Run the script:
   ```bash
   <script-path> <flags>
   ```

### Step 5: Handle script not found (entire play mode)

If no script exists for the play name:
```bash
ls ~/utono/nvim-glosses-qa/scripts/gloss-play_*.sh
```
Suggest running `/analyze-plays` to generate the script.

### Step 6: Monitor and report

Watch output for:
- `[FAILED]` markers
- `[CLAUDE_ACTION_REQUIRED]` markers
- Success messages

Report:
- Scene(s) processed
- Any failures
- Output file location

## Available Flags (entire play mode only)

| Flag | Purpose |
|------|---------|
| `--dry-run` | Preview without API calls |
| `--status` | Show cache status |
| `--validate` | Verify all scenes exist |
| `--resume` | Skip cached scenes |

## Output Locations

Single scene output: `~/utono/literature/glosses/<play-name>/act<N>_scene<M>.md`
Entire play output: `~/utono/literature/glosses/<play-name>/`

## Error Recovery

If scene analysis fails:
1. Check logs: `~/utono/nvim-glosses-qa/logs/scene_analyzer.log`
2. Retry the specific scene with the direct command

## Examples

```
# Single scene by play name
/gloss-play hamlet "Act III, Scene I"
/gloss-play twelfth-night "Act I, Scene V"

# Single act by play name (processes all scenes in act)
/gloss-play hamlet "Act III"
/gloss-play henry-v "Act 4"

# Single scene by file path
/gloss-play ~/utono/literature/.../romeo_and_juliet_gut.txt "Act II, Scene II"

# Single act by file path
/gloss-play ~/utono/literature/.../hamlet_gut.txt "Act III"

# Entire play by file path
/gloss-play ~/utono/literature/.../hamlet_gut.txt

# Entire play by name
/gloss-play hamlet

# Check status
/gloss-play macbeth --status
```
