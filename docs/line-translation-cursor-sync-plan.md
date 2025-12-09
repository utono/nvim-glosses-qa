# Line Translation Cursor Sync Plan

Integrate `/line-by-line` translations with nvim-xc so that translations
appear in a floating window as the cursor moves through Shakespeare dialogue.

## Problem Statement

Current state:
- `/line-by-line` generates translations stored at **chunk level** (42+ lines)
- nvim-xc syncs audio timestamps at **line level** via `line_timestamps` table
- No mechanism to display per-line translations on cursor movement

Desired state:
- As cursor moves to a dialogue line, its translation appears in a floating window
- Toggle on/off with keybind (hidden by default, shown when needed)
- Similar UX to how `line_timestamps` enables audio sync per line

## Architecture Overview

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
│  └─────────────────┘    │ NEW TABLE        │                   │
│                         └────────┬─────────┘                   │
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

## TODO List

### Phase 1: Database Schema

- [ ] Add `line_translations` table to gloss.db
- [ ] Create indexes for efficient queries
- [ ] Test schema with sample data

### Phase 2: Modify scene_analyzer.py

- [ ] Parse generated translations to extract line-level mappings
- [ ] Map original lines to their line numbers in source file
- [ ] Insert records into `line_translations` during `--save-chunk`
- [ ] Handle speaker attribution (character field)

### Phase 3: nvim-xc Integration

- [ ] Create `translation_display.lua` module in `~/utono/xc/nvim-mpv/lua/transcript_db/`
- [ ] Implement cache loading (all translations for file on open)
- [ ] Create floating window management (open/close/update)
- [ ] Add CursorMoved autocmd to update translation display
- [ ] Handle lines without translations gracefully (show nothing or "(no translation)")
- [ ] Add keybind to `~/.config/nvim-xc/lua/custom/keymaps.lua`

### Phase 4: Testing & Polish

- [ ] Test with Romeo and Juliet Act I, Scene I
- [ ] Test cursor movement performance
- [ ] Handle edge cases (no translation, stage directions)
- [ ] Document keybinds

---

## Detailed Implementation

### 1. Database Schema Change

**File**: Apply to `~/utono/literature/gloss.db`

```sql
CREATE TABLE line_translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,       -- normalized play file path
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

CREATE INDEX idx_line_trans_file
    ON line_translations(source_file);
CREATE INDEX idx_line_trans_lookup
    ON line_translations(source_file, line_number);
```

### 2. Modify scene_analyzer.py

**File**: `~/utono/nvim-glosses-qa/python/scene_analyzer.py`

Add function to parse Claude's output and extract line mappings:

```python
def parse_line_translations(chunk_text: str, generated_output: str) -> list:
    """
    Parse generated translation output to extract line-level mappings.

    Input format (from Claude):
        **"What country friends is this?"**

        What land is this, my friends?

        **"This is Illyria lady."**

        This is Illyria, my lady.

    Returns:
        List of (original_text, translation, character) tuples
    """
    # Pattern: **"original"** followed by blank line, then translation
    pattern = r'\*\*"([^"]+)"\*\*\s*\n\s*\n([^\n\*]+)'
    ...
```

Modify `save_chunk()` to also populate `line_translations`:

```python
def save_chunk(self, chunk_hash: str, analysis_text: str):
    # Existing: save to glosses table
    self._save_to_glosses(chunk_hash, analysis_text)

    # NEW: parse and save line-level translations
    line_mappings = parse_line_translations(
        self.chunks[chunk_hash].text,
        analysis_text
    )
    self._save_line_translations(line_mappings)
```

**Challenge**: Mapping original lines back to source file line numbers
- Need to track line_start/line_end from Speech/SpeechChunk objects
- Match parsed original_text to lines in chunk to get line numbers

### 3. nvim-xc Integration

**New file**: `~/utono/xc/nvim-mpv/lua/transcript_db/translation_display.lua`

