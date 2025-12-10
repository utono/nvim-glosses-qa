Generate line-by-line translations.
For a play or a scene, generate translations only - no dramaturgical
discussion, operative words, or acting notes.

**Arguments: $ARGUMENTS**

## Argument Formats

```
/line-translations <play-file-path> "Act N, Scene M"
/line-translations <play-name> "Act N, Scene M"
```

Examples:
```
/line-translations ~/utono/literature/.../romeo_and_juliet_gut.txt "Act I, Scene I"
/line-translations twelfth-night "Act I, Scene V"
/line-translations hamlet "Act III, Scene I"
```

## How This Works

This command processes scene chunks **directly in the current Claude Code
session** — no external API calls are made. The workflow:

1. Run `scene_analyzer.py --export-chunks` to get chunk data as JSON
2. For each non-cached chunk: generate translation, then save with
   `--save-chunk --line-translations-only`
3. Report results

**Note:** This command saves ONLY to the `line_translations` table. It does
NOT write to the glosses table and does NOT generate markdown output.

## Steps to Execute

### Step 1: Parse arguments

Extract play file and act/scene from arguments.

**Format detection:**
- Contains `/` or ends with `.txt` → direct file path
- Otherwise → play name (find file from gloss script)

**For play name format**, extract PLAY_FILE from the gloss script:
```bash
SCRIPT=~/utono/nvim-glosses-qa/scripts/gloss-play_<play-name>.sh
rg "^PLAY_FILE=" "$SCRIPT" | cut -d'=' -f2 | tr -d '"'
```

### Step 2: Export chunks

Run scene_analyzer.py with --export-chunks to get chunk data:

```bash
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    "<play-file>" "<act/scene-spec>" --merge 42 --export-chunks
```

This outputs JSON with:
- `play_name`, `act`, `scene`, `scene_header`
- `chunks[]` - each with `text`, `hash`, `cached`, `cached_text`

### Step 3: Process each chunk

For each chunk in the JSON:

**If `cached` is true:** Skip — already in database.

**If `cached` is false:** Generate translation, then save to database.

---

## Line-by-Line Translation Prompt

Generate a line-by-line translation of this chunk. Work through the
**original text** one line at a time, providing a clear modern English
rendering of each line.

### Structure for Each Line

For each line, provide:

1. The line itself quoted in **bold**
2. A blank line
3. The translation (1-2 sentences of clear modern English)

**Do NOT add:**
- Operative word analysis
- Acting insights or performance notes
- Labels like "Meaning:", "Translation:"
- Line numbers like "LINE 1:", "LINE 2:"
- Separators (---) between lines

### Format Example

```
**"What infinite heart's ease must kings neglect"**

What limitless peace of mind kings must give up.

**"That private men enjoy?"**

That ordinary people have freely.

**"And what have kings that privates have not too"**

And what do kings have that ordinary men don't also have?

**"Save ceremony, save general ceremony?"**

Except ceremony — nothing but public ritual and display.
```

### Critical Requirements

- Complete ALL lines in the chunk
- Output ONLY the line-by-line translations
- Do NOT add preamble like "I'll translate..." or "Here's the chunk..."
- Do NOT add closing remarks like "That's the translation..."
- Do NOT offer follow-up questions
- Begin IMMEDIATELY with the first line in bold

**LINE WIDTH:** Wrap all prose at 65 characters maximum. This ensures
proper display in the terminal viewer. Break lines at natural phrase
boundaries — never mid-word, rarely mid-phrase.

**SPEAKER ATTRIBUTION:**
If the chunk contains multiple speakers (names in ALL CAPS followed by a
period), include the speaker name in ALL CAPS on its own line BEFORE
that character's lines:

```
SAMPSON.

**"Gregory, on my word, we'll not carry coals."**

Gregory, I swear we won't put up with insults.

GREGORY.

**"No, for then we should be colliers."**

No, because then we'd be coal-carriers — lowly workers.
```

---

### Step 4: Save chunk to database

After generating translation for a chunk, save it using `--save-chunk`:

```bash
cat << 'CHUNK_EOF' | python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    "<play-file>" "<act/scene-spec>" --merge 42 --save-chunk <CHUNK_HASH> \
    --line-translations-only
<TRANSLATION_TEXT>
CHUNK_EOF
```

The script reads the translation from stdin and saves it to the database.
The `--line-translations-only` flag saves ONLY to `line_translations` table
(skips passages/glosses/addenda).

**Workflow per chunk:**
1. Generate translation for chunk
2. Pipe translation to `--save-chunk` with the chunk's hash
3. Verify "Saved N line translations" output
4. Proceed to next chunk

### Step 5: Report results

After completion:
- Report number of chunks processed (cached vs new)
- Report total line translations saved
- Note any errors

## Database Location

`~/utono/literature/gloss.db`

## Command Reference

| Flag | Purpose |
|------|---------|
| `--export-chunks` | Export chunk data as JSON (no API calls) |
| `--save-chunk HASH` | Save translation for chunk (reads from stdin) |
| `--line-translations-only` | Only save to line_translations (skip glosses) |
| `--dry-run` | Preview chunks without processing |
| `--status` | Show cache status only |
| `--merge N` | Merge speeches into N-line chunks |

## Examples

```
# Single scene by file path
/line-translations ~/utono/literature/.../romeo_and_juliet_gut.txt "Act I, Scene I"

# Single scene by play name
/line-translations hamlet "Act III, Scene I"
/line-translations henry-v "Act IV, Scene VII"

# Check what would be processed
/line-translations twelfth-night "Act I, Scene V" --dry-run
```
