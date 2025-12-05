#!/usr/bin/env python3
"""Scene-level line-by-line analysis generator.

Processes an entire scene by speech, generating line-by-line actor analysis
for each speech unit, caching results in the database, and producing a
unified markdown file per scene.

Usage:
    python scene_analyzer.py <play_file> <act> <scene> [--output-dir DIR]
    python scene_analyzer.py henry_v_gut.txt 4 7

Environment:
    ANTHROPIC_API_KEY: Required for API backend
    GLOSS_BACKEND: 'api' or 'claude-code' (default: claude-code)
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add xc/nvim/python to path for gloss module imports
XC_PYTHON_DIR = Path.home() / "utono" / "xc" / "nvim" / "python"
sys.path.insert(0, str(XC_PYTHON_DIR))

from hash_utils import generate_hash
from gloss import (
    GlossDatabase,
    PromptBuilder,
    create_backend,
    setup_logging,
    preprocess_text,
)
from gloss.config import GLOSSES_DIR, DEFAULT_BACKEND

logger = setup_logging()


@dataclass
class Speech:
    """A single character's continuous speech."""
    speaker: str
    lines: list[str]
    text: str  # Full text including speaker name
    line_start: int  # Line number in source file
    line_end: int

    # Pattern for stage directions
    STAGE_DIR_RE = re.compile(r'^\[.*\]\s*$')

    @property
    def hash(self) -> str:
        """Generate hash for this speech."""
        return generate_hash(self.text)

    @property
    def line_count(self) -> int:
        """Number of dialogue lines (excluding speaker name)."""
        return len(self.lines)

    @property
    def has_dialogue(self) -> bool:
        """Check if speech contains actual dialogue (not just stage directions)."""
        for line in self.lines:
            stripped = line.strip()
            # Skip empty lines and stage directions
            if not stripped:
                continue
            if self.STAGE_DIR_RE.match(stripped):
                continue
            # Found actual dialogue
            return True
        return False


@dataclass
class SpeechChunk:
    """A group of consecutive speeches processed together."""
    speeches: list[Speech]
    text: str  # Combined text of all speeches

    @property
    def hash(self) -> str:
        """Generate hash for the combined chunk."""
        return generate_hash(self.text)

    @property
    def line_count(self) -> int:
        """Total lines across all speeches."""
        return sum(s.line_count for s in self.speeches)

    @property
    def speaker_summary(self) -> str:
        """Summary of speakers in this chunk."""
        speakers = [s.speaker for s in self.speeches]
        if len(speakers) == 1:
            return speakers[0]
        return f"{speakers[0]}...{speakers[-1]} ({len(speakers)} speeches)"


