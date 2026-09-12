"""Preview and safely import videos from the official YouTube channel."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "catalog" / "fallen-catalog.json"
USER_AGENT = "Mozilla/5.0 (compatible; FallenCatalogImporter/1.0)"
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
DURATION_RE = re.compile(r"^(?:\d+:)?\d{1,2}:\d{2}$")


class ImportError(RuntimeError):
    """Raised when YouTube data cannot be imported safely."""


def _initial_data(html: str) -> dict[str, Any]:
    markers = ("var ytInitialData = ", "window[\"ytInitialData\"] = ")
    decoder = json.JSONDecoder()
    for marker in markers:
        start = html.find(marker)
        if start < 0:
            continue
        start += len(marker)
        try:
            value, _ = decoder.raw_decode(html[start:])
        except json.JSONDecodeError as exc:
            raise ImportError("YouTube returned malformed initial data.") from exc
        if isinstance(value, dict):
            return value
    raise ImportError("YouTube initial data was not found; the page format may have changed.")


def _walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _duration(lockup: dict[str, Any]) -> str | None:
    image = lockup.get("contentImage", {})
    for node in _walk(image):
        badge = node.get("thumbnailBadgeViewModel")
        if isinstance(badge, dict):
            text = badge.get("text")
            if isinstance(text, str) and DURATION_RE.fullmatch(text):
                return text
    return None


def parse_videos(html: str) -> list[dict[str, str]]:
    """Extract ordinary channel videos from YouTube's embedded page data."""
    videos: list[dict[str, str]] = []
    seen: set[str] = set()
    for node in _walk(_initial_data(html)):
        lockup = node.get("lockupViewModel")
        if not isinstance(lockup, dict) or lockup.get("contentType") != "LOCKUP_CONTENT_TYPE_VIDEO":
            continue
        video_id = lockup.get("contentId")
        title = (
            lockup.get("metadata", {})
            .get("lockupMetadataViewModel", {})
            .get("title", {})
            .get("content")
        )
        duration = _duration(lockup)
        if not (
            isinstance(video_id, str)
            and VIDEO_ID_RE.fullmatch(video_id)
            and isinstance(title, str)
            and title.strip()
            and duration
        ):
            continue
        if video_id not in seen:
            videos.append({"title": title.strip(), "videoId": video_id, "duration": duration})
            seen.add(video_id)
    if not videos:
        raise ImportError("No videos with titles and durations were found on the channel page.")
    return videos


def fetch_channel(channel_url: str) -> str:
    url = channel_url.rstrip("/") + "/videos"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "uk,en;q=0.8"})
    try:
        with urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", "replace")
    except OSError as exc:
        raise ImportError(f"Could not load the official YouTube channel: {exc}") from exc


def parse_moods(values: list[str], allowed: set[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for value in values:
        video_id, separator, raw_moods = value.partition("=")
        moods = [mood.strip() for mood in raw_moods.split(",") if mood.strip()]
        if not separator or not VIDEO_ID_RE.fullmatch(video_id) or not moods:
            raise ImportError(f"Invalid --mood value: {value!r}; expected VIDEO_ID=mood[,mood].")
        unknown = set(moods) - allowed
        if unknown:
            raise ImportError(f"Unknown mood(s) for {video_id}: {', '.join(sorted(unknown))}.")
        result[video_id] = list(dict.fromkeys(moods))
    return result


def _atomic_write(path: Path, catalog: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(catalog, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def run(args: argparse.Namespace) -> int:
    catalog_path = Path(args.catalog)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    channel_url = catalog.get("bandLinks", {}).get("YouTube")
    if not isinstance(channel_url, str) or not channel_url.startswith("https://www.youtube.com/"):
        raise ImportError("Catalog bandLinks.YouTube must contain the official YouTube channel URL.")

    html = Path(args.source_file).read_text(encoding="utf-8") if args.source_file else fetch_channel(channel_url)
    remote = parse_videos(html)
    existing_ids = {video["videoId"] for video in catalog["videos"]}
    additions = [video for video in remote if video["videoId"] not in existing_ids]

    print(f"Official channel: {channel_url}")
    print(f"Found {len(remote)} channel videos; {len(additions)} are new.")
    if not additions:
        print("Catalog is already up to date.")
        return 0

    for video in additions:
        print(f'+ {video["title"]} [{video["videoId"]}] {video["duration"]}')

    if not args.apply:
        print("\nPreview only: catalog was not changed.")
        print("To apply, assign a mood to every new video and add --apply:")
        for video in additions:
            print(f'  --mood {video["videoId"]}=<mood>')
        print(f'Allowed moods: {", ".join(catalog["moods"].keys())}')
        return 0

    mood_map = parse_moods(args.mood, set(catalog["moods"]))
    missing = [video["videoId"] for video in additions if video["videoId"] not in mood_map]
    extra = sorted(set(mood_map) - {video["videoId"] for video in additions})
    if missing:
        raise ImportError("Refusing to write: assign --mood for new video(s): " + ", ".join(missing))
    if extra:
        raise ImportError("Refusing to write: --mood supplied for non-new video(s): " + ", ".join(extra))

    catalog["videos"].extend({**video, "moods": mood_map[video["videoId"]]} for video in additions)
    _atomic_write(catalog_path, catalog)
    print(f"Added {len(additions)} video(s) to {catalog_path}.")
    print("Release descriptions were not changed. Run `pnpm validate:catalog` before committing.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview new official YouTube videos; write only with --apply and explicit moods."
    )
    parser.add_argument("--apply", action="store_true", help="Atomically update the catalog.")
    parser.add_argument(
        "--mood",
        action="append",
        default=[],
        metavar="VIDEO_ID=MOOD[,MOOD]",
        help="Manual mood assignment for a new video; repeat for each video.",
    )
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG), help=argparse.SUPPRESS)
    parser.add_argument("--source-file", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        return run(args)
    except (ImportError, json.JSONDecodeError, KeyError, OSError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())