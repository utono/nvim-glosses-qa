Add Elizabethan resonance terms to the database for future reference.

The user has provided terms to add: $ARGUMENTS

If no arguments provided, remind the user:
```
Usage: /add term1 term2 "multi word phrase"
Example: /add nothing will "star-crossed"
```

For each term provided:

1. **Check if it already exists:**
```bash
sqlite3 ~/utono/literature/gloss.db \
  "SELECT term, category, significance FROM elizabethan_terms
   WHERE term = '<term>'"
```

If it exists, report: "Term '<term>' already exists." and skip to next term.

2. **Propose the addition** with category and significance:

```
PROPOSED TERM: <term>
CATEGORY: <one of the categories below>
SIGNIFICANCE: <1-2 sentence explanation>

[a]pprove  [r]evise
```

Categories:
- Philosophical and Scientific Terms
- Social and Political Terms
- Theatre and Performance
- Words of Extremity and Paradox
- Words of Identity and Desire

3. **Wait for user response:**

- **a or approve**: Insert the term and update the cache:
  ```bash
  sqlite3 ~/utono/literature/gloss.db \
    "INSERT INTO elizabethan_terms (term, category, significance, proposed_by)
     VALUES ('<term>', '<category>', '<significance>', 'claude');"
  ```
  Then refresh the terms cache:
  ```bash
  sqlite3 ~/utono/literature/gloss.db \
    "SELECT term FROM elizabethan_terms WHERE approved = 1 ORDER BY term" \
    > ~/.config/nvim-glosses-qa/terms-cache.txt
  ```
  Confirm: "Added '<term>' to database."

- **r or revise**: Ask what to change (category, significance, or both),
  then re-propose with changes.

Process terms one at a time, waiting for approval before moving to the next.
