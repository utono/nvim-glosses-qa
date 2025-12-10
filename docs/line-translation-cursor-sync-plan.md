# Line Translation Cursor Sync

**Status: IMPLEMENTED** (2024-12-09)

Integrate `/line-by-line` translations with nvim-xc so that translations
appear in a floating window as the cursor moves through Shakespeare dialogue.

## Usage

1. Open a play file in nvim-xc
2. Press `<M-g>` (Alt+g) to toggle the translation floating window
3. Move cursor through dialogue lines to see translations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  /line-by-line command                                          │
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │ scene_analyzer  │───▶│ glosses table    │ (chunk-level md)  │
│  │ .py             │    │ gloss_type=      │                   │
│  │                 │    │ 'line-by-line'   │                   │
│  │                 │    └──────────────────┘                   │
│  │                 │    ┌──────────────────┐                   │
│  │                 │───▶│ line_translations│ (line-level)      │
│  └─────────────────┘    └────────┬─────────┘                   │
└──────────────────────────────────┼─────────────────────────────┘
                                   │
┌──────────────────────────────────┼─────────────────────────────┐
│  nvim-xc                         │                              │
│                                  ▼                              │
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │ CursorMoved     │───▶│ query            │                   │
│  │ autocmd         │    │ line_translations│                   │
│  └─────────────────┘    └────────┬─────────┘                   │
│                                  │                              │
│                                  ▼                              │
│                         ┌──────────────────┐                   │
│                         │ translation      │                   │
│                         │ floating window  │                   │
│                         └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

## Files Modified

| File | Change |
|------|--------|
| `~/utono/literature/gloss.db` | Added `line_translations` table |
| `~/utono/nvim-glosses-qa/python/scene_analyzer.py` | Parse and save line-level translations |
| `~/utono/xc/nvim-mpv/lua/transcript_db/translation_display.lua` | Floating window display module |
| `~/.config/nvim-xc/lua/custom/keymaps.lua` | `<M-g>` toggle keybind |

## Database Schema

```sql
CREATE TABLE line_translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,       -- full path to play file
    line_number INTEGER NOT NULL,    -- 1-indexed line in source file
    original_text TEXT NOT NULL,     -- original Shakespeare line
    translation TEXT NOT NULL,       -- modern English translation
    character TEXT,                  -- speaker (VIOLA, CAPTAIN, etc.)
    play_name TEXT,
    act TEXT,
    scene TEXT,
    chunk_hash TEXT,                 -- link back to glosses chunk
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_file, line_number)
);

CREATE INDEX idx_line_trans_file ON line_translations(source_file);
CREATE INDEX idx_line_trans_lookup ON line_translations(source_file, line_number);
```

## Design Decisions

1. **Window position**: Floating window in bottom-right corner
2. **Toggle keybind**: `<M-g>` (Alt+g) for "gloss"
3. **Stage directions**: Excluded from translations
4. **Caching**: All translations for a file loaded on toggle, no per-line
   DB queries
5. **Partial coverage**: Lines without translations show "(no translation)"

## Current Data

- 145 line translations
- Henry V: 86 lines
- Twelfth Night: 59 lines

Query translations:
```bash
sqlite3 -header -column ~/utono/literature/gloss.db \
  "SELECT line_number, character, original_text, translation
   FROM line_translations ORDER BY source_file, line_number"
```
