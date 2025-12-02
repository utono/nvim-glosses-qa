Clear conversation history and provide a summary of the loaded context.

First, run the built-in /clear command to reset conversation history.

Then provide a context summary showing what you have available. Include:

1. **The passage** - Brief description (play, act, scene, what it's about)

2. **Your translation** - Mention you have the user's translation

3. **Wordplay/notes** - If the system prompt mentions wordplay or special notes

4. **Catalogued terms** - List terms from CATALOGUED TERMS in system prompt
   that appear in this passage (e.g., "ceremony" is in your catalogue)

5. **Prior discussions** - Count from system prompt (PRIOR DISCUSSIONS: n saved)

6. **Related glosses** - Count from system prompt (RELATED: n by character, n in scene)

Format your response like this example:

```
I have King Henry V's soliloquy from Act IV, the night before
Agincourt. It begins with wordplay on "French crowns" (coins/heads)
and moves into his meditation on the burdens of kingship.

The passage runs from the crowns/clipper jest through Henry's
bitter comparison: ceremony gives kings nothing the "wretched
slave" doesn't have — indeed, the laborer sleeps better, works
honestly, and "had the fore-hand and vantage of a king" were it
not for empty ceremony.

I also have:
- Your translation of this passage
- The WORDPLAY note on lines 1-4 (crowns/clipper pun)
- Glossary of 15 Elizabethan terms (balm, Elysium, Hyperion, etc.)
- Note that "ceremony" is already in your catalogue
- 3 prior discussions saved, 4 related glosses by Henry

What would you like to explore?
```

This gives the user a clear picture of what context is available without
requiring them to re-read everything.
