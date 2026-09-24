"""Extract a YouTube transcript and generate an original, style-inspired script."""

from __future__ import annotations

import re
from typing import Callable
from urllib.parse import parse_qs, urlparse

from loguru import logger

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
MAX_TRANSCRIPT_CHARS = 12_000


class ChannelSimulationError(RuntimeError):
    """Raised when a source URL cannot be converted into a usable transcript."""


def _video_id_from_url(source_url: str) -> str | None:
    parsed = urlparse(source_url.strip())
    host = parsed.netloc.lower().split(":", 1)[0]
    path_parts = [part for part in parsed.path.split("/") if part]
    if host in {"youtu.be", "www.youtu.be"} and path_parts:
        return path_parts[0]
    if host.endswith("youtube.com"):
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id:
            return query_id
        if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
            return path_parts[1]
    return None


def _validate_video_id(video_id: str) -> str:
    video_id = video_id.strip()
    if not VIDEO_ID_RE.fullmatch(video_id):
        raise ChannelSimulationError("The YouTube URL does not contain a valid video ID.")
    return video_id


def resolve_video_id(source_url: str) -> str:
    """Resolve a video URL or a public channel URL to one video ID.

    Channel resolution uses yt-dlp only when needed; direct video URLs do not require
    a channel lookup. The first available video is used as the channel's style sample.
    """
    source_url = (source_url or "").strip()
    if not source_url:
        raise ChannelSimulationError("Please enter a YouTube video or channel URL.")
    direct_id = _video_id_from_url(source_url)
    if direct_id:
        return _validate_video_id(direct_id)
    if not re.match(r"^https?://(?:www\.)?youtube\.com/", source_url, re.I):
        raise ChannelSimulationError("Please enter a valid YouTube video or channel URL.")
    try:
        import yt_dlp

        options = {
            "extract_flat": True,
            "ignoreerrors": True,
            "quiet": True,
            "skip_download": True,
            "playlistend": 1,
        }
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(source_url, download=False)
        entries = (info or {}).get("entries") or []
        first_entry = next((entry for entry in entries if entry), None)
        candidate = (first_entry or info or {}).get("id")
        if candidate:
            return _validate_video_id(str(candidate))
    except ChannelSimulationError:
        raise
    except Exception as exc:  # yt-dlp reports provider-specific errors
        logger.warning("failed to resolve YouTube channel: {}", exc)
    raise ChannelSimulationError(
        "Could not find a public video in this YouTube channel. "
        "Try a specific video URL instead."
    )


def fetch_transcript(video_id: str, languages: list[str] | None = None) -> str:
    """Fetch transcript text, supporting both youtube-transcript-api APIs."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        language_list = languages or ["en", "ar"]
        if hasattr(api, "fetch"):
            transcript = api.fetch(video_id, languages=language_list)
        else:  # compatibility with youtube-transcript-api 0.x
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id, languages=language_list
            )
    except Exception as exc:
        raise ChannelSimulationError(f"Could not fetch the YouTube transcript: {exc}") from exc

    parts: list[str] = []
    for snippet in transcript:
        text = getattr(snippet, "text", None)
        if text is None and isinstance(snippet, dict):
            text = snippet.get("text")
        if text:
            parts.append(str(text).replace("\n", " ").strip())
    result = re.sub(r"\s+", " ", " ".join(parts)).strip()
    if not result:
        raise ChannelSimulationError("The selected YouTube video has an empty transcript.")
    return result[:MAX_TRANSCRIPT_CHARS]


def generate_original_script(
    transcript: str,
    *,
    language: str = "",
    paragraph_number: int = 1,
    llm_generator: Callable[..., str] | None = None,
) -> str:
    """Generate a new script inspired by a transcript without copying it verbatim."""
    transcript = re.sub(r"\s+", " ", (transcript or "")).strip()[:MAX_TRANSCRIPT_CHARS]
    if not transcript:
        raise ChannelSimulationError("A transcript is required to generate a script.")
    if llm_generator is None:
        from app.services import llm

        llm_generator = llm.generate_script
    subject = (
        "Create an original short-video script inspired by the ideas, pacing, and "
        "narrative structure in this source transcript. Do not quote, translate, or "
        "reuse distinctive phrases; use fresh wording and examples.\n\n"
        f"Source transcript:\n{transcript}"
    )
    script = llm_generator(
        video_subject=subject,
        language=language,
        paragraph_number=paragraph_number,
        video_script_prompt=(
            "Write an original script only. Preserve high-level storytelling traits "
            "but do not imitate a living creator's identifiable voice or reproduce "
            "the source wording."
        ),
        custom_system_prompt="",
    )
    if not script or not str(script).strip():
        raise ChannelSimulationError("The AI model returned an empty script.")
    return str(script).strip()


def simulate_from_source(
    source_url: str,
    *,
    language: str = "",
    paragraph_number: int = 1,
) -> tuple[str, str]:
    """Return ``(script, resolved_video_id)`` for a YouTube source."""
    video_id = resolve_video_id(source_url)
    transcript = fetch_transcript(video_id)
    return generate_original_script(
        transcript, language=language, paragraph_number=paragraph_number
    ), video_id