class PlayParser:
    """Parse a play file to extract scenes and speeches."""

    # Patterns for play structure
    # ACT pattern matches Roman numerals (ACT IV.), Arabic (ACT 1.), and words (ACT FIRST.)
    ACT_PATTERN = re.compile(
        r'^ACT\s+([IVX]+|\d+|FIRST|SECOND|THIRD|FOURTH|FIFTH)\.?\s*$',
        re.IGNORECASE
    )
    # SCENE pattern matches both Roman (SCENE I.) and Arabic (SCENE 1.)
    SCENE_PATTERN = re.compile(r'^SCENE\s+([IVX]+|\d+)[\.\s:](.*)$', re.IGNORECASE)
    # Combined ACT + SCENE on same line (e.g., "ACT IV. SCENE I. Location.")
    ACT_SCENE_COMBINED_PATTERN = re.compile(
        r'^ACT\s+([IVX]+|\d+|FIRST|SECOND|THIRD|FOURTH|FIFTH)\.?\s*SCENE\s+([IVX]+|\d+)[\.\s:](.*)$',
        re.IGNORECASE
    )
    PROLOGUE_PATTERN = re.compile(r'^PROLOGUE\.?\s*$', re.IGNORECASE)
    EPILOGUE_PATTERN = re.compile(r'^EPILOGUE\.?\s*$', re.IGNORECASE)
    SPEAKER_PATTERN = re.compile(r'^([A-Z][A-Z\s]+)\.\s*$')
    STAGE_DIR_PATTERN = re.compile(r'^\[.*\]\s*$')

    # Ordinal words to integers
    ORDINAL_TO_INT = {
        'FIRST': 1, 'SECOND': 2, 'THIRD': 3, 'FOURTH': 4, 'FIFTH': 5
    }

    def __init__(self, play_file: Path):
        """Initialize parser with play file.

        Args:
            play_file: Path to the play text file.
        """
        self.play_file = Path(play_file)
        self.lines: list[str] = []
        self._load_file()

    def _load_file(self) -> None:
        """Load play file into memory."""
        with open(self.play_file, 'r', encoding='utf-8') as f:
            self.lines = f.readlines()

    def _roman_to_int(self, roman: str) -> int:
        """Convert Roman numeral to integer."""
        values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
        result = 0
        prev = 0
        for char in reversed(roman.upper()):
            curr = values.get(char, 0)
            if curr < prev:
                result -= curr
            else:
                result += curr
            prev = curr
        return result

    def _int_to_roman(self, num: int) -> str:
        """Convert integer to Roman numeral."""
        val = [10, 9, 5, 4, 1]
        syms = ['X', 'IX', 'V', 'IV', 'I']
        result = ''
        for i, v in enumerate(val):
            while num >= v:
                result += syms[i]
                num -= v
        return result

    def _normalize_act(self, act_str: str) -> int:
        """Normalize act string (Roman numeral, Arabic numeral, or ordinal word) to integer.

        Args:
            act_str: Act identifier like 'III', '3', 'FIRST', 'IV', etc.

        Returns:
            Integer act number.
        """
        act_upper = act_str.upper().strip()
        if act_upper in self.ORDINAL_TO_INT:
            return self.ORDINAL_TO_INT[act_upper]
        # Try Arabic numeral first
        if act_upper.isdigit():
            return int(act_upper)
        return self._roman_to_int(act_upper)

    def _normalize_scene(self, scene_str: str) -> int:
        """Normalize scene string (Roman or Arabic numeral) to integer.

        Args:
            scene_str: Scene identifier like 'III', '3', 'IV', etc.

        Returns:
            Integer scene number.
        """
        scene_str = scene_str.strip()
        if scene_str.isdigit():
            return int(scene_str)
        return self._roman_to_int(scene_str)

    def find_scene(self, act: int, scene: int) -> tuple[int, int]:
        """Find the start and end line numbers for a scene.

        Args:
            act: Act number (integer), or 0 for opening prologue
            scene: Scene number (integer), or 0 for prologue

        Returns:
            Tuple of (start_line, end_line) as 0-indexed line numbers.

        Raises:
            ValueError: If scene not found.
        """
        # Handle prologue (scene=0) and epilogue (scene=-1)
        if scene == 0:
            return self._find_prologue(act)
        if scene == -1:
            return self._find_epilogue()

        # Use integer comparison for flexibility with different formats
        target_act = act
        target_scene = scene

        current_act = None
        scene_start = None
        scene_end = None

        for i, line in enumerate(self.lines):
            stripped = line.strip()

            # Check for combined ACT + SCENE on same line (e.g., "ACT IV. SCENE I.")
            combined_match = self.ACT_SCENE_COMBINED_PATTERN.match(stripped)
            if combined_match:
                line_act = self._normalize_act(combined_match.group(1))
                line_scene = self._normalize_scene(combined_match.group(2))

                # If we already found our scene, this marks the end
                if scene_start is not None:
                    scene_end = i - 1
                    break

                # Update current act and check if this is our target
                current_act = line_act
                if line_act == target_act and line_scene == target_scene:
                    scene_start = i
                continue

            # Check for act header (standalone)
            act_match = self.ACT_PATTERN.match(stripped)
            if act_match:
                # Normalize to integer (handles both Roman and ordinal words)
                current_act = self._normalize_act(act_match.group(1))
                continue

            # Check for scene header (standalone)
            scene_match = self.SCENE_PATTERN.match(stripped)
            if scene_match:
                scene_num = self._normalize_scene(scene_match.group(1))

                # If we already found our scene, this marks the end
                if scene_start is not None:
                    scene_end = i - 1
                    break

                # Check if this is our target scene (integer comparison)
                if current_act == target_act and scene_num == target_scene:
                    scene_start = i

        # If scene_end not set, scene goes to end of file
        if scene_start is not None and scene_end is None:
            scene_end = len(self.lines) - 1

        if scene_start is None:
            raise ValueError(
                f"Scene {act}.{scene} (Act {self._int_to_roman(act)}, "
                f"Scene {self._int_to_roman(scene)}) not found in {self.play_file}"
            )

        return scene_start, scene_end

    def _find_prologue(self, act: int) -> tuple[int, int]:
        """Find the prologue for a specific act.

        Args:
            act: Act number (1-5), or 0 for opening prologue before Act 1

        Returns:
            Tuple of (start_line, end_line) as 0-indexed line numbers.

        Raises:
            ValueError: If prologue not found.
        """
        current_act = 0  # 0 = before any act header (opening prologue)
        prologue_start = None
        prologue_end = None

        for i, line in enumerate(self.lines):
            stripped = line.strip()

            # Check for act header
            act_match = self.ACT_PATTERN.match(stripped)
            if act_match:
                current_act = self._normalize_act(act_match.group(1))
                continue

            # Check for prologue header
            if self.PROLOGUE_PATTERN.match(stripped):
                # If we already found our prologue, this marks the end
                if prologue_start is not None:
                    prologue_end = i - 1
                    break

                # Check if this is our target prologue
                # act=0 means opening prologue (before any ACT marker)
                # act=N means the prologue right after ACT N header
                if current_act == act:
                    prologue_start = i

            # Scene header also ends the prologue
            scene_match = self.SCENE_PATTERN.match(stripped)
            if scene_match and prologue_start is not None:
                prologue_end = i - 1
                break

        # If prologue_end not set, prologue goes to next major marker
        if prologue_start is not None and prologue_end is None:
            prologue_end = len(self.lines) - 1

        if prologue_start is None:
            if act == 0:
                raise ValueError(f"Opening prologue not found in {self.play_file}")
            raise ValueError(
                f"Prologue for Act {self._int_to_roman(act)} not found in "
                f"{self.play_file}"
            )

        return prologue_start, prologue_end

    def _find_epilogue(self) -> tuple[int, int]:
        """Find the epilogue section.

        Returns:
            Tuple of (start_line, end_line) as 0-indexed line numbers.

        Raises:
            ValueError: If epilogue not found.
        """
        epilogue_start = None

        for i, line in enumerate(self.lines):
            if self.EPILOGUE_PATTERN.match(line.strip()):
                epilogue_start = i
                break

        if epilogue_start is None:
            raise ValueError(f"Epilogue not found in {self.play_file}")

        # Epilogue goes to end of file
        return epilogue_start, len(self.lines) - 1

    def extract_speeches(self, start_line: int, end_line: int) -> list[Speech]:
        """Extract individual speeches from a line range.

        Args:
            start_line: Starting line number (0-indexed)
            end_line: Ending line number (0-indexed)

        Returns:
            List of Speech objects.
        """
        speeches = []
        current_speaker = None
        current_lines = []
        speech_start = None

        for i in range(start_line, end_line + 1):
            line = self.lines[i].rstrip()

            # Check for new speaker first (before handling empty lines)
            speaker_match = self.SPEAKER_PATTERN.match(line.strip()) if line.strip() else None

            # Handle empty lines - preserve them within speeches for proper formatting
            if not line.strip():
                # Only add empty line if we're inside a speech
                if current_speaker and current_lines:
                    current_lines.append('')
                continue

            # Check for pure stage directions (lines that are only [bracketed text])
            # Include them in speech text for display, but they won't be analyzed line-by-line
            is_stage_direction = self.STAGE_DIR_PATTERN.match(line.strip())

            if speaker_match:
                # Save previous speech if exists
                if current_speaker and current_lines:
                    speech_text = f"{current_speaker}.\n" + "\n".join(current_lines)
                    speeches.append(Speech(
                        speaker=current_speaker,
                        lines=current_lines,
                        text=speech_text,
                        line_start=speech_start,
                        line_end=i - 1
                    ))

                # Start new speech
                current_speaker = speaker_match.group(1).strip()
                current_lines = []
                speech_start = i
                continue

            # Add line to current speech (if we have a speaker)
            if current_speaker:
                current_lines.append(line)

        # Don't forget the last speech
        if current_speaker and current_lines:
            speech_text = f"{current_speaker}.\n" + "\n".join(current_lines)
            speeches.append(Speech(
                speaker=current_speaker,
                lines=current_lines,
                text=speech_text,
                line_start=speech_start,
                line_end=end_line
            ))

        # Filter out speeches with no actual dialogue (only stage directions)
        speeches = [s for s in speeches if s.has_dialogue]

        return speeches


