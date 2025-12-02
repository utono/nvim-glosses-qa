Remove Elizabethan resonance terms from the database.

The user has provided terms to remove: $ARGUMENTS

If no arguments provided, remind the user:
```
Usage: /remove term1 term2 "multi word phrase"
Example: /remove nothing "star-crossed"
```

For each term provided:

1. **Check if it exists:**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT term, category, significance FROM elizabethan_terms WHERE term = '<term>'"
```

2. **If it exists, confirm and remove:**
```bash
sqlite3 ~/utono/literature/gloss.db "DELETE FROM elizabethan_terms WHERE term = '<term>'; SELECT changes();"
```

3. **After all removals, refresh the terms cache:**
```bash
sqlite3 ~/utono/literature/gloss.db \
  "SELECT term FROM elizabethan_terms WHERE approved = 1 ORDER BY term" \
  > ~/.config/nvim-glosses-qa/terms-cache.txt
```

Format your response:

```
REMOVING TERM: <term>
```

For each term, report the result:
- "Removed '<term>' from Elizabethan terms database."
- "Term '<term>' not found in database."

If removing multiple terms, summarize at the end:
"Removed [n] term(s). [m] term(s) not found."
