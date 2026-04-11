from __future__ import annotations

from pathlib import Path
from typing import Sequence

from app.core.config import Settings
from app.models.schemas import FrameAnalysis, FrameInput


class VisionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def analyze(self, frame_images: Sequence[FrameInput]) -> list[FrameAnalysis]:
        if not frame_images:
            return []
        return self._fallback_analysis(frame_images)

    def _fallback_analysis(self, frame_images: Sequence[FrameInput]) -> list[FrameAnalysis]:
        analyses: list[FrameAnalysis] = []
        for index, frame in enumerate(frame_images):
            timestamp = frame.timestamp if frame.timestamp is not None else float(index * 5)
            stem = Path(frame.s3_key).stem.replace("_", " ").replace("-", " ")
            descriptive_label = stem or f"frame {index + 1}"
            objects = [part for part in descriptive_label.split()[:3] if part]
            description = f"Visual scene captured in {descriptive_label} with notable on-screen context."
            analyses.append(
                FrameAnalysis(
                    timestamp=timestamp,
                    description=description,
                    source_key=frame.s3_key,
                    objects=objects,
                    onscreen_text=descriptive_label.title(),
                )
            )
        return analyses

