# Shakespeare Q&A Commands Reference

This document describes all slash commands and prompt patterns available in the
Claude Q&A terminal (opened with `<M-c>` from nvim-glosses).

## Quick Reference

### Slash Commands

| Command | Description |
|---------|-------------|
| `/add <terms>` | Add Elizabethan terms (with approval) |
| `/remove <terms>` | Remove terms from database |
| `/lookup <word>` | Search database for a word |
| `/context` | Show all database context |
| `/reset` | Restore context after `/clear` |
| `/summarize` | Generate conversation summary |
| `/save` | Save last reply to database |

### Prompt Patterns

| Pattern | Description |
|---------|-------------|
| `explain <phrase>` | Close reading with line-by-line analysis |
| `discuss <word>` | Scholarly analysis across Shakespeare's works |

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

### /context

Display all available database context for the current passage.

**Shows:**
- Current passage details (hash, source file, character, act, scene, tag)
- User's translation
- All approved Elizabethan terms by category
- Prior Q&A sessions for this passage
- Related glosses (same character or scene)
- Database totals (glosses, terms, addenda)

---

### /reset

Re-initialize session context after using `/clear`.

**Use when:** You've run `/clear` to reset conversation history and want to
restore database context.

**Restores:**
- Current passage and user's translation
- Prior discussions about this passage
- Related gloss counts

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

### /save

Save the most recent Claude reply to the database.

**Saves to:** `addenda` table, linked to current passage via `gloss_hash`

**What to save:**
- A summary from `/summarize`
- A "discuss" analysis
- Any substantive reply worth preserving

**Confirmation:** Reports ID and timestamp of saved entry.

---

## Prompt Patterns

These are not slash commands - just type them directly.

### explain <phrase>

Close reading with line-by-line analysis of a specific phrase or passage.

**Usage:**
```
explain twin-born with greatness
explain the quality of mercy
```

**Structure:**
1. Opening statement placing the phrase in dramatic context
2. Line-by-line analysis with **bold** quoted phrases
3. Synthesis paragraph connecting parts into thematic whole

**Example output:**
```
This is Henry's bitter complaint about kingship's paradox:

**"O hard condition / Twin-born with greatness"** The "hard
condition" (burden) is born as a twin alongside greatness — you
cannot have royal power without this weight. They arrive together
at birth, inseparable.

**"subject to the breath / Of every fool"** Despite being king,
Henry is "subject to" — subordinate to, at the mercy of —
what every fool says ("breath" = speech, opinion). The irony
stings: the ruler is ruled by public opinion.

The compression is masterful: Henry must bear responsibility for
everyone, yet endure criticism from people who can only think
about themselves.
```

---

### discuss <word>

Scholarly analysis of how Shakespeare uses a word across his complete works.

**Usage:**
```
discuss ceremony
discuss the quality of mercy
discuss nothing
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
