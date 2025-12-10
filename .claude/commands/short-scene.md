Find the shortest scene(s) in a Shakespeare play file.

**Arguments: $ARGUMENTS**

Parse the arguments to extract:
`<play_file> [--top N] [--all] [--by-dialogue]`

## Usage

```
/short-scene twelfth_night_gut.txt
/short-scene /home/mlj/utono/literature/shakespeare-william/gutenberg/hamlet_gut.txt
/short-scene henry_v_gut.txt --top 5
/short-scene macbeth_gut.txt --all
/short-scene romeo_and_juliet_gut.txt --by-dialogue
```

## What This Does

1. **Parses the play file** to locate all ACT/SCENE markers
2. **Calculates line counts** for each scene (total and dialogue lines)
3. **Counts speeches** in each scene
4. **Reports shortest scenes** ordered by length

## Options

- `--top N` or `-t N`: Show top N shortest scenes (default: 3)
- `--all` or `-a`: Show all scenes sorted by length
- `--by-dialogue` or `-d`: Sort by dialogue lines instead of total lines

## Output

Shows a table of scenes sorted by line count:
```
Scene                     Lines      Dialogue   Speeches
------------------------------------------------------------
Act 4, Scene 3            55         38         4
  ^ SHORTEST
Act 2, Scene 2            58         40         6
Act 1, Scene 1            66         44         7
```

## Execution

Run the find_short_scene.py script:

```bash
python ~/utono/nvim-glosses-qa/python/find_short_scene.py <play_file> [options]
```

## Play File Locations

If only a filename is given (not a full path), resolve it to:
`~/utono/literature/shakespeare-william/gutenberg/<filename>`

Common files:
- `twelfth_night_gut.txt` - Twelfth Night
- `henry_v_gut.txt` - Henry V
- `hamlet_gut.txt` - Hamlet
- `macbeth_gut.txt` - Macbeth
- `romeo_and_juliet_gut.txt` - Romeo and Juliet
- `midsummer_gut.txt` - A Midsummer Night's Dream
- `othello_gut.txt` - Othello
- `king_lear_gut.txt` - King Lear

## Example Session

User: `/short-scene twelfth_night_gut.txt`

1. Parse arguments: play=twelfth_night_gut.txt
2. Resolve full path: ~/utono/literature/shakespeare-william/gutenberg/twelfth_night_gut.txt
3. Run: `python ~/utono/nvim-glosses-qa/python/find_short_scene.py <full_path>`
4. Report the shortest scene(s)

## Use Case

This command helps actors find short scenes for:
- Quick rehearsal sessions
- Audition preparation
- Scene study exercises
- Memorization practice

The shortest scenes make ideal starting points for intensive text work.
