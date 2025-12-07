# Shakespeare Q&A Commands Reference

This document describes all slash commands and prompt patterns available in the
Claude Q&A terminal (opened with `<M-c>` from nvim-glosses).

## Quick Reference

### Slash Commands

| Command | Description |
|---------|-------------|
| `/new` | Clear history and show context summary |
| `/summarize` | Generate summary of conversation (optional) |
| `/save` | Save the most recent reply to addenda table |
| `/add <term>` | Add Elizabethan resonance term to catalogue |
| `/remove <term>` | Remove term from catalogue |
| `/term [word]` | List all terms, or get record for specific term |
| `/lookup <word>` | Search database broadly (glosses, terms, addenda) |
| `/db` | Show all available context from database |
| `/line-by-line` | Line-by-line close reading for actor rehearsal |
| `/lines <range>` | Analyze specific lines (e.g., `1-5`, `3,7,12`) |
| `/sounds [full]` | Sound-pattern analysis for voicing |
| `/discuss <word>` | Cross-canon analysis of a word |
| `/scene` | Generate scene analysis with caching |
| `/gloss-play` | Generate glosses for a play scene (in-session) |
| `/gloss-sounds` | Generate sound analysis for a play scene |
| `/analyze-plays` | Generate gloss-play scripts for all plays |
| `/teacher-gloss` | Generate glosses in acting teacher's voice |

---

## Slash Commands

### /add <terms>

Add Elizabethan resonance terms to the database.

**Usage:**
```
/add term1 term2 "multi word phrase"
/add nothing will "star-crossed"
```

**Workflow:**
1. Claude proposes each term with category and significance
2. You respond with `[a]pprove` or `[r]evise`
3. On approve, term is inserted into `elizabethan_terms` table
4. On revise, Claude asks what to change and re-proposes

**Categories:**
- Philosophical and Scientific Terms
- Social and Political Terms
- Theatre and Performance
- Words of Extremity and Paradox
- Words of Identity and Desire

---

### /remove <terms>

Remove Elizabethan resonance terms from the database.

**Usage:**
```
/remove term1 term2 "multi word phrase"
/remove nothing "star-crossed"
```

**Behavior:**
- Checks if each term exists before removing
- Reports success or "not found" for each term
- Summarizes: "Removed [n] term(s). [m] term(s) not found."

---

### /lookup <word>

Search the database for context about a word or phrase.

**Usage:**
```
/lookup ceremony
/lookup "star-crossed"
```

**Searches:**
1. Glosses (source text and translations)
2. Elizabethan terms database
3. Prior discussions (addenda)

**Output:**
- Count of glosses containing the term
- Elizabethan term entry (if exists)
- Mentions in prior discussions
- Relevance to current passage

---

### /db

Display all available database context for the current passage.

**Shows:**
- Current passage details (hash, source file, character, act, scene, tag)
- User's translation
- All approved Elizabethan terms by category
- Prior Q&A sessions for this passage
- Related glosses (same character or scene)
- Database totals (glosses, terms, addenda)

---

### /new

Clear conversation history and provide a summary of the loaded context.

**Use when:** Starting fresh or after a long conversation to reset history while
keeping context awareness.

