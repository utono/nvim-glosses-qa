Generate sound-pattern analysis for a play scene using the current session.

**Arguments: $ARGUMENTS**

## Argument Formats

```
/gloss-sounds <play-file-path> "Act N, Scene M"
/gloss-sounds <play-name> "Act N, Scene M"
```

Examples:
```
/gloss-sounds ~/utono/literature/.../henry_v_gut.txt "Act IV, Scene III"
/gloss-sounds henry-v "Act IV, Scene III"
/gloss-sounds hamlet "Act III, Scene I"
```

## How This Works

This command processes scene chunks **directly in the current Claude Code
session** - no external API calls are made. The workflow:

1. Run `scene_analyzer.py --export-chunks --gloss-type sounds` to get chunks
2. For each non-cached chunk: generate analysis, then save with `--save-chunk`
3. Run `scene_analyzer.py --build-from-cache --gloss-type sounds` to build md

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

Run scene_analyzer.py with --export-chunks and --gloss-type sounds:

```bash
python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    "<play-file>" "<act/scene-spec>" --merge 42 \
    --export-chunks --gloss-type sounds
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

## Sound-Landing Analysis Prompt

Perform a line-by-line close reading for actor rehearsal, focusing on
**SOUND PATTERNS to "land."**

Your goal: Help the actor identify recurring sounds (vowels, consonants,
alliterative patterns) that run through the passage and should be "landed"
— given weight and clarity — so the audience hears and feels them.

### Structure for Each Line

For each line, provide in flowing prose:

1. The line itself quoted in **bold**
2. What it literally means (1-2 sentences)
3. The KEY SOUNDS to land — specific vowel sounds, consonants, or sound
   clusters that recur and should be emphasized
4. How these sounds connect to meaning — why did Shakespeare choose these
   particular sounds for this content?
5. Performance note on voicing these sounds

**Do NOT use labels** like "Meaning:", "Sounds:", "Performance:".
**Do NOT number lines** like "LINE 1:", "LINE 2:".
Write each analysis as a cohesive paragraph.

### Sound Pattern Categories

**Identify these patterns:**

| Pattern | Description | Example |
|---------|-------------|---------|
| ASSONANCE | Repeated vowel sounds | long A in "graves," "native," "brave" |
| ALLITERATION | Repeated initial consonants | "brave," "blood," "battle" |
| CONSONANCE | Repeated consonants anywhere | T in "tattered," "tottering" |
| SIBILANCE | S and SH sounds | hissing, whispering quality |
| PLOSIVES | P, B, T, D, K, G | explosive, percussive effect |
| NASALS | M, N | humming, continuous quality |
| LIQUIDS | L, R | flowing, melting quality |

### Elevated Style Requirements

The goal is theatrical, evocative analysis that helps the actor HEAR and
VOICE the sounds. Each analysis should feel like a voice coach's note.

**1. Name the Sound Precisely**
Don't just say "vowel sounds" — specify which:
- WEAK: "There are repeated vowel sounds"
- STRONG: "The long A dominates — 'graves,' 'native,' 'brave' — a mournful,
  open sound the actor should lean into"

**2. Connect Sound to Meaning**
Explain WHY these sounds serve the content:
- "The sibilance in 'witness,' 'brass,' 'this day's' creates a sound of
  permanence — the hiss of something being sealed"
- "The plosive T's in 'tattered,' 'tottering' enact the violence they
  describe"

**3. Give Vocal Direction**
Tell the actor HOW to voice it:
- "Let the mouth open on each long A"
- "Feel the stopped energy of the T before releasing it"
- "Sustain the M through the line — don't clip it"

**4. Track Sounds Across Lines**
Show how sounds weave through the passage:
- "The long A continues from the previous line — keep threading it"
- "This introduces a new sound (hard K) that will return in line 5"

**5. Note Sonic Contrasts**
When sounds shift, mark the change:
- "The contrast between open A and stopped T creates the passage's sonic
  tension"
- "After all those soft L sounds, the hard G of 'grave' lands like a blow"

### Format Example

```
**"A many of our bodies shall no doubt"**

