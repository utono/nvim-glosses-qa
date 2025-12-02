# Shakespeare Q&A Commands Reference

This document describes all slash commands and prompt patterns available in the
Claude Q&A terminal (opened with `<M-c>` from nvim-glosses).

## Quick Reference

### Slash Commands

| Command | Description |
|---------|-------------|
| `/add <terms>` | Add Elizabethan terms (with approval) |
| `/db` | Display all available database context |
| `/line-by-line [full]` | Line-by-line close reading for actor rehearsal |
| `/lines <range>` | Analyze specific lines (e.g., `1-5`, `3,7,12`) |
| `/lookup <word>` | Search database for a word |
| `/new` | Clear history and show context summary |
| `/remove <terms>` | Remove terms from database |
| `/save` | Save last reply to database |
| `/summarize` | Generate conversation summary |
| `/term [word]` | List all terms, or get record for specific term |
| `/discuss <word>` | Scholarly analysis across Shakespeare's works |

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

### /line-by-line [full]

Perform a line-by-line close reading of the passage for actor rehearsal.

**Purpose:** Help actors understand, embody, and speak each line of the original
text through detailed analysis.

**Usage:**
```
/line-by-line        # Default: pauses every 4-6 lines
/line-by-line full   # Complete entire passage without pausing
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

**For long passages (>15 lines):** Breaks into sections and pauses between them
to check in with the actor (default mode) or uses section headers but continues
through to end (full mode).

---

### /lines <range>

Analyze specific lines from the passage.

**Purpose:** Focus on particular lines without analyzing the entire passage.

**Usage:**
```
/lines 1-5           # Lines 1 through 5
/lines 3,7,12        # Lines 3, 7, and 12
/lines 1-3,8,10-12   # Mixed ranges and individual lines
```

**Line counting:** Counts dialogue lines from the original text starting at 1.
Skips blank lines and character names when counting.

**Behavior:** Completes all requested lines without pausing.

**Same analysis structure as `/line-by-line`:** meaning, operative words,
breath/thought, and acting note for each line.

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

### /discuss <word>

Scholarly analysis of how Shakespeare uses a word across his complete works.

**Usage:**
```
/discuss ceremony
/discuss nothing
/discuss quality of mercy
```

**Structure:**
1. **Etymology and Elizabethan meaning** - what the word meant to Shakespeare's
   audience (may differ from modern usage)
2. **Key appearances** - notable uses across tragedies, histories, comedies,
   romances, sonnets, and narrative poems
3. **Thematic patterns** - how Shakespeare deploys the word for dramatic effect
4. **Connection to current passage** - relevance to the passage being discussed

**Note:** Claude queries the database first to find other glosses containing
the word.

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

## Typical Workflow

1. Press `<M-c>` in nvim-glosses to open Q&A terminal
2. Ask questions about the passage
3. Use `discuss <word>` for deep dives on specific terms
4. Use `/add <term>` to record Elizabethan resonances
5. Use `/summarize` to generate a summary
6. Use `/save` to store the summary in the database
7. Type `/done` or press `<M-c>` to close
