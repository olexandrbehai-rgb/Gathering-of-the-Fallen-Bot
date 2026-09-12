import argparse
import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_youtube_catalog import ImportError, parse_videos, run


VIDEO_ID = "abcdefghijk"


def youtube_html() -> str:
    initial_data = {
        "contents": [
            {
                "lockupViewModel": {
                    "contentId": VIDEO_ID,
                    "contentType": "LOCKUP_CONTENT_TYPE_VIDEO",
                    "contentImage": {
                        "thumbnailViewModel": {
                            "overlays": [
                                {
                                    "thumbnailBottomOverlayViewModel": {
                                        "badges": [
                                            {"thumbnailBadgeViewModel": {"text": "4:07"}}
                                        ]
                                    }
                                }
                            ]
                        }
                    },
                    "metadata": {
                        "lockupMetadataViewModel": {
                            "title": {"content": "Справжня назва"}
                        }
                    },
                }
            }
        ]
    }
    return "<script>var ytInitialData = " + json.dumps(initial_data) + ";</script>"


class ImportYouTubeCatalogTests(unittest.TestCase):
    def test_parses_title_id_and_duration(self):
        self.assertEqual(
            parse_videos(youtube_html()),
            [{"title": "Справжня назва", "videoId": VIDEO_ID, "duration": "4:07"}],
        )

    def test_preview_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            source_path = root / "channel.html"
            catalog = {
                "bandLinks": {"YouTube": "https://www.youtube.com/@official"},
                "moods": {"fire": "Fire"},
                "videos": [],
                "tracks": [],
                "releases": [{"description": "Manual"}],
            }
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            source_path.write_text(youtube_html(), encoding="utf-8")
            before = catalog_path.read_bytes()

            result = run(
                argparse.Namespace(
                    catalog=str(catalog_path),
                    source_file=str(source_path),
                    apply=False,
                    mood=[],
                )
            )

            self.assertEqual(result, 0)
            self.assertEqual(catalog_path.read_bytes(), before)

    def test_apply_requires_manual_mood(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            source_path = root / "channel.html"
            catalog = {
                "bandLinks": {"YouTube": "https://www.youtube.com/@official"},
                "moods": {"fire": "Fire"},
                "videos": [],
                "tracks": [],
                "releases": [{"description": "Manual"}],
            }
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            source_path.write_text(youtube_html(), encoding="utf-8")

            with self.assertRaisesRegex(ImportError, "assign --mood"):
                run(
                    argparse.Namespace(
                        catalog=str(catalog_path),
                        source_file=str(source_path),
                        apply=True,
                        mood=[],
                    )
                )

            self.assertEqual(json.loads(catalog_path.read_text()), catalog)

    def test_apply_preserves_release_and_adds_manual_mood(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            source_path = root / "channel.html"
            release = {"description": "Manual"}
            catalog = {
                "bandLinks": {"YouTube": "https://www.youtube.com/@official"},
                "moods": {"fire": "Fire"},
                "videos": [],
                "tracks": [],
                "releases": [release],
            }
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            source_path.write_text(youtube_html(), encoding="utf-8")

            run(
                argparse.Namespace(
                    catalog=str(catalog_path),
                    source_file=str(source_path),
                    apply=True,
                    mood=[f"{VIDEO_ID}=fire"],
                )
            )

            updated = json.loads(catalog_path.read_text())
            self.assertEqual(updated["releases"], [release])
            self.assertEqual(updated["videos"][0]["moods"], ["fire"])


if __name__ == "__main__":
    unittest.main()