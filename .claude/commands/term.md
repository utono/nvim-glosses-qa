Retrieve the database record for an Elizabethan resonant term: $ARGUMENTS

**If no argument provided**, list all catalogued terms:

```bash
sqlite3 ~/utono/literature/gloss.db \
  "SELECT term, category FROM elizabethan_terms
   WHERE approved = 1 ORDER BY category, term"
```

Display grouped by category:

```
ELIZABETHAN TERMS CATALOGUE
═══════════════════════════

Social and Political Terms:
  ceremony, honour, blood, ...

Theatre and Performance:
  shadow, show, ...

[etc.]

Total: <count> terms

→ /term <word> for full details on a specific term
→ /add <word> to add a new term
```

**If argument provided**, query the elizabethan_terms table for the exact term:

```bash
sqlite3 ~/utono/literature/gloss.db \
  "SELECT term, category, significance, examples, proposed_by,
   datetime(timestamp, 'localtime') as added
   FROM elizabethan_terms
   WHERE term = '$ARGUMENTS' AND approved = 1"
```

**If the term exists**, display it formatted:

```
ELIZABETHAN TERM: "<term>"
════════════════════════════════════════

Category:     <category>
Significance: <significance>
Examples:     <examples or "none recorded">
Added:        <date> (by <proposed_by>)
```

Then offer:
- "discuss <term>" to explore its use across Shakespeare's works
- Note if the term appears in the current passage

**If the term does not exist**, report:

```
"<term>" is not in your Elizabethan terms catalogue.

→ To add it: /add <term>
→ To search broadly: /lookup <term>
```
