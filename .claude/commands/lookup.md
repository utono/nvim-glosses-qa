Search the database for context about: $ARGUMENTS

If no argument provided, ask the user what word or phrase to look up.

Run these queries:

**1. Search in glosses (source text and translations):**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT source_text, gloss_text FROM glosses WHERE source_text LIKE '%$ARGUMENTS%' OR gloss_text LIKE '%$ARGUMENTS%' LIMIT 10"
```

**2. Search in Elizabethan terms:**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT term, category, significance FROM elizabethan_terms WHERE (term LIKE '%$ARGUMENTS%' OR significance LIKE '%$ARGUMENTS%') AND approved = 1"
```

**3. Search in prior discussions (addenda):**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT gloss_hash, substr(answer, 1, 150) as preview FROM addenda WHERE answer LIKE '%$ARGUMENTS%' LIMIT 5"
```

Present findings in this format:

```
LOOKUP: "$ARGUMENTS"
====================

GLOSSES CONTAINING THIS TERM: [count]
- "[source excerpt]..." -> "[translation excerpt]..."
...

ELIZABETHAN TERM ENTRY:
Category: [category]
Significance: [significance]
(or "Not in Elizabethan terms database")

MENTIONED IN PRIOR DISCUSSIONS: [count]
- [hash]: "[preview]..."
...

RELEVANCE TO CURRENT PASSAGE:
[Explain how this relates to the passage being discussed]
```

If proposing to add as an Elizabethan term, use the format:
```
PROPOSED TERM: $ARGUMENTS
CATEGORY: [appropriate category]
SIGNIFICANCE: [explanation]
```