**Provides summary of:**
- The passage (play, act, scene, what it's about)
- Your translation
- Catalogued terms that appear in this passage
- Prior discussions count
- Related glosses count

---

### /summarize

Generate a concise summary (2-4 paragraphs) of the conversation.

**Focus:**
- Main questions asked and their answers
- Key insights about the text
- Important historical or literary context
- Elizabethan terms or resonances identified

**Output:** Standalone summary suitable for database storage.

**Follow-up:** Reminds you to type `/save` to store the summary.

---

### /line-by-line

Perform a line-by-line close reading of the passage for actor rehearsal.

**Purpose:** Help actors understand, embody, and speak each line of the original
text through detailed analysis.

**Usage:**
```
/line-by-line
```

**For each line, provides:**
1. **The line** - quoted in bold
2. **Meaning** - what the line literally says (1-2 sentences)
3. **Operative word(s)** - which words must "land" for meaning to arrive
4. **Breath/thought** - where thought continues vs. completes; where to breathe
5. **Acting note** - one practical performance insight

**Example output:**
```
LINE 1: **"What infinite heart's ease must kings neglect"**

Meaning: What limitless peace of mind kings must give up.

Operative: "neglect" — not "lose" but actively ignore, sacrifice.

Breath: Thought continues to line 2; no breath after "neglect".

Acting: The question is bitter, not curious. Henry already knows
the answer. Weight on "infinite" — the loss is measureless.
```

**Practitioner vocabulary used:**
- "Operative word" (Barton) — the word that carries the argument
- "Thought-through-line" (Berry) — sustaining intention across complexity
- "Landing" (Hall) — making a word arrive for the audience
- "Second circle" (Rodenburg) — present, connected energy

**Performance challenges flagged:**
- Enjambment (thought runs over line end)
- Caesura (mid-line pause)
- Antithesis (balanced oppositions)
- Periodic structure (meaning delayed to line end)
- Inverted syntax (verb before subject)

---

### /save

Save the most recent Claude reply to the database.

**Saves to:** `addenda` table, linked to current passage via `gloss_hash`

**What to save:**
- A summary from `/summarize`
- A "discuss" analysis
- Any substantive reply worth preserving

**Confirmation:** Reports ID and timestamp of saved entry.

---

### /term [word]

Retrieve Elizabethan term records from the database.

**Usage:**
```
/term              # List all catalogued terms by category
/term ceremony     # Get full record for specific term
```

**Without argument:** Lists all approved terms grouped by category with totals.

**With argument:** Shows the full record including:
- Category
- Significance (explanation of Elizabethan resonance)
- Examples (if recorded)
- Date added and who proposed it

**If term not found:** Suggests `/add <term>` or `/lookup <term>`.

---

### /lines <range>

Analyze specific lines from the passage by number.

**Usage:**
```
/lines 1-5           # Range: lines 1 through 5
/lines 3,7,12        # List: lines 3, 7, and 12
/lines 1-3,8,10-12   # Mixed: lines 1-3, line 8, and lines 10-12
```

**Structure per line:**
1. The line quoted in bold
2. What it literally means (1-2 sentences)
3. Operative word(s) — which must "land"
4. Breath/thought guidance
5. Acting insight — one practical performance note

**Output format:** Flowing prose paragraphs (no labels like "Meaning:").

**After completion:** Offers to continue with more lines or explore deeper.

---

### /sounds [full]

Sound-pattern analysis focusing on vowels, consonants, and alliterative
patterns that should be "landed" for the audience.

**Usage:**
```
/sounds              # Analyze in sections with pauses
/sounds full         # Complete entire passage without pausing
```

**Structure per line:**
1. The line quoted in bold
2. What it literally means
3. Key sounds to land (specific vowels, consonants, clusters)
4. How sounds connect to meaning
5. Performance note on voicing

**Sound patterns identified:**
- Assonance (repeated vowels): long A in "graves," "native," "brave"
- Alliteration (initial consonants): "brave," "blood," "battle"
- Consonance (consonants anywhere): T in "tattered," "tottering"
- Sibilance (S/SH): hissing, whispering quality
- Plosives (P, B, T, D, K, G): explosive, percussive
- Nasals (M, N): humming, continuous
- Liquids (L, R): flowing, melting

**Summary:** After completion, lists 2-3 key recurring sounds and where they
appear.

---

### /discuss <word>

Scholarly analysis of how Shakespeare uses a word across his complete works.
(Also available as prompt pattern `discuss <word>`.)

**Usage:**
```
/discuss ceremony
/discuss nothing
/discuss quality of mercy
```

**Structure:**
1. **Etymology and Elizabethan meaning** — what the word meant to
   Shakespeare's audience (may differ from modern usage)
2. **Key appearances** — notable uses across tragedies, histories,
   comedies, romances, sonnets, and narrative poems
3. **Thematic patterns** — how Shakespeare deploys the word for dramatic
   effect
4. **Connection to current passage** — relevance to the passage being
   discussed

**Database integration:** Queries for other glosses containing the word,
checks elizabethan_terms table, notes prior discussions.

---

### /scene

Generate line-by-line actor analysis for an entire scene.

**Usage:**
```
/scene henry_v_gut.txt "Act IV, Scene VII"
/scene henry_v_gut.txt 4 7
/scene henry_v_gut.txt "Act IV, Scene VII" --merge 15
/scene henry_v_gut.txt 4 7 --dry-run
```

**Options:**
- `--merge N` or `-m N`: Merge speeches into N-line chunks (reduces API calls)
- `--dry-run` or `-n`: Preview without processing

**Output:** `~/utono/literature/glosses/{play}/act{N}_scene{M}_line-by-line.md`

**Features:**
- Parses play file to locate act/scene
- Extracts speeches (each character's continuous dialogue)
- Checks cache — skips already-analyzed speeches
- Saves each unit to database for reuse
- Produces unified markdown with all analyses

**Workflow with `<M-a>`:**
1. Navigate to scene in Neovim
2. Press `<M-a>` to copy "Act IV, Scene VII" to clipboard
3. Run `/scene henry_v_gut.txt "<paste>" --merge 15`

---

### /gloss-play

Generate line-by-line glosses for a play scene using the current Claude
session (no external API calls).

**Usage:**
```
/gloss-play ~/utono/literature/.../twelfth_night_gut.txt "Act I, Scene V"
/gloss-play twelfth-night "Act I, Scene V"
/gloss-play hamlet "Act III, Scene I"
```

**Workflow:**
1. Run `scene_analyzer.py --export-chunks` to get chunk data as JSON
2. For each non-cached chunk: generate analysis, save with `--save-chunk`
3. Run `scene_analyzer.py --build-from-cache` to build markdown

**Analysis style:** Elevated, theatrical prose with:
- Vivid paraphrase (not flat translation)
- Operative words explained with WHY they land
- Specific acting direction (physical, vocal, energy)
- Structural insights (enjambment, caesura, antithesis)
- Audience awareness and foreshadowing

**Output:** `~/utono/literature/glosses/<play>/act<N>_scene<M>_line-by-line.md`

---

### /gloss-sounds

Generate sound-pattern analysis for a play scene using the current session.

**Usage:**
```
/gloss-sounds henry-v "Act IV, Scene III"
/gloss-sounds hamlet "Act III, Scene I"
```

**Workflow:** Same as `/gloss-play` but with `--gloss-type sounds`.

**Analysis focus:**
- Specific vowel/consonant patterns per line
- How sounds connect across lines
- Vocal direction for landing sounds
- Sound-to-meaning connections

**Summary section:** After all chunks, adds "KEY SOUNDS TO LAND" with:
- Primary sounds threading through the scene
- Sonic arc of the scene

**Output:** `~/utono/literature/glosses/<play>/act<N>_scene<M>_sounds.md`

**When to use:** Especially valuable for set pieces, soliloquies, heightened
emotional moments, and passages difficult to voice.

---

### /teacher-gloss

Generate line-by-line glosses for a Shakespeare scene in the distinctive voice
and methodology of a classical acting teacher.

**Usage:**
```
/teacher-gloss /path/to/play.txt "Act II, Scene I"
/teacher-gloss /path/to/hamlet.txt "3 1"
/teacher-gloss /path/to/tempest.txt "Act I"
```

**Arguments:**
1. **Play file path** (required): Full path to the play text file
2. **Scene filter** (required): Act and scene specification
   - Formats: `"Act II, Scene I"`, `"Act 2, Scene 1"`, or `"2 1"`
   - Prologues: `"Act II, Prologue"` or `"2 0"`
   - Entire act: `"Act II"` or just `"2"`

**Teacher Selection:**
After running the command, you'll be prompted to select one or more teachers
(multi-select enabled):

1. **Peter Hall** (RSC founder, verse specialist)
   - Focus: iambic pentameter as heartbeat, honoring line endings, caesura,
     thought and breath alignment
   - Phrases: "Honor the line ending", "The verse tells you where to breathe",
     "Land that word"

2. **John Barton** (RSC director, *Playing Shakespeare* author)
   - Focus: antithesis, rhetoric as character, operative words, argument
     structure
   - Phrases: "Find the antithesis", "The rhetoric IS the character",
     "Balance the oppositions"

3. **Patsy Rodenburg** (Voice and presence expert)
   - Focus: three circles of energy, owning the text, presence, connection
     to the word
   - Phrases: "Stay in Second Circle", "Own that word", "Let it land in
     the room"

**Multiple Teachers:**
If you select multiple teachers, the command processes the scene once per
teacher, generating separate output files:
- `act2_scene1_teacher-hall.md`
- `act2_scene1_teacher-barton.md`
- `act2_scene1_teacher-rodenburg.md`

**Workflow:**
1. Export chunks: `scene_analyzer.py --export-chunks --gloss-type teacher-X`
2. Process each non-cached chunk with teacher-specific prompt
3. Save chunks: `scene_analyzer.py --save-chunk <hash> --gloss-type teacher-X`
4. Build markdown: `scene_analyzer.py --build-from-cache --gloss-type teacher-X`

**Output format per line:**
1. Line quoted in **bold**
2. Plain meaning (1-2 sentences)
3. Teacher-specific analysis (verse/rhetoric/energy)
4. Performance note in the teacher's voice

**Output:** `~/utono/literature/glosses/<play>/act<N>_scene<M>_teacher-<name>.md`

**Example header in output:**
```markdown
# Henry V - Act II, Scene I
## Line-by-Line Analysis in the Voice of John Barton

*"The rhetoric IS the character. Find the antithesis."*

---
```

**When to use:**
- Actor rehearsal preparation with specific methodological focus
- Comparing different pedagogical approaches to the same text
- Deep verse work (Hall), argument structure (Barton), or presence (Rodenburg)

---

### /analyze-plays

Generate gloss-play scripts for all Shakespeare plays.

**Usage:**
```
/analyze-plays                    # Generate scripts for all plays
/analyze-plays --help             # Show help
```

**What it does:** Runs `generate_gloss_scripts.py` to analyze all play files
in `~/utono/literature/shakespeare-william/gutenberg/` and generate shell
scripts for each play.

**Output:** `~/utono/nvim-glosses-qa/scripts/gloss-play_*.sh`

**Generated script features:**
- `--status`: Check processing status
- `--dry-run`: Preview without API calls
- `--resume`: Resume after interruption
- `--validate`: Validate output

**Example usage after generation:**
```bash
~/utono/nvim-glosses-qa/scripts/gloss-play_twelfth-night.sh --status
~/utono/nvim-glosses-qa/scripts/gloss-play_twelfth-night.sh --dry-run
~/utono/nvim-glosses-qa/scripts/gloss-play_twelfth-night.sh
```

---

## Prompt Patterns

These are natural language patterns (not slash commands) that trigger specific
response formats. Note that `discuss <word>` is also available as `/discuss`.

### explain <phrase>

Close reading of a specific phrase or line from the passage.

**Usage:**
```
explain twin-born with greatness
explain "subject to the breath of every fool"
```

**Structure:**
1. Opening statement placing phrase in dramatic context
2. Line-by-line analysis with bold quoted phrases
3. Synthesis connecting parts into thematic whole

---

## Database Tables

### glosses
User's translations created in XC.
- `hash` - unique identifier
- `source_text` - original Shakespeare text
- `gloss_text` - user's translation
- `character`, `act`, `scene`, `tag`

### elizabethan_terms
Words with special Elizabethan resonance.
- `term` - the word or phrase
- `category` - classification
- `significance` - explanation of resonance
- `approved` - whether term is active (1 = yes)

### addenda
Saved Q&A discussions.
- `gloss_hash` - links to a gloss
- `question` - brief topic descriptor
- `answer` - the saved reply
- `timestamp` - when saved

---

## Environment Variables

Available in the Q&A session:
- `$GLOSS_HASH` - unique identifier for current passage
- `$DB_PATH` - path to database (`~/utono/literature/gloss.db`)
- `$CHARACTER` - speaking character (if known)
- `$ACT` - act number (if known)
- `$SCENE` - scene number (if known)

---

## Typical Workflows

### Passage Q&A (from nvim-glosses)

1. Press `<M-c>` in nvim-glosses to open Q&A terminal
2. Ask questions about the passage
3. Use `/discuss <word>` for deep dives on specific terms
4. Use `/add <term>` to record Elizabethan resonances
5. Use `/summarize` to generate a summary
6. Use `/save` to store the summary in the database
7. Type `/done` or press `<M-c>` to close

### Scene-Level Glossing

1. Run `/analyze-plays` to generate scripts for all plays (one-time setup)
2. Use `/gloss-play <play> "Act N, Scene M"` to generate line-by-line glosses
3. Use `/gloss-sounds <play> "Act N, Scene M"` for sound analysis
4. Use `/teacher-gloss <play> "Act N, Scene M"` for teacher-voice analysis
5. Output files appear in `~/utono/literature/glosses/<play>/`

### Quick Line Analysis (in Q&A session)

1. Use `/lines 1-5` to analyze specific lines
2. Use `/sounds full` for sound-pattern analysis of entire passage
3. Use `/line-by-line` for complete passage analysis
