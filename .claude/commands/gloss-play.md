Generate line-by-line glosses for a play or specific scene.

**Arguments: $ARGUMENTS**

## Argument Formats

The command accepts two formats:

### Format 1: Direct play file with optional scene
```
/gloss-play <play-file-path> ["Act N, Scene M"]
```

Examples:
```
# Entire play
/gloss-play ~/utono/literature/.../romeo_and_juliet_gut.txt

# Specific scene (various formats accepted)
/gloss-play ~/utono/literature/.../romeo_and_juliet_gut.txt "Act II, Scene II"
/gloss-play ~/utono/literature/.../henry_v_gut.txt "Act 4, Scene 7"
/gloss-play ~/utono/literature/.../hamlet_gut.txt "Act III Scene I"
```

### Format 2: Play name (uses pre-generated script)
```
/gloss-play <play-name> [--flags]
```

Examples:
```
/gloss-play henry-v
/gloss-play hamlet --dry-run
/gloss-play macbeth --status
```

## What This Does

**For specific scene (Format 1 with act/scene):**
1. Parses the act and scene from the specification
2. Runs scene_analyzer.py directly for that single scene
3. Generates line-by-line glosses for actor rehearsal

**For entire play (Format 1 without act/scene or Format 2):**
1. Determines script path or uses play file directly
2. Checks cache status (if no flags provided)
3. Auto-adds `--resume` if cached scenes exist
4. Runs the script with flags
5. Reports results

## Parsing the Act/Scene Specification

Accept flexible formats for the scene specification:

| Input | Act | Scene |
|-------|-----|-------|
| `"Act II, Scene II"` | 2 | 2 |
| `"Act 2, Scene 2"` | 2 | 2 |
| `"Act III Scene I"` | 3 | 1 |
| `"Act 4 Scene 7"` | 4 | 7 |
| `"act 1 scene 5"` | 1 | 5 |

Roman numerals: I=1, II=2, III=3, IV=4, V=5, VI=6, VII=7

## Steps to Execute

### Step 1: Parse arguments

Determine which format is being used:

**If first argument contains `/` or ends with `.txt`** → Format 1 (direct file)
- Extract file path (first argument)
- Check if second argument exists and looks like act/scene spec
- If act/scene spec found → single scene mode
- If no act/scene spec → entire play mode

**Otherwise** → Format 2 (play name with script)
- Treat as play name, construct script path
- Remaining arguments are flags

### Step 2a: Single Scene Mode (Format 1 with act/scene)

Parse the act/scene specification:
```
# Extract act number (convert Roman to Arabic if needed)
# Extract scene number (convert Roman to Arabic if needed)
```

Verify the play file exists.

Run scene_analyzer.py directly:
```bash
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    "<play-file>" <act> <scene> --merge 42
```

Report the result and output location.

### Step 2b: Entire Play Mode (Format 1 without act/scene or Format 2)

**For Format 1 (direct file path):**
- Derive play name from filename
  (e.g., `romeo_and_juliet_gut.txt` → `romeo-and-juliet`)
- Look for matching script in `~/utono/nvim-glosses-qa/scripts/`
- If no script found, inform user to run `/analyze-plays` first

**For Format 2 (play name):**
- Construct script path: `~/utono/nvim-glosses-qa/scripts/gloss-play_<name>.sh`

### Step 3: Verify script/file exists

For single scene mode: verify play file exists.
For entire play mode: verify script exists.

If not found, list available options:
```bash
ls ~/utono/nvim-glosses-qa/scripts/gloss-play_*.sh
```

### Step 4: Auto-detect cached scenes (entire play mode only)

**Skip if user provided flags or in single scene mode.**

Run the script with `--status` to check cache state:
```bash
<script-path> --status
```

Parse output for:
- "Cached: N scenes"
- "Pending: M scenes"

**Decision logic:**
- Cached > 0 AND Pending > 0: Add `--resume` flag automatically
- Cached > 0 AND Pending = 0: Report "All scenes cached" and stop
- Cached = 0: Run normally

### Step 5: Run the command

**Single scene:**
```bash
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    "<play-file>" <act> <scene> --merge 42
```

**Entire play:**
```bash
<script-path> <flags>
```

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
# Single scene - the balcony scene
/gloss-play ~/utono/literature/.../romeo_and_juliet_gut.txt "Act II, Scene II"

# Single scene - Henry V before Agincourt
/gloss-play ~/utono/literature/.../henry_v_gut.txt "Act IV, Scene I"

# Entire play by file path
/gloss-play ~/utono/literature/.../hamlet_gut.txt

# Entire play by name
/gloss-play hamlet

# Check status
/gloss-play macbeth --status
```
