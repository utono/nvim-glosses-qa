Re-initialize the session with fresh database context after /clear.

Run these queries to rebuild context:

**1. Get the gloss hash:**
```bash
echo $GLOSS_HASH
```

**2. Get the current passage and user's translation:**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT source_text, gloss_text, character, act, scene, tag FROM glosses WHERE hash = '$GLOSS_HASH'"
```

**3. Get Elizabethan terms that appear in the passage:**
First get all approved terms, then check which appear in the source text from the system prompt.
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT term, category, significance FROM elizabethan_terms WHERE approved = 1 ORDER BY term"
```

**4. Get prior discussions about this passage:**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT question, substr(answer, 1, 200) as answer_preview, datetime(timestamp, 'localtime') as when FROM addenda WHERE gloss_hash = '$GLOSS_HASH' ORDER BY timestamp"
```

**5. Find related glosses (same character or scene):**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT source_text FROM glosses WHERE hash != '$GLOSS_HASH' AND (character = '$CHARACTER' OR (act = '$ACT' AND scene = '$SCENE')) LIMIT 5"
```

Present this as a formatted context summary:

```
SESSION CONTEXT RESTORED
========================

PASSAGE: [from system prompt]

USER'S TRANSLATION: [from query 2]

CHARACTER: [name] | ACT: [n] SCENE: [n]

ELIZABETHAN TERMS IN PASSAGE:
- [term]: [significance]
...

PRIOR DISCUSSIONS: [count]
- [date]: [preview]
...

RELATED GLOSSES: [count] by same character, [count] in same scene

Ready to continue. What would you like to explore?
```
