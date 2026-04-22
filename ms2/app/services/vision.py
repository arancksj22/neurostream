from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Sequence

from app.core.config import Settings
from app.models.schemas import FrameAnalysis, FrameInput
from app.services.s3_helper import download_s3_file


logger = logging.getLogger(__name__)


class VisionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def analyze(self, frame_images: Sequence[FrameInput]) -> list[FrameAnalysis]:
        if not frame_images:
            return []

        if (
            not self._settings.mock_external_services
            and self._settings.gemini_api_key
            and self._settings.gemini_vision_model
        ):
            try:
                return await asyncio.to_thread(self._analyze_with_gemini, frame_images)
            except Exception as exc:
                logger.warning("Gemini vision failed, falling back to mock: %s", exc)

        return self._fallback_analysis(frame_images)

    def _analyze_with_gemini(self, frame_images: Sequence[FrameInput]) -> list[FrameAnalysis]:
        from google import genai
        from google.genai import types
        from PIL import Image

        client = genai.Client(api_key=self._settings.gemini_api_key)

        analyses: list[FrameAnalysis] = []
        downloaded_files: list[str] = []

        prompt = (
            "Analyze this video frame. Respond ONLY with a JSON object (no markdown) with these keys:\n"
            '- "description": A 1-2 sentence description of the scene.\n'
            '- "objects": A list of 3-5 notable objects visible in the frame.\n'
            '- "onscreen_text": Any text visible on screen (empty string if none).\n'
        )

        try:
            for index, frame in enumerate(frame_images):
                timestamp = frame.timestamp if frame.timestamp is not None else float(index * 5)

                # Resolve file: download from S3 if not local
                frame_path = Path(frame.s3_key)
                if frame_path.exists():
                    local_path = str(frame_path)
                else:
                    local_path = download_s3_file(self._settings, frame.s3_key)
                    downloaded_files.append(local_path)

                try:
                    image = Image.open(local_path)
                    response = client.models.generate_content(
                        model=self._settings.gemini_vision_model,
                        contents=[prompt, image],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0,
                        ),
                    )
                    parsed = self._parse_vision_response(response.text)

                    analyses.append(
                        FrameAnalysis(
                            timestamp=timestamp,
                            description=parsed.get("description", f"Visual scene at {timestamp:.1f}s"),
                            source_key=frame.s3_key,
                            objects=parsed.get("objects", []),
                            onscreen_text=parsed.get("onscreen_text", ""),
                        )
                    )
                except Exception as exc:
                    logger.warning("Vision analysis failed for frame %s: %s", frame.s3_key, exc)
                    # Fallback for this individual frame
                    stem = Path(frame.s3_key).stem.replace("_", " ").replace("-", " ")
                    analyses.append(
                        FrameAnalysis(
                            timestamp=timestamp,
                            description=f"Visual scene captured in {stem or f'frame {index + 1}'}.",
                            source_key=frame.s3_key,
                            objects=[],
                            onscreen_text="",
                        )
                    )
        finally:
            for path in downloaded_files:
                try:
                    os.remove(path)
                except OSError:
                    pass

        return analyses

    @staticmethod
    def _parse_vision_response(text: str) -> dict:
        """Parse the Gemini response — handles both raw JSON and markdown-wrapped JSON."""
        cleaned = text.strip()
        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last lines (```json and ```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "description": text.strip()[:200],
                "objects": [],
                "onscreen_text": "",
            }

    def _fallback_analysis(self, frame_images: Sequence[FrameInput]) -> list[FrameAnalysis]:
        analyses: list[FrameAnalysis] = []
        for index, frame in enumerate(frame_images):
            timestamp = frame.timestamp if frame.timestamp is not None else float(index * 5)
            stem = Path(frame.s3_key).stem.replace("_", " ").replace("-", " ")
            descriptive_label = stem or f"frame {index + 1}"
            objects = [part for part in descriptive_label.split()[:3] if part]
            description = f"[mock visual] Visual scene captured in {descriptive_label} with notable on-screen context."
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
