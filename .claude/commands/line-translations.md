Generate line-by-line translations.
For a play or a scene, generate translations only - no dramaturgical
discussion, operative words, or acting notes.

**Arguments: $ARGUMENTS**

## Argument Format

```
/line-translations <play-file.txt> "Act N, Scene M"
```

Examples:
```
/line-translations ~/utono/literature/shakespeare-william/gutenberg/romeo_and_juliet_gut.txt "Act I, Scene I"
/line-translations ~/utono/literature/shakespeare-william/gutenberg/twelfth_night_gut.txt "Act I, Scene V"
/line-translations ~/utono/literature/shakespeare-william/gutenberg/hamlet_gut.txt "Act III, Scene I"
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

Extract play file path and act/scene from arguments.

The first argument must be a path to a `.txt` play file.
The second argument is the act/scene spec (e.g., "Act I, Scene V").

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

**CRITICAL - Physical Line Boundaries:**
Quote each PHYSICAL LINE from the source exactly as written, even when
sentences enjamb (continue across line breaks). Never combine lines.
Never truncate a line at punctuation.

**WRONG** (combining enjambed lines):
```
**"my lips so wide as a bristle may enter in way of thy excuse:"**

my lips even wide enough to let a bristle through, to make excuses.
```

**CORRECT** (respecting physical line breaks):
```
**"my lips so wide as a bristle may enter in way of thy excuse: my"**

my lips even wide enough to let a bristle through, to make

**"lady will hang thee for thy absence."**

excuses. My lady will hang you for being away so long.
```

Notice:
- Line 1 ends with "my" (mid-sentence) — quote it exactly
- Line 2 completes the sentence — quote it as a separate line
- The translation can flow naturally across the two entries

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
# Single scene
/line-translations ~/utono/literature/shakespeare-william/gutenberg/romeo_and_juliet_gut.txt "Act I, Scene I"
/line-translations ~/utono/literature/shakespeare-william/gutenberg/hamlet_gut.txt "Act III, Scene I"
/line-translations ~/utono/literature/shakespeare-william/gutenberg/henry_v_gut.txt "Act IV, Scene VII"
```
