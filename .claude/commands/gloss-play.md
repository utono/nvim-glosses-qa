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
2. For each non-cached chunk: generate analysis, then save with `--save-chunk`
3. Run `scene_analyzer.py --build-from-cache` to build the markdown file

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

**If `cached` is true:** Skip - already in database.

**If `cached` is false:** Generate analysis, then save to database.

---

## Line-by-Line Analysis Prompt

Perform a line-by-line close reading for actor rehearsal. Work through the
**original text** one line at a time, helping the actor understand, embody,
and speak each line.

### Structure for Each Line

For each line, provide in flowing prose:

1. The line itself quoted in **bold**
2. What it literally means (1-2 sentences) — THE TRANSLATION
3. A blank line after the translation
4. The operative word(s) - which must "land" for meaning to arrive
5. Acting insight - one practical performance note

**CRITICAL FORMAT:** After the translation (item 2), insert a BLANK LINE
before continuing with operative words and acting notes. This separates
the plain meaning from the dramaturgical analysis.

**Do NOT use labels** like "Meaning:", "Operative:", "Acting:".
**Do NOT number lines** like "LINE 1:", "LINE 2:".
Write each analysis as a cohesive paragraph (after the translation).

### Elevated Style Requirements

The goal is theatrical, evocative analysis — not flat translation. Each gloss
should feel like a director's note that helps an actor embody the line.

**1. Vivid Paraphrase**
Don't just translate — capture the energy:
- FLAT: "England's youth are excited about war"
- ELEVATED: "England's young men burn with martial energy"

**2. Operative Words Explained**
Don't just identify — explain WHY the word lands:
- WEAK: "'Fire' is the operative word"
- STRONG: "The operative word is 'fire' — not merely eager, but aflame
  with passion for war"

**3. Specific Acting Direction**
Give physical, vocal, and energy notes:
- "Let the vowel open the speech"
- "Weight 'all' to paint the totality"
- "The line must kindle that heat in the room"
- "Make the shift visible — the world contracts to these two"

**4. Structural Insights Integrated**
Note rhetorical features as acting challenges:
- "The enjambment suspends 'three' — the number hangs, incomplete"
- "The dash pivots sharply from intimacy to logistics"
- "The antithesis is implicit: fire vs. silk, war vs. play"

**5. Audience Awareness**
Connect to theatrical effect:
- "Let the audience see him not seeing"
- "Let it hang in the air"
- "The audience knows what Orsino cannot"

**6. Physical/Spatial Awareness**
Ground abstract language in the body and stage:
- "Let 'wardrobe' be physical — we see the chest closing"
- "The shift must be physical — Viola's body changes"

**7. Immediate Dramatic Context**
Name what the character is DOING, not just saying:
- "This is benediction — Romeo blessing Juliet as he watches her sleep"
- "Romeo speaks as priest and lover simultaneously"

**8. Double Meanings and Wordplay**
Note when words carry multiple meanings:
- "'So sweet to rest' lands with double meaning: rest sweetly AND rest
  with her"
- "'Admit' works doubly: allow entry and accept emotionally"

**9. Foreshadowing and Shadows**
When words carry weight beyond their immediate meaning:
- "'Ghostly' means spiritual (the Friar is his confessor), but the word
  carries death's shadow"
- "The audience knows what Orsino cannot"

**10. Character Shifts Within Speech**
Note when the character's role or energy changes:
- "He's a supplicant now, not a lover-priest"
- "The line turns inward — he's no longer blessing her, he's mourning
  his separation"
- "Romeo moves from lyric contemplation to plot mechanics"

**11. Etymology When Enriching**
Period-specific meanings that deepen understanding:
- "'Dear hap' is stunning compression: 'hap' (fortune, chance) modified
  by 'dear' (precious, costly)"
- "'Nuncio' — papal envoy, formal diplomat"

**12. Structural Pivots**
Note when form signals meaning:
- "The rhyming couplet snaps the speech shut"
- "The syntax is inverted — 'will I to' instead of 'I will go to' —
  giving the line formality, perhaps self-discipline"

### Format Example

```
**"Now all the youth of England are on fire"**

England's young men burn with martial energy.

The operative word is "fire" — not merely eager, but
aflame with passion for war. The Chorus speaks with
rising excitement, inviting the audience into this
fever. The line must kindle that heat in the room.
Weight "all" to paint the totality of this change.

**"And silken dalliance in the wardrobe lies"**

Soft peacetime pleasures are packed away like silk.

"Dalliance" is the key — courtship, flirtation, leisure
all abandoned. "Lies" completes the thought: these things
are dormant, not destroyed. The antithesis is implicit:
fire vs. silk, war vs. play. Let "wardrobe" be physical —
we see the chest closing.
```

