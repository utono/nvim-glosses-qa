Generate line-by-line glosses for a play scene using the current Claude session.

**Arguments: $ARGUMENTS**

## Argument Formats

```
/gloss-play <play-file-path> "Act N, Scene M"
/gloss-play <play-name> "Act N, Scene M"
```

Examples:
```
/gloss-play ~/utono/literature/.../twelfth_night_gut.txt "Act I, Scene V"
/gloss-play twelfth-night "Act I, Scene V"
/gloss-play hamlet "Act III, Scene I"
```

## How This Works

This command processes scene chunks **directly in the current Claude Code
session** - no external API calls are made. The workflow:

1. Run `scene_analyzer.py --export-chunks` to get chunk data as JSON
2. For each non-cached chunk, generate line-by-line analysis directly
3. Save results to database and write the output markdown file

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
- `output_dir`, `output_filename`
- `chunks[]` - each with `text`, `hash`, `cached`, `cached_text`

### Step 3: Process each chunk

For each chunk in the JSON:

**If `cached` is true:** Use the `cached_text` directly.

**If `cached` is false:** Generate the line-by-line analysis.

#### Line-by-Line Analysis Instructions

For each non-cached chunk, perform a line-by-line close reading for actor
rehearsal. Work through the original text one line at a time.

**For each line, provide in flowing prose:**

1. The line itself quoted in **bold**
2. What it literally means (1-2 sentences)
3. The operative word(s) - which must "land" for meaning to arrive
4. Acting insight - one practical performance note

**Do NOT use labels** like "Meaning:", "Operative:", "Acting:".
**Do NOT number lines** like "LINE 1:", "LINE 2:".
Write each analysis as a cohesive paragraph.

**Format Example:**

```
**"What infinite heart's ease must kings neglect"**

What limitless peace of mind kings must give up. The operative word
is "neglect" - not "lose" but actively ignore, sacrifice. The question
is bitter, not curious. Henry already knows the answer. Weight on
"infinite" - the loss is measureless.

**"That private men enjoy?"**

That ordinary people have freely. "Private" is the word Henry envies;
"enjoy" lands the contrast. The comparison is complete. "Private men"
isn't contemptuous - it's wistful. These are the people Henry wishes
he could be.
```

**Use practitioner vocabulary:**
- "Operative word" (Barton) - the word that carries the argument
- "Thought-through-line" (Berry) - sustaining intention across complexity
- "Landing" (Hall) - making a word arrive for the audience
- "Second circle" (Rodenburg) - present, connected energy

**Flag performance challenges:**
- Enjambment (thought runs over line end)
- Caesura (mid-line pause)
- Antithesis (balanced oppositions to shape vocally)
- Periodic structure (meaning delayed to line end)
- Inverted syntax (verb before subject)

**SPEAKER ATTRIBUTION:**
If the chunk contains multiple speakers (names in ALL CAPS followed by a
period), include the speaker name in ALL CAPS on its own line BEFORE
analyzing that character's lines.

### Step 4: Save results to database

After generating analysis for a chunk, save it to the database:

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, str(__import__('pathlib').Path.home() / 'utono/xc/nvim/python'))
from gloss import GlossDatabase

db = GlossDatabase()
db.setup()

chunk_hash = "<CHUNK_HASH>"
chunk_text = """<CHUNK_TEXT>"""
analysis = """<ANALYSIS_TEXT>"""

# Create passage record
metadata = {
    'play_name': '<PLAY_NAME>',
    'act': '<ACT>',
    'scene': '<SCENE>',
}
db.get_or_create_passage(chunk_hash, chunk_text, metadata)

# Save as line-by-line gloss
filename = f"{chunk_hash[:8]}_chunk_line-by-line.md"
db.save(chunk_hash, chunk_text, analysis, filename, 'line-by-line', metadata)

# Save to addenda
db.save_addendum(chunk_hash, "Line-by-line analysis", analysis)
print(f"Saved chunk {chunk_hash[:8]}")
EOF
```

### Step 5: Build output markdown

After processing all chunks, build the scene document:

```markdown
# <Play Name>
## Act <N>, Scene <M>

*<Scene Header>*

---

### 1. <Speaker Name>

#### Original Text
```
<chunk text>
```

#### Line-by-Line Analysis

<analysis>

---

[repeat for each chunk]

*Generated: <timestamp>*
*Source: <play_file>*
```

Write to: `<output_dir>/<output_filename>`

### Step 6: Report results

After completion:
- Report number of chunks processed (cached vs new)
- Show output file path
- Note any errors

## Database Location

`~/utono/literature/gloss.db`

## Output Location

`~/utono/literature/glosses/<play-name>/act<N>_scene<M>_line-by-line.md`

## Flags (for --export-chunks only)

| Flag | Purpose |
|------|---------|
| `--dry-run` | Preview chunks without processing |
| `--status` | Show cache status only |

## Examples

```
# Single scene by file path
/gloss-play ~/utono/literature/.../twelfth_night_gut.txt "Act I, Scene V"

# Single scene by play name
/gloss-play hamlet "Act III, Scene I"
/gloss-play henry-v "Act IV, Scene VII"

# Check what would be processed
/gloss-play twelfth-night "Act I, Scene V" --dry-run
```