class SceneAnalyzer:
    """Analyze an entire scene speech by speech."""

    def __init__(self, play_file: Path, act: int, scene: int,
                 backend: str = None, output_dir: Path = None,
                 merge_threshold: int = 0):
        """Initialize scene analyzer.

        Args:
            play_file: Path to play text file.
            act: Act number (integer).
            scene: Scene number (integer).
            backend: 'api' or 'claude-code'.
            output_dir: Directory for output files. Defaults to GLOSSES_DIR.
            merge_threshold: Minimum lines per chunk. Speeches are merged until
                           this threshold is reached. 0 = no merging.
        """
        self.play_file = Path(play_file)
        self.act = act
        self.scene = scene
        self.backend = create_backend(backend)
        self.backend_type = backend or os.getenv('GLOSS_BACKEND', DEFAULT_BACKEND)
        self.output_dir = output_dir or GLOSSES_DIR
        self.merge_threshold = merge_threshold
        self.db = GlossDatabase()
        self.db.setup()  # Ensure tables exist

        # Parse play
        self.parser = PlayParser(play_file)

        # Extract play name from filename
        self.play_name = self.play_file.stem.replace('_gut', '').replace('_', '-')

    def _merge_speeches_into_chunks(self, speeches: list[Speech]) -> list[SpeechChunk]:
        """Merge consecutive small speeches into larger chunks.

        Speeches are never split - each speech stays intact. Chunks are closed
        when adding the next speech would exceed the threshold, ensuring a
        character's dialogue is always analyzed as a complete unit.

        Args:
            speeches: List of individual Speech objects.

        Returns:
            List of SpeechChunk objects.
        """
        if self.merge_threshold <= 0:
            # No merging - each speech becomes its own chunk
            return [
                SpeechChunk(speeches=[s], text=s.text)
                for s in speeches
            ]

        chunks = []
        current_speeches = []
        current_lines = 0

        for speech in speeches:
            # Check if adding this speech would exceed threshold
            # (but always include at least one speech per chunk)
            if current_speeches and current_lines + speech.line_count > self.merge_threshold:
                # Close current chunk before adding this speech
                combined_text = "\n\n".join(s.text.rstrip() for s in current_speeches)
                chunks.append(SpeechChunk(
                    speeches=current_speeches,
                    text=combined_text
                ))
                current_speeches = []
                current_lines = 0

            # Add speech to current chunk
            current_speeches.append(speech)
            current_lines += speech.line_count

        # Don't forget remaining speeches
        if current_speeches:
            combined_text = "\n\n".join(s.text.rstrip() for s in current_speeches)
            chunks.append(SpeechChunk(
                speeches=current_speeches,
                text=combined_text
            ))

        return chunks

    def _get_metadata(self, speech: Speech) -> dict:
        """Build metadata dict for a speech."""
        return {
            'source_file': str(self.play_file.name),
            'tag': f"{self.play_name}_act{self.act}_scene{self.scene}",
            'line_number': speech.line_start,
            'char_position': 0,
            'character': speech.speaker,
            'act': str(self.act),
            'scene': str(self.scene),
            'play_name': self.play_name,
        }

    def _analyze_speech(self, speech: Speech) -> str:
        """Generate line-by-line analysis for a single speech.

        Args:
            speech: The Speech object to analyze.

        Returns:
            The analysis text.
        """
        # Check cache first
        existing = self.db.get_existing(speech.hash, 'line-by-line')
        if existing:
            logger.info(f"  Cache hit for {speech.speaker} ({speech.line_count} lines)")
            return existing['text']

        logger.info(f"  Generating analysis for {speech.speaker} "
                   f"({speech.line_count} lines)...")

        # Build prompt and generate
        prompt_builder = PromptBuilder(speech.text)
        prompt = prompt_builder.build_line_by_line_prompt()
        raw_analysis = self.backend.generate(prompt)

        # Prepend speaker name only if not already present in the analysis
        speaker_prefix = f"{speech.speaker.upper()}."
        if raw_analysis.lstrip().startswith(speaker_prefix):
            analysis = raw_analysis
        else:
            analysis = f"{speaker_prefix}\n\n{raw_analysis}"

        # Save to database
        metadata = self._get_metadata(speech)

        passage_id = self.db.get_or_create_passage(
            speech.hash, speech.text, metadata
        )

        # Save as gloss type 'line-by-line'
        filename = f"{speech.hash[:8]}_{speech.speaker.lower()}_line-by-line.md"
        self.db.save(
            speech.hash, speech.text, analysis, filename,
            'line-by-line', metadata
        )

        # Also save to addenda for the full analysis
        self.db.save_addendum(speech.hash, "Line-by-line analysis", analysis)

        return analysis

    def _analyze_chunk(self, chunk: SpeechChunk) -> str:
        """Generate line-by-line analysis for a chunk of speeches.

        Args:
            chunk: The SpeechChunk object to analyze.

        Returns:
            The analysis text.
        """
        # Check cache first using chunk hash
        existing = self.db.get_existing(chunk.hash, 'line-by-line')
        if existing:
            logger.info(f"  Cache hit for chunk: {chunk.speaker_summary} "
                       f"({chunk.line_count} lines)")
            return existing['text']

        logger.info(f"  Generating analysis for chunk: {chunk.speaker_summary} "
                   f"({chunk.line_count} lines)...")

        # Build prompt and generate
        prompt_builder = PromptBuilder(chunk.text)
        prompt = prompt_builder.build_line_by_line_prompt()
        raw_analysis = self.backend.generate(prompt)

        # For single-speech chunks, prepend the speaker name only if not present
        # For multi-speech chunks, the raw analysis handles speaker names
        # since the input text includes them before each speech
        if len(chunk.speeches) == 1:
            speaker_prefix = f"{chunk.speeches[0].speaker.upper()}."
            if raw_analysis.lstrip().startswith(speaker_prefix):
                analysis = raw_analysis
            else:
                analysis = f"{speaker_prefix}\n\n{raw_analysis}"
        else:
            analysis = raw_analysis

        # Save to database using first speech's metadata
        first_speech = chunk.speeches[0]
        metadata = self._get_metadata(first_speech)
        metadata['character'] = chunk.speaker_summary

        self.db.get_or_create_passage(chunk.hash, chunk.text, metadata)

        # Save as gloss type 'line-by-line'
        filename = f"{chunk.hash[:8]}_chunk_line-by-line.md"
        self.db.save(
            chunk.hash, chunk.text, analysis, filename,
            'line-by-line', metadata
        )

        # Also save to addenda
        self.db.save_addendum(chunk.hash, "Line-by-line analysis", analysis)

        return analysis

    def _clean_analysis(self, analysis: str) -> str:
        """Remove trailing separators from analysis text.

        Args:
            analysis: Raw analysis text from Claude.

        Returns:
            Cleaned analysis without trailing '---' separators.
        """
        cleaned = analysis.rstrip()
        while cleaned.endswith('---'):
            cleaned = cleaned[:-3].rstrip()
        return cleaned

    def _format_scene_document(self, chunks: list[SpeechChunk],
                                analyses: list[str],
                                scene_header: str) -> str:
        """Format the complete scene analysis as markdown.

        Args:
            chunks: List of SpeechChunk objects.
            analyses: List of analysis strings (parallel to chunks).
            scene_header: The scene header line from the source.

        Returns:
            Formatted markdown document.
        """
        lines = []

        # Header
        lines.append(f"# {self.play_name.replace('-', ' ').title()}")
        lines.append(f"## Act {self.act}, Scene {self.scene}")
        lines.append("")
        lines.append(f"*{scene_header.strip()}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Each chunk with analysis
        speech_num = 1
        for chunk, analysis in zip(chunks, analyses):
            # If single-speech chunk, use simple format
            if len(chunk.speeches) == 1:
                speech = chunk.speeches[0]
                anchor = f"speech-{speech_num}"
                lines.append(f"<a name=\"{anchor}\"></a>")
                lines.append(f"### {speech_num}. {speech.speaker}")
                lines.append("")
                lines.append("#### Original Text")
                lines.append("```")
                lines.append(speech.text)
                lines.append("```")
                lines.append("")
                lines.append("#### Line-by-Line Analysis")
                lines.append("")
                lines.append(self._clean_analysis(analysis))
                lines.append("")
                lines.append("---")
                lines.append("")
                speech_num += 1
            else:
                # Multi-speech chunk
                lines.append(f"### Speeches {speech_num}-"
                            f"{speech_num + len(chunk.speeches) - 1}")
                lines.append("")
                lines.append("#### Original Text")
                lines.append("```")
                for speech in chunk.speeches:
                    anchor = f"speech-{speech_num}"
                    lines.append(f"<!-- {anchor} -->")
                    lines.append(speech.text)
                    lines.append("")
                    speech_num += 1
                lines.append("```")
                lines.append("")
                lines.append("#### Line-by-Line Analysis")
                lines.append("")
                lines.append(self._clean_analysis(analysis))
                lines.append("")
                lines.append("---")
                lines.append("")

        # Footer
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append(f"*Source: {self.play_file.name}*")

        return "\n".join(lines)

    def analyze(self, dry_run: bool = False) -> Path:
        """Analyze the entire scene.

        Args:
            dry_run: If True, just show what would be processed without
                    calling the API.

        Returns:
            Path to the generated markdown file.
        """
        # Log what we're analyzing (handle prologues/epilogue specially)
        if self.scene == -1:
            logger.info(f"Analyzing {self.play_name} Epilogue...")
        elif self.scene == 0:
            if self.act == 0:
                logger.info(f"Analyzing {self.play_name} Prologue...")
            else:
                logger.info(f"Analyzing {self.play_name} Act {self.act} Prologue...")
        else:
            logger.info(f"Analyzing {self.play_name} Act {self.act}, "
                       f"Scene {self.scene}...")

        # Find scene boundaries
        start_line, end_line = self.parser.find_scene(self.act, self.scene)
        scene_header = self.parser.lines[start_line].strip()
        logger.info(f"Found scene at lines {start_line}-{end_line}: {scene_header}")

        # Extract speeches
        speeches = self.parser.extract_speeches(start_line, end_line)
        logger.info(f"Found {len(speeches)} speeches")

        # Skip if no dialogue found (only stage directions)
        if not speeches:
            logger.info("No dialogue found in this section, skipping")
            if dry_run:
                print(f"\nSkipping: No dialogue found (only stage directions)")
            return None

        # Merge into chunks if threshold is set
        chunks = self._merge_speeches_into_chunks(speeches)
        if self.merge_threshold > 0:
            logger.info(f"Merged into {len(chunks)} chunks "
                       f"(threshold: {self.merge_threshold} lines)")

        if dry_run:
            if self.scene == -1:
                print(f"\nDry run: {self.play_name} Epilogue")
            elif self.scene == 0:
                if self.act == 0:
                    print(f"\nDry run: {self.play_name} Prologue")
                else:
                    print(f"\nDry run: {self.play_name} Act {self.act} Prologue")
            else:
                print(f"\nDry run: {self.play_name} Act {self.act}, Scene {self.scene}")
            print(f"Scene location: lines {start_line}-{end_line}")
            print(f"Total speeches: {len(speeches)}")
            if self.merge_threshold > 0:
                print(f"Merge threshold: {self.merge_threshold} lines")
                print(f"Chunks after merging: {len(chunks)}")
                print("\nChunks to process:")
                for i, chunk in enumerate(chunks, 1):
                    cached = self.db.get_existing(chunk.hash, 'line-by-line')
                    status = "[CACHED]" if cached else "[NEW]"
                    print(f"  {i}. {chunk.speaker_summary}: "
                          f"{chunk.line_count} lines {status}")
            else:
                print("\nSpeeches to process:")
                for i, speech in enumerate(speeches, 1):
                    cached = self.db.get_existing(speech.hash, 'line-by-line')
                    status = "[CACHED]" if cached else "[NEW]"
                    print(f"  {i}. {speech.speaker}: "
                          f"{speech.line_count} lines {status}")
            return None

        # Analyze each chunk
        analyses = []
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)}: "
                       f"{chunk.speaker_summary}")
            analysis = self._analyze_chunk(chunk)
            analyses.append(analysis)

        # Generate output document
        document = self._format_scene_document(chunks, analyses, scene_header)

        # Save to file in play-specific subdirectory
        play_dir = self.output_dir / self.play_name
        play_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename based on act/scene (handle prologues/epilogue specially)
        if self.scene == -1:
            output_filename = "epilogue_line-by-line.md"
        elif self.scene == 0:
            if self.act == 0:
                output_filename = "prologue_line-by-line.md"
            else:
                output_filename = f"act{self.act}_prologue_line-by-line.md"
        else:
            output_filename = f"act{self.act}_scene{self.scene}_line-by-line.md"
        output_path = play_dir / output_filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(document)

        logger.info(f"Saved scene analysis to {output_path}")
        return output_path