### Format Example 2: Romeo and Juliet

```
ROMEO.

**"Sleep dwell upon thine eyes peace in thy breast!"**

May sleep rest on your eyes, peace fill your heart.

This is benediction — Romeo blessing Juliet as he
watches her sleep. The operative words are "dwell"
and "peace" — not fleeting rest but permanent
residence. The syntax is compressed, almost liturgical:
no comma between "eyes" and "peace" creates rhythmic
urgency. Romeo speaks as priest and lover.

**"Would I were sleep and peace so sweet to rest!"**

I wish I could be that sleep and peace, so I could
rest as sweetly with you.

"Would I were" carries the operative weight —
subjunctive longing, impossible wish. Romeo wants to
dissolve into the abstractions he just invoked. "So
sweet to rest" lands doubly: rest sweetly AND rest
with her. The line turns inward — he's mourning his
separation now.

**"Hence will I to my ghostly father's cell"**

From here I'll go to my spiritual father's room.

"Hence" is the operative — departure, movement away.
"Ghostly" means spiritual (the Friar is his confessor),
but the word carries death's shadow. The syntax is
inverted — "will I to" instead of "I will go to" —
giving formality, perhaps self-discipline. Romeo pulls
himself from reverie into action.

**"His help to crave and my dear hap to tell."**

To beg his help and tell him my precious fortune.

The operative words are "crave" and "hap" — he's a
supplicant now, not a lover-priest. "Dear hap" is
stunning compression: "hap" (fortune, chance) modified
by "dear" (precious, costly). The rhyming couplet snaps
the speech shut — Romeo moves from contemplation to
plot mechanics. The actor must shift energy: from
communion with sleeping Juliet to forward momentum.
```

### Guidance

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

**Connect to character psychology:**
- Why does the character choose THESE words?
- What does the syntax reveal about their mental state?
- Where is the character thinking vs. performing?

### Critical Requirements

- Complete ALL lines in the chunk
- Output ONLY the line-by-line analyses
- Do NOT add preamble like "I'll work through..." or "Let me analyze..."
- Do NOT add closing remarks like "That's the full passage..."
- Do NOT offer follow-up questions
- Do NOT use --- or separators between line analyses
- Begin IMMEDIATELY with the first line in bold

**LINE WIDTH:** Wrap all prose at 65 characters maximum. This ensures
proper display in the terminal viewer. Break lines at natural phrase
boundaries — never mid-word, rarely mid-phrase.

**SPEAKER ATTRIBUTION:**
If the chunk contains multiple speakers (names in ALL CAPS followed by a
period), include the speaker name in ALL CAPS on its own line BEFORE
analyzing that character's lines. Example:

```
CANTERBURY.

**"Hear him but reason in divinity"**
[analysis...]

ELY.

**"It would be all in all to him"**
[analysis...]
```

---

### Step 4: Save chunk to database

After generating analysis for a chunk, save it using `--save-chunk`:

```bash
cat << 'CHUNK_EOF' | python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    "<play-file>" "<act/scene-spec>" --merge 42 --save-chunk <CHUNK_HASH>
<ANALYSIS_TEXT>
CHUNK_EOF
```

The script reads the analysis from stdin and saves it to the database.

**Workflow per chunk:**
1. Generate analysis for chunk
2. Pipe analysis to `--save-chunk` with the chunk's hash
3. Verify "Saved chunk XXXXXXXX" output
4. Proceed to next chunk

### Step 5: Build markdown from cache

After ALL chunks are saved, build the markdown file:

```bash
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    "<play-file>" "<act/scene-spec>" --merge 42 --build-from-cache
```

This verifies all chunks are cached and builds the output markdown.

### Step 6: Report results

After completion:
- Report number of chunks processed (cached vs new)
- Show output file path
- Note any errors

## Database Location

`~/utono/literature/gloss.db`

## Output Location

`~/utono/literature/glosses/<play-name>/act<N>_scene<M>_line-by-line.md`

## Command Reference

| Flag | Purpose |
|------|---------|
| `--export-chunks` | Export chunk data as JSON (no API calls) |
| `--save-chunk HASH` | Save analysis for chunk (reads from stdin) |
| `--build-from-cache` | Build markdown from all cached chunks |
| `--dry-run` | Preview chunks without processing |
| `--status` | Show cache status only |
| `--merge N` | Merge speeches into N-line chunks |

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
