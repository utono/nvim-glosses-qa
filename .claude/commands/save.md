Save your most recent reply to the gloss database.

**Step 1: Get the gloss hash**
```bash
echo $GLOSS_HASH
```

**Step 2: Save the reply**

Take your most recent reply (the message immediately before the user typed /save) and save it to the addenda table. This could be:
- A summary from /summarize
- A "discuss" analysis
- Any other substantive reply worth preserving

```bash
sqlite3 ~/utono/literature/gloss.db "INSERT INTO addenda (gloss_hash, question, answer) VALUES ('<hash>', '<brief_topic>', '<escaped_reply>');"
```

**Important:**
1. Escape single quotes in the reply by doubling them ('')
2. Use the actual GLOSS_HASH value from the environment variable
3. For the 'question' field, use a brief topic descriptor:
   - "Q&A Session" for general discussion summaries
   - "Discuss: <word>" for word analysis (e.g., "Discuss: ceremony")
   - Or a short phrase describing the topic
4. **Remove soft line breaks**: Before saving, join lines that are just wrapped for display. Only preserve blank lines as paragraph separators. For example:
   - `"This is a long\nsentence that wraps"` → `"This is a long sentence that wraps"`
   - But keep: `"Paragraph one.\n\nParagraph two."` (blank line = intentional break)

**Step 3: Verify the save**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT id, datetime(timestamp, 'localtime') FROM addenda WHERE gloss_hash = '$GLOSS_HASH' ORDER BY timestamp DESC LIMIT 1"
```

Confirm success: "Saved to addenda (ID: [id], [timestamp])"
