# Passage Viewer

Sequential viewer for line-by-line analyses stored in the database.

## Overview

The passage viewer provides navigation through analyzed passages, ordered as
they appear in the play. It integrates with `~/.config/nvim-glosses` for
viewing passages and their Q&A pages.

## Workflow

1. **scene_analyzer.py** creates line-by-line analyses (the "glossing")
2. **~/.config/nvim-glosses** views passages and Q&A pages sequentially
3. **~/utono/xc/nvim** (`U` keybind) handles ad-hoc translations/Q&A if needed

## Keybinds

| Key | Action |
|-----|--------|
| `.` | Next passage in current play |
| `,` | Previous passage in current play |
| `Tab` | Toggle passage / Q&A pages |
| `<leader>gp` | Pick different play, then fuzzy search for passage |
| `<leader>gf` | Find any passage in any play (fuzzy search) |
| `<leader>gb` | Go back to previous play/position |

## Behavior

### Auto-Detection

On first `,` or `.` press, the viewer auto-detects the play from the current
buffer's associated passage (`play_name` field in database).

### Play Picker (`<leader>gp`)

1. Fuzzy list of all plays in database
2. User selects play
3. Opens fuzzy search for passages within that play
4. User selects passage - viewer jumps there
5. Previous position pushed to stack

### Global Search (`<leader>gf`)

1. Fuzzy search showing all passages from all plays
2. Display format: `[Play] Act.Scene - Character: "first few words..."`
3. User selects passage - viewer jumps there
4. Previous position pushed to stack

### Go Back (`<leader>gb`)

1. Pop most recent position from stack (max depth: 5)
2. Load that play's passages if different from current
3. Jump to saved index

## State Management

```lua
state = {
  current_play = "henry-v",
  passages = { ... },        -- ordered list for current play
  current_index = 47,        -- position in passages list
  viewing_qa = false,        -- Tab toggle state
  qa_page = 1,               -- which Q&A page if multiple
  stack = {                  -- max 5 positions
    { play = "henry-v", index = 47 },
  }
}
```

## Database Schema

The `passages` table includes a `play_name` field for fast queries:

```sql
-- Added column
ALTER TABLE passages ADD COLUMN play_name TEXT;
CREATE INDEX idx_passages_play_name ON passages(play_name);

-- Migration for existing data
UPDATE passages
SET play_name = REPLACE(REPLACE(source_file, '_gut.txt', ''), '_', '-')
WHERE play_name IS NULL;
```

## Query Functions

Located in `~/utono/nvim-glosses-qa/python/db_queries.py`:

- `get_plays()` - List all plays in database
- `get_passages_for_play(play_name)` - Ordered by act/scene/line_number
- `get_qa_for_passage(passage_id)` - Get addenda for a passage
- `search_passages(query, play_name=None)` - Fuzzy search

## File Locations

- **Viewer plugin**: `~/.config/nvim-glosses/lua/passage_viewer/init.lua`
- **Query module**: `~/utono/nvim-glosses-qa/python/db_queries.py`
- **Scene analyzer**: `~/utono/nvim-glosses-qa/python/scene_analyzer.py`

## Implementation Order

1. Schema: Add `play_name` column, migrate data
2. Update `scene_analyzer.py` to populate `play_name`
3. Create `db_queries.py` with query functions
4. Create Lua plugin in `~/.config/nvim-glosses`
5. Set up keybinds
