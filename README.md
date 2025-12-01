# nvim-glosses-qa

Claude Code configuration for Shakespeare Q&A sessions.

This directory provides the CLAUDE.md and slash commands used when `<M-c>` is pressed in nvim-glosses to ask questions about a Shakespeare passage.

## Usage

This is not meant to be used directly. It's invoked by nvim-glosses via the `ask-claude.sh` script when you press `<M-c>` while viewing a gloss.

## Features

- Database-informed context from `~/utono/literature/gloss.db`
- Elizabethan term matching and proposals
- Prior Q&A session retrieval
- Cross-referencing related glosses

## Slash Commands

| Command | Description |
|---------|-------------|
| `/reset` | Re-display database context (use after /clear) |
| `/context` | Show all available context from database |
| `/lookup <word>` | Search database for a specific word |
| `/done` | Generate summary for saving |
| `/save` | Save summary to addenda table |
| `/add <terms>` | Add Elizabethan resonance terms |
| `/remove <terms>` | Remove terms from database |

## Related

- [nvim-glosses](https://github.com/utono/nvim-glosses) - The main plugin
- Database: `~/utono/literature/gloss.db`
