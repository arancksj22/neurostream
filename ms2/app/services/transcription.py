from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Sequence

from app.core.config import Settings
from app.models.schemas import AudioSegmentInput, TranscriptSegment


logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def transcribe(self, audio_segments: Sequence[AudioSegmentInput]) -> list[TranscriptSegment]:
        if not audio_segments:
            return []

        if not self._settings.mock_external_services:
            try:
                return await asyncio.to_thread(self._transcribe_with_whisper, audio_segments)
            except Exception as exc:
                logger.warning("Whisper transcription failed, falling back to mock output: %s", exc)

        return self._fallback_transcription(audio_segments)

    def _transcribe_with_whisper(
        self,
        audio_segments: Sequence[AudioSegmentInput],
    ) -> list[TranscriptSegment]:
        import whisper

        model = whisper.load_model(self._settings.whisper_model)
        transcripts: list[TranscriptSegment] = []
        cursor = 0.0
        for index, audio_segment in enumerate(audio_segments):
            media_path = Path(audio_segment.s3_key)
            if not media_path.exists():
                raise FileNotFoundError(
                    f"Audio segment {audio_segment.s3_key} must be a local file path when "
                    "MOCK_EXTERNAL_SERVICES=false"
                )
            result = model.transcribe(str(media_path))
            segments = result.get("segments") or []
            start_offset = audio_segment.start_time if audio_segment.start_time is not None else cursor
            if segments:
                for segment in segments:
                    start_time = start_offset + float(segment.get("start", 0.0))
                    end_time = start_offset + float(segment.get("end", float(segment.get("start", 0.0))))
                    transcripts.append(
                        TranscriptSegment(
                            start_time=start_time,
                            end_time=end_time,
                            text=segment.get("text", "").strip() or f"Segment {index + 1}",
                            source_key=audio_segment.s3_key,
                        )
                    )
                cursor = transcripts[-1].end_time
                continue

            start_time = audio_segment.start_time if audio_segment.start_time is not None else cursor
            end_time = audio_segment.end_time if audio_segment.end_time is not None else start_time + 15.0
            transcripts.append(
                TranscriptSegment(
                    start_time=start_time,
                    end_time=end_time,
                    text=result.get("text", "").strip() or f"Transcribed audio {index + 1}",
                    source_key=audio_segment.s3_key,
                )
            )
            cursor = end_time
        return transcripts

    def _fallback_transcription(
        self,
        audio_segments: Sequence[AudioSegmentInput],
    ) -> list[TranscriptSegment]:
        transcripts: list[TranscriptSegment] = []
        cursor = 0.0
        for index, audio_segment in enumerate(audio_segments):
            start_time = audio_segment.start_time if audio_segment.start_time is not None else cursor
            end_time = audio_segment.end_time if audio_segment.end_time is not None else start_time + 15.0
            stem = Path(audio_segment.s3_key).stem.replace("_", " ").replace("-", " ")
            text = f"Transcribed narration from {stem or f'audio segment {index + 1}'}."
            transcripts.append(
                TranscriptSegment(
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                    source_key=audio_segment.s3_key,
                )
            )
            cursor = end_time
        return transcripts
