Display all available database context for the current passage.

Run these queries and present a comprehensive reference:

**1. Current passage details:**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT id, hash, source_file, character, act, scene, tag, datetime(timestamp, 'localtime') as created FROM glosses WHERE hash = '$GLOSS_HASH'"
```

**2. User's translation:**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT gloss_text FROM glosses WHERE hash = '$GLOSS_HASH'"
```

**3. All approved Elizabethan terms:**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT term, category, substr(significance, 1, 80) as sig FROM elizabethan_terms WHERE approved = 1 ORDER BY category, term"
```

**4. Prior Q&A sessions for this passage:**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT id, question, substr(answer, 1, 100) as preview, datetime(timestamp, 'localtime') as when FROM addenda WHERE gloss_hash = '$GLOSS_HASH' ORDER BY timestamp"
```

**5. Related glosses by character:**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT COUNT(*) as count FROM glosses WHERE character = '$CHARACTER' AND hash != '$GLOSS_HASH'"
```

**6. Related glosses in same scene:**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT COUNT(*) as count FROM glosses WHERE act = '$ACT' AND scene = '$SCENE' AND hash != '$GLOSS_HASH'"
```

**7. Total database statistics:**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT (SELECT COUNT(*) FROM glosses) as glosses, (SELECT COUNT(*) FROM elizabethan_terms WHERE approved=1) as terms, (SELECT COUNT(*) FROM addenda) as addenda"
```

Present as a reference card:

```
DATABASE CONTEXT
================

CURRENT PASSAGE
  Hash: [hash]
  Source: [source_file]
  Character: [character]
  Location: Act [act], Scene [scene]
  Tag: [tag]
  Created: [timestamp]

USER'S TRANSLATION
  [gloss_text or "None recorded"]

ELIZABETHAN TERMS DATABASE ([count] terms)
  Categories:
  - Philosophical and Scientific Terms: [terms...]
  - Social and Political Terms: [terms...]
  - Theatre and Performance: [terms...]
  - Words of Extremity and Paradox: [terms...]
  - Words of Identity and Desire: [terms...]

PRIOR DISCUSSIONS ([count])
  [List with dates and previews]

RELATED CONTENT
  - [n] other glosses by [character]
  - [n] other glosses in Act [act] Scene [scene]

DATABASE TOTALS
  Glosses: [n] | Terms: [n] | Addenda: [n]
```