```lua
local M = {}

local state = {
    enabled = false,
    win_id = nil,
    buf_id = nil,
    current_file = nil,
    cache = {},  -- cache[line_number] = {translation, character, original}
}

-- Load all translations for a file into cache
function M.load_cache(source_file)
    state.cache = {}
    state.current_file = source_file

    local query = string.format([[
        SELECT line_number, translation, character, original_text
        FROM line_translations
        WHERE source_file = '%s'
    ]], source_file)

    local results = database.execute_multi(query)
    for _, row in ipairs(results or {}) do
        state.cache[row.line_number] = {
            translation = row.translation,
            character = row.character,
            original = row.original_text,
        }
    end
end

-- Get translation from cache (fast, no DB query)
function M.get_translation(line_number)
    return state.cache[line_number]
end

-- Update the translation window with new content
function M.update_display(entry)
    if not state.enabled or not state.win_id then return end
    if not vim.api.nvim_win_is_valid(state.win_id) then return end

    local lines = {}

    if entry then
        -- Show translation with optional character attribution
        if entry.character then
            table.insert(lines, entry.character .. ":")
            table.insert(lines, "")
        end
        -- Show original line (dimmed/italic via highlight)
        table.insert(lines, entry.original or "")
        table.insert(lines, "")
        -- Show translation
        table.insert(lines, entry.translation or "")
    else
        -- No translation for this line - show minimal indicator
        table.insert(lines, "")
        table.insert(lines, "  (no translation)")
        table.insert(lines, "")
    end

    vim.api.nvim_buf_set_lines(state.buf_id, 0, -1, false, lines)
end

-- Open floating translation window
function M.open_window()
    -- Create buffer
    state.buf_id = vim.api.nvim_create_buf(false, true)
    vim.api.nvim_buf_set_option(state.buf_id, 'buftype', 'nofile')
    vim.api.nvim_buf_set_option(state.buf_id, 'filetype', 'markdown')
    vim.api.nvim_buf_set_option(state.buf_id, 'bufhidden', 'wipe')

    -- Floating window config (bottom-right corner)
    local width = 50
    local height = 6
    local opts = {
        relative = 'editor',
        width = width,
        height = height,
        row = vim.o.lines - height - 3,
        col = vim.o.columns - width - 2,
        style = 'minimal',
        border = 'rounded',
        title = ' Translation ',
        title_pos = 'center',
    }

    state.win_id = vim.api.nvim_open_win(state.buf_id, false, opts)
    vim.api.nvim_win_set_option(state.win_id, 'wrap', true)
    vim.api.nvim_win_set_option(state.win_id, 'linebreak', true)

    state.enabled = true

    -- Load cache for current file
    M.load_cache(vim.fn.expand('%:p'))

    -- Update display for current line
    M.on_cursor_moved()
end

-- Close translation window
function M.close_window()
    if state.win_id and vim.api.nvim_win_is_valid(state.win_id) then
        vim.api.nvim_win_close(state.win_id, true)
    end
    state.win_id = nil
    state.buf_id = nil
    state.enabled = false
end

-- Toggle translation window
function M.toggle()
    if state.enabled then
        M.close_window()
    else
        M.open_window()
    end
end

-- CursorMoved handler (uses cache, no DB query)
function M.on_cursor_moved()
    if not state.enabled then return end

    local file = vim.fn.expand('%:p')
    local line = vim.fn.line('.')

    -- Reload cache if file changed
    if file ~= state.current_file then
        M.load_cache(file)
    end

    local entry = M.get_translation(line)
    M.update_display(entry)  -- entry may be nil
end

-- Setup autocmd
function M.setup()
    vim.api.nvim_create_autocmd('CursorMoved', {
        pattern = '*.txt',
        callback = M.on_cursor_moved,
    })
end

return M
```

**Keybind**: Add to `~/.config/nvim-xc/lua/custom/keymaps.lua`

```lua
-- Toggle translation floating window
vim.keymap.set('n', '<M-t>', function()
    require('transcript_db.translation_display').toggle()
end, { desc = 'Toggle translation window' })
```

This keybind is in the user config (not the plugin) so it can be easily
customized and persists across plugin updates.

### 4. Line Number Mapping Strategy

The tricky part: matching original lines to source file line numbers.

**Approach A**: Store line numbers during chunk creation
- `SpeechChunk` already has `line_start`, `line_end` from `Speech` objects
- When parsing generated output, match lines sequentially within chunk range

**Approach B**: Fuzzy match at query time
- Store original_text in `line_translations`
- When querying, match current line text to original_text
- Less reliable but more flexible

**Recommended**: Approach A - track line numbers during generation

```python
# In scene_analyzer.py, SpeechChunk tracks line ranges
@dataclass
class SpeechChunk:
    speeches: list[Speech]

    @property
    def line_numbers(self) -> list[int]:
        """Get all line numbers in this chunk."""
        numbers = []
        for speech in self.speeches:
            for i in range(speech.line_start, speech.line_end + 1):
                numbers.append(i)
        return numbers
```

---

## File Modifications Summary

| File | Change |
|------|--------|
| `~/utono/literature/gloss.db` | Add `line_translations` table |
| `~/utono/nvim-glosses-qa/python/scene_analyzer.py` | Parse translations, populate new table |
| `~/utono/xc/nvim-mpv/lua/transcript_db/translation_display.lua` | NEW: query and display floating window |
| `~/.config/nvim-xc/lua/custom/keymaps.lua` | Add toggle keybind |
| `~/utono/xc/nvim-mpv/lua/transcript_db/init.lua` | Require new module |

## Design Decisions

1. **Window position**: Floating window (can be toggled on/off)
2. **Stage directions**: Skip - only translate spoken dialogue
3. **Caching**: Cache per file - load all translations on file open for fast
   cursor response
4. **Toggle keybind**: In `~/.config/nvim-xc` for easy access
5. **Partial coverage**: Not all lines will have translations until full play
   is glossed - floating window shows "(no translation)" or hides gracefully

## Testing Plan

1. Generate translations for Romeo and Juliet I.i
2. Verify `line_translations` table populated correctly
3. Open play file in nvim-xc
4. Toggle translation window
5. Move cursor through dialogue, verify translations update
6. Test edge cases: blank lines, stage directions, no translation
