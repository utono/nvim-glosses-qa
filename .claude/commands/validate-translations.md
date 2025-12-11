Validate line translations against source file content.

Detects orphaned DB entries where `original_text` no longer matches the actual file line (e.g., after manual edits to the source file).

Arguments: $ARGUMENTS

**Usage:**
```
/validate-translations <play_file>           # Report mismatches only
/validate-translations --fix <play_file>     # Delete orphaned entries
```

**Examples:**
```
/validate-translations troilus_and_cressida_gut.txt
/validate-translations --fix twelfth_night_gut.txt
```

**Execution:**

1. Parse arguments to determine if `--fix` flag is present and extract the play file path.

2. Resolve the play file path. Check these locations in order:
   - If absolute path provided, use it directly
   - `~/utono/literature/shakespeare-william/gutenberg/<filename>`
   - Current working directory

3. Run the validation command:
```bash
python python/scene_analyzer.py --validate-translations [--fix] <resolved_path>
```

4. Report the results to the user:
   - If mismatches found without `--fix`: list them and suggest running with `--fix`
   - If mismatches found with `--fix`: confirm deletions
   - If no mismatches: confirm all translations are valid

**Error handling:**
- If no play file argument provided, show usage
- If file not found, list available play files with translations:
```bash
sqlite3 ~/utono/literature/gloss.db "SELECT DISTINCT source_file FROM line_translations"
```