Many of us will certainly die. The long A sounds dominate — "A many,"
"shall" — creating a mournful, open quality. Let the mouth open on
each long A; the sound itself carries the grief of anticipated loss.
This sustained vowel weaves through the whole passage and must be
landed consistently.

**"Find native graves upon the which I trust"**

We'll find graves in our homeland, which I believe. The long A
continues in "graves" and "native" — keep threading this vowel
through. "Trust" introduces a harder T sound that will return. The
contrast between open A and stopped T creates the passage's sonic
tension.

**"Shall witness live in brass of this day's work"**

Will testify forever to what we do today. "Brass" lands the long A
one final time while introducing sibilant S sounds in "witness,"
"brass," "this day's." Feel both the sustained A vowel and the
hissing energy of these S consonants — together they create a sound
of permanence and memorial.
```

### Guidance

**Use practitioner vocabulary:**
- "Landing" (Hall/Barton) — giving a sound full value so it arrives
- "Voicing through" — sustaining a sound quality across phrases
- "Sound painting" — using vocal texture to create meaning
- "Operative sound" — the recurring sound that carries the argument

**For each line, ask:**
- What sounds recur within this line?
- What sounds connect this line to previous/following lines?
- Does the sound match the meaning (harsh sounds for harsh content)?
- Where should the actor "land" a sound for the audience?

**Connect sound to meaning:**
- Why these sounds for this content?
- How does the sound shape emotional impact?
- Where does Shakespeare use sound for emphasis?

### Critical Requirements

- Complete ALL lines in the chunk
- Output ONLY the sound analyses
- Do NOT add preamble like "I'll work through..." or "Let me analyze..."
- Do NOT add closing remarks
- Do NOT offer follow-up questions
- Begin IMMEDIATELY with the first line in bold

**SPEAKER ATTRIBUTION:**
If the chunk contains multiple speakers (names in ALL CAPS followed by a
period), include the speaker name in ALL CAPS on its own line BEFORE
analyzing that character's lines.

### After Final Chunk: Summary

After processing ALL chunks, add a summary section:

```
---

## KEY SOUNDS TO LAND

**Primary sounds threading through this scene:**

1. [SOUND 1]: [Where it appears, what it does emotionally]
2. [SOUND 2]: [Where it appears, what it does emotionally]
3. [SOUND 3]: [Where it appears, what it does emotionally]

**Sonic arc of the scene:**
[2-3 sentences on how the sound palette shifts through the scene]
```

---

### Step 4: Save chunk to database

After generating analysis for a chunk, save it using `--save-chunk`:

```bash
cat << 'CHUNK_EOF' | python ~/utono/nvim-glosses-qa/python/scene_analyzer.py \
    "<play-file>" "<act/scene-spec>" --merge 42 \
    --save-chunk <CHUNK_HASH> --gloss-type sounds
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
    "<play-file>" "<act/scene-spec>" --merge 42 \
    --build-from-cache --gloss-type sounds
```

This verifies all chunks are cached and builds the output markdown.

### Step 6: Add sound summary

After building from cache, add the KEY SOUNDS TO LAND summary section to the
end of the output file. This summarizes the primary sounds threading through
the scene and the sonic arc.

### Step 7: Report results

After completion:
- Report number of chunks processed (cached vs new)
- Show output file path
- List the 2-3 key sounds identified

## Output Location

`~/utono/literature/glosses/<play-name>/act<N>_scene<M>_sounds.md`

## Examples

```
# Single scene by file path
/gloss-sounds ~/utono/literature/.../henry_v_gut.txt "Act IV, Scene III"

# Single scene by play name (St. Crispin's Day speech)
/gloss-sounds henry-v "Act IV, Scene III"

# Hamlet's soliloquy
/gloss-sounds hamlet "Act III, Scene I"
```

## When to Use Sound Analysis

Sound analysis is especially valuable for:

- **Set pieces and soliloquies** where Shakespeare crafts dense sound textures
- **Heightened emotional moments** where sound carries feeling
- **Choral/rhetorical passages** (Chorus speeches, funeral orations)
- **Passages the actor finds "difficult to voice"** — sound awareness often
  unlocks them
