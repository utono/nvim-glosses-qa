Add Elizabethan resonance terms to the database for future reference.

The user has provided terms to add: $ARGUMENTS

If no arguments provided, remind the user:
```
Usage: /add term1 term2 "multi word phrase" 'another phrase'
Example: /add nothing will "star-crossed"
```

For each term provided:

1. **Check if it already exists:**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT term, category, significance FROM elizabethan_terms WHERE term = '<term>'"
```

2. **Determine an appropriate category** from:
   - Philosophical and Scientific Terms
   - Social and Political Terms
   - Theatre and Performance
   - Words of Extremity and Paradox
   - Words of Identity and Desire
   - (or suggest a new category if none fit)

3. **Write a brief significance** explaining why this word/phrase carried special resonance for Elizabethan audiences

Format your response as database entries:

```
ADDING TERM: <term>
CATEGORY: <category>
SIGNIFICANCE: <1-2 sentence explanation>
```

Repeat for each term.

After formatting all terms, run the insert commands:
```bash
sqlite3 ~/utono/literature/gloss.db "INSERT OR IGNORE INTO elizabethan_terms (term, category, significance, proposed_by, approved) VALUES ('<term>', '<category>', '<significance>', 'claude', 1);"
```

Confirm each addition: "Added '<term>' to Elizabethan terms database."

If a term already exists, report: "Term '<term>' already exists in database."
