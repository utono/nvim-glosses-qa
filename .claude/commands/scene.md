Generate line-by-line actor analysis for an entire scene.

**Arguments: $ARGUMENTS**

Parse the arguments to extract:
`<play_file> <act_scene> [--merge N] [--dry-run]`

Where `<act_scene>` can be:
- `"Act IV, Scene VII"` (from `<M-a>` clipboard)
- `4 7` (numeric)

## Usage

```
/scene henry_v_gut.txt "Act IV, Scene VII"
/scene henry_v_gut.txt 4 7
/scene henry_v_gut.txt "Act IV, Scene VII" --merge 15
/scene henry_v_gut.txt 4 7 --dry-run
```

## What This Does

1. **Parses the play file** to locate Act N, Scene M
2. **Extracts speeches** - each character's continuous dialogue becomes one unit
3. **Optionally merges** small speeches into larger chunks (--merge N)
4. **Checks cache** - skips speeches/chunks already analyzed (by content hash)
5. **Generates analysis** - calls Claude for each uncached unit
6. **Saves to database** - each unit stored individually for future reuse
7. **Produces markdown** - unified scene file with all analyses

## Options

- `--merge N` or `-m N`: Merge consecutive speeches until reaching N lines.
  Reduces API calls significantly (e.g., 53 speeches → 10 chunks with -m 15)
- `--dry-run` or `-n`: Show what would be processed without calling API

## Output

Creates: `~/utono/literature/glosses/{play}/act{N}_scene{M}_line-by-line.md`

Directory structure:
```
~/utono/literature/glosses/
├── henry-v/
│   ├── act1_scene1_line-by-line.md
│   ├── act4_scene7_line-by-line.md
│   └── ...
├── hamlet/
│   └── ...
└── macbeth/
    └── ...
```

The file contains:
- Scene header and location
- Table of contents (all speakers)
- For each speech/chunk:
  - Original text
  - Line-by-line actor analysis (meaning, operative words, acting insight)

## Execution

Run the scene analyzer CLI:

```bash
# Process speech by speech (granular caching)
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py <play_file> <act> <scene>

# Merge small speeches into ~15-line chunks (faster)
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py <play_file> <act> <scene> --merge 15

# Dry run to preview
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py <play_file> <act> <scene> --dry-run
```

## Play File Locations

Shakespeare plays are in: `~/utono/literature/shakespeare-william/gutenberg/`

Common files:
- `henry_v_gut.txt` - Henry V
- `hamlet_gut.txt` - Hamlet
- `macbeth_gut.txt` - Macbeth
- `midsummer_gut.txt` - A Midsummer Night's Dream

## Example Session

User: `/scene henry_v_gut.txt "Act IV, Scene VII" --merge 15`

1. Parse arguments: play=henry_v_gut.txt, act_scene="Act IV, Scene VII", merge=15
2. Resolve full path if needed
3. Run: `python ~/utono/nvim-glosses-qa/python/scene_analyzer.py ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt "Act IV, Scene VII" --merge 15`
4. Report progress and final output location

## Workflow with `<M-a>`

1. In Neovim, navigate to the scene you want to analyze
2. Press `<M-a>` to copy "Act IV, Scene VII" to system clipboard
3. Run `/scene henry_v_gut.txt "<paste>" --merge 15`

## Notes

- **Caching**: Previously analyzed units retrieved from database (fast)
- **Hybrid storage**: Both database (granular) and markdown file (readable)
- **Speech boundaries**: Natural dramatic units when not merging
- **Merge trade-off**: Fewer API calls but less granular caching
- **Recommended**: Use `--merge 15` for initial processing, no merge for reruns
