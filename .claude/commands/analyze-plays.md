Generate gloss-play scripts for Shakespeare plays.

**Arguments: $ARGUMENTS**

## Usage

```
/analyze-plays                    # Generate scripts for all plays
/analyze-plays --help             # Show this help
```

## What This Does

Runs `generate_gloss_scripts.py` to analyze all Shakespeare play files in
`~/utono/literature/shakespeare-william/gutenberg/` and generate shell scripts
for each play.

## Steps to Execute

### Step 1: Run the generator script

```bash
python ~/utono/nvim-glosses-qa/scripts/generate_gloss_scripts.py
```

### Step 2: Report results

Show the output from the script, which includes:
- Number of plays processed
- Scene count per play
- Total output files across all plays

### Step 3: Provide usage examples

After generation, remind the user how to use the scripts:

```bash
# Check status of a play
~/utono/nvim-glosses-qa/scripts/gloss-play_twelfth-night.sh --status

# Dry run (preview without API calls)
~/utono/nvim-glosses-qa/scripts/gloss-play_twelfth-night.sh --dry-run

# Process all scenes
~/utono/nvim-glosses-qa/scripts/gloss-play_twelfth-night.sh

# Resume after interruption
~/utono/nvim-glosses-qa/scripts/gloss-play_twelfth-night.sh --resume
```

## Script Location

Generator: `~/utono/nvim-glosses-qa/scripts/generate_gloss_scripts.py`
Output: `~/utono/nvim-glosses-qa/scripts/gloss-play_*.sh`

## Notes

- The generator automatically skips non-play files (sonnets, poems, metadata)
- Scripts handle various Gutenberg formatting quirks (ACT/Act, SCENE on same
  line as ACT, Roman/Arabic numerals)
- Each generated script supports: --status, --dry-run, --resume, --validate
- Merge threshold is set to 42 lines by default
