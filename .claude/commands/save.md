Save the summary from the previous /done command to the gloss database.

**Step 1: Get the gloss hash**
```bash
echo $GLOSS_HASH
```

**Step 2: Save the summary**

Take the summary you generated from the /done command and save it to the addenda table.

```bash
sqlite3 ~/utono/literature/gloss.db "INSERT INTO addenda (gloss_hash, question, answer) VALUES ('<hash>', 'Q&A Session', '<escaped_summary>');"
```

**Important:**
1. Escape single quotes in the summary by doubling them ('')
2. Use the actual GLOSS_HASH value from the environment variable
3. The 'question' field should be 'Q&A Session' to indicate this came from an interactive session

**Step 3: Verify the save**
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT id, datetime(timestamp, 'localtime') FROM addenda WHERE gloss_hash = '$GLOSS_HASH' ORDER BY timestamp DESC LIMIT 1"
```

Confirm success: "Summary saved to addenda (ID: [id], [timestamp])"

If there was no previous /done summary in this conversation, tell the user: "No summary found. Run /done first to generate a summary."