def parse_act_scene_string(act_scene: str) -> tuple[int, int]:
    """Parse 'Act IV, Scene VII', 'Prologue', or 'Epilogue' format to integers.

    Accepts formats like:
    - "Act IV, Scene VII"
    - "Act 4, Scene 7"
    - "act iv scene vii"
    - "Act IV Scene 7"
    - "Prologue" (returns act=0, scene=0 for opening prologue)
    - "Act 2 Prologue" or "Act II Prologue" (returns act=N, scene=0)
    - "Epilogue" (returns act=0, scene=-1)

    Args:
        act_scene: String in "Act N, Scene M", "Prologue", or "Epilogue" format

    Returns:
        Tuple of (act_number, scene_number) as integers.
        For prologues, scene=0. For epilogue, scene=-1.

    Raises:
        ValueError: If format is not recognized
    """
    # Roman numeral conversion
    def roman_to_int(roman: str) -> int:
        values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
        result = 0
        prev = 0
        for char in reversed(roman.upper()):
            curr = values.get(char, 0)
            if curr < prev:
                result -= curr
            else:
                result += curr
            prev = curr
        return result

    # Normalize input
    text = act_scene.strip().upper()

    # Check for "Prologue" or "Scene Prologue" (opening prologue before Act 1)
    if text in ('PROLOGUE', 'SCENE PROLOGUE'):
        return 0, 0

    # Check for "Epilogue" or "Scene Epilogue"
    if text in ('EPILOGUE', 'SCENE EPILOGUE'):
        return 0, -1

    # Check for "Act N Prologue" format
    prologue_pattern = r'ACT\s+([IVXLC]+|\d+)[,\s]+PROLOGUE'
    prologue_match = re.match(prologue_pattern, text)
    if prologue_match:
        act_str = prologue_match.group(1)
        if act_str.isdigit():
            act = int(act_str)
        else:
            act = roman_to_int(act_str)
        return act, 0

    # Pattern: "ACT <num>, SCENE <num>" or "ACT <num> SCENE <num>"
    # Where <num> can be Roman (IV) or Arabic (4)
    pattern = r'ACT\s+([IVXLC]+|\d+)[,\s]+SCENE\s+([IVXLC]+|\d+)'
    match = re.match(pattern, text)

    if not match:
        raise ValueError(
            f"Could not parse '{act_scene}'. "
            "Expected format: 'Act IV, Scene VII', 'Act 4, Scene 7', "
            "'Prologue', 'Act 2 Prologue', or 'Epilogue'"
        )

    act_str, scene_str = match.groups()

    # Convert to integers
    if act_str.isdigit():
        act = int(act_str)
    else:
        act = roman_to_int(act_str)

    if scene_str.isdigit():
        scene = int(scene_str)
    else:
        scene = roman_to_int(scene_str)

    return act, scene


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate line-by-line actor analysis for an entire scene',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Using "Act N, Scene M" format (from <M-a> clipboard)
    python scene_analyzer.py henry_v_gut.txt "Act IV, Scene VII"

    # Using numeric arguments
    python scene_analyzer.py henry_v_gut.txt 4 7

    # Dry run to see what would be processed
    python scene_analyzer.py henry_v_gut.txt "Act IV, Scene VII" --dry-run

    # Merge small speeches into 15-line chunks (fewer Claude Code calls)
    python scene_analyzer.py henry_v_gut.txt 4 7 --merge 15

    # Use direct API backend instead of claude-code
    python scene_analyzer.py henry_v_gut.txt 4 7 --backend api
        """
    )
    parser.add_argument(
        'play_file',
        type=Path,
        help='Path to the play text file'
    )
    parser.add_argument(
        'act_scene',
        nargs='+',
        help='Act and scene: either "Act IV, Scene VII" or two numbers: 4 7'
    )
    parser.add_argument(
        '--backend', '-b',
        choices=['api', 'claude-code'],
        default=os.getenv('GLOSS_BACKEND', DEFAULT_BACKEND),
        help=f'Backend for generation (default: {DEFAULT_BACKEND})'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=Path,
        default=None,
        help=f'Output directory (default: {GLOSSES_DIR})'
    )
    parser.add_argument(
        '--merge', '-m',
        type=int,
        default=0,
        metavar='LINES',
        help='Merge speeches into chunks of at least N lines (fewer calls)'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be processed without calling Claude Code'
    )

    args = parser.parse_args()

    # Parse act/scene from arguments
    act_scene_args = args.act_scene
    if len(act_scene_args) == 1:
        # Single argument: "Act IV, Scene VII" format
        try:
            act, scene = parse_act_scene_string(act_scene_args[0])
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif len(act_scene_args) == 2:
        # Two arguments: numeric act and scene
        try:
            act = int(act_scene_args[0])
            scene = int(act_scene_args[1])
        except ValueError:
            # Maybe it's "Act IV," "Scene VII" as two args
            combined = ' '.join(act_scene_args)
            try:
                act, scene = parse_act_scene_string(combined)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        # Multiple args - try combining them
        combined = ' '.join(act_scene_args)
        try:
            act, scene = parse_act_scene_string(combined)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate play file exists
    if not args.play_file.exists():
        print(f"Error: Play file not found: {args.play_file}", file=sys.stderr)
        sys.exit(1)

    # Check for API key if using API backend
    if args.backend == 'api' and not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    try:
        analyzer = SceneAnalyzer(
            play_file=args.play_file,
            act=act,
            scene=scene,
            backend=args.backend,
            output_dir=args.output_dir,
            merge_threshold=args.merge
        )

        output_path = analyzer.analyze(dry_run=args.dry_run)

        if output_path:
            print(f"\nScene analysis saved to: {output_path}")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
