import os
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import shift_subtitles as shift

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shift_subtitles.py")

SAMPLE = """\
1
00:00:10,000 --> 00:00:12,500
Hello world.

2
00:00:15,000 --> 00:00:18,000
This is a subtitle.
"""


class ParseTests(unittest.TestCase):
    def test_short_offsets(self):
        cases = {
            "+2.5": 2500,
            "-0.25": -250,
            "+1:30": 90_000,
            "-1:30": -90_000,
            "+1:02:03.5": 3_723_500,
            "+500ms": 500,
            "-500ms": -500,
            "+1m2s": 62_000,
            "+1m2.5s": 62_500,
            "+1h": 3_600_000,
            "+1.5m": 90_000,
            "+00:00:02:500": 2500,
            "-00:00:01:000": -1000,
            "+00:01:00:000": 60_000,
            "-01:00:00:000": -3_600_000,
            "+ 2.5": 2500,
            "+2,5": 2500,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(shift.parse_offset(text), expected)

    def test_invalid_offset(self):
        for text in ("2.5", "1:05.200", "+1m2", "+abc", ""):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    shift.parse_offset(text)

    def test_moments(self):
        self.assertEqual(shift.parse_moment("1:05.200"), 65_200)
        self.assertEqual(shift.parse_moment("1:02.000"), 62_000)
        self.assertEqual(shift.parse_moment("65.2"), 65_200)
        self.assertEqual(shift.parse_moment("1:02:03,500"), 3_723_500)
        self.assertEqual(
            shift.parse_moment("1:05.200") - shift.parse_moment("1:02.000"),
            3200,
        )

    def test_signed_moment_rejected(self):
        with self.assertRaises(ValueError):
            shift.parse_moment("+1:05.200")

    def test_timestamp_round_trip_keeps_milliseconds(self):
        self.assertEqual(shift.timestamp_to_ms("00:00:10,123"), 10_123)
        self.assertEqual(shift.ms_to_timestamp(10_123), "00:00:10,123")


class ShiftContentTests(unittest.TestCase):
    def test_forward_shift_preserves_text(self):
        updated, cues, clamped = shift.shift_content(SAMPLE, 2000)
        self.assertEqual(cues, 2)
        self.assertEqual(clamped, 0)
        self.assertIn("00:00:12,000 --> 00:00:14,500\nHello world.", updated)
        self.assertIn("00:00:17,000 --> 00:00:20,000\nThis is a subtitle.", updated)
        self.assertTrue(updated.startswith("1\n"))

    def test_millisecond_precision(self):
        content = "1\n00:00:10,123 --> 00:00:12,123\nHi\n"
        updated, _, _ = shift.shift_content(content, 1)
        self.assertIn("00:00:10,124 --> 00:00:12,124", updated)

    def test_hour_boundary(self):
        content = "1\n00:59:59,500 --> 01:00:01,000\nHi\n"
        updated, _, clamped = shift.shift_content(content, 1000)
        self.assertEqual(clamped, 0)
        self.assertIn("01:00:00,500 --> 01:00:02,000", updated)

    def test_clamp_before_zero(self):
        content = "1\n00:00:01,000 --> 00:00:03,000\nHi\n"
        updated, cues, clamped = shift.shift_content(content, -2000)
        self.assertEqual(cues, 1)
        self.assertEqual(clamped, 1)
        self.assertIn("00:00:00,000 --> 00:00:01,000", updated)

    def test_clamp_whole_cue(self):
        content = "1\n00:00:01,000 --> 00:00:02,000\nHi\n"
        updated, _, clamped = shift.shift_content(content, -5000)
        self.assertEqual(clamped, 1)
        self.assertIn("00:00:00,000 --> 00:00:00,000", updated)

    def test_keeps_positioning_suffix_and_ignores_dialogue(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000 X1:52 X2:303\n"
            "See 00:00:01,000 --> 00:00:02,000 in the text\n"
        )
        updated, cues, _ = shift.shift_content(content, 1000)
        self.assertEqual(cues, 1)
        self.assertIn("00:00:02,000 --> 00:00:03,000 X1:52 X2:303", updated)
        self.assertIn("See 00:00:01,000 --> 00:00:02,000 in the text", updated)

    def test_crlf_preserved(self):
        content = "1\r\n00:00:01,000 --> 00:00:02,000\r\nHi\r\n"
        updated, _, _ = shift.shift_content(content, 1000)
        self.assertEqual(
            updated,
            "1\r\n00:00:02,000 --> 00:00:03,000\r\nHi\r\n",
        )

    def test_no_cues(self):
        updated, cues, clamped = shift.shift_content("just text\n", 1000)
        self.assertEqual(updated, "just text\n")
        self.assertEqual(cues, 0)
        self.assertEqual(clamped, 0)


class CliTests(unittest.TestCase):
    def run_script(self, *args, stdin=None):
        return subprocess.run(
            [sys.executable, SCRIPT, *args],
            input=stdin,
            capture_output=True,
            text=True,
        )

    def write_sample(self, directory, content=SAMPLE, name="movie.srt"):
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        return path

    def test_overwrites_with_short_offset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_sample(directory)
            os.chmod(path, 0o640)
            result = self.run_script(path, "+2.5")
            self.assertEqual(result.returncode, 0, result.stderr)
            with open(path, encoding="utf-8", newline="") as handle:
                updated = handle.read()
            self.assertIn("00:00:12,500 --> 00:00:15,000", updated)
            self.assertIn("00:00:17,500 --> 00:00:20,500", updated)
            self.assertIn("Hello world.", updated)
            self.assertIn(f"Overwrote {path}", result.stdout)
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o640)
            self.assertFalse(any(name.startswith(".shift-") for name in os.listdir(directory)))

    def test_negative_offset_is_not_a_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_sample(directory)
            result = self.run_script(path, "-1.5")
            self.assertEqual(result.returncode, 0, result.stderr)
            with open(path, encoding="utf-8") as handle:
                updated = handle.read()
            self.assertIn("00:00:08,500 --> 00:00:11,000", updated)

    def test_sync_from_sentence_and_subtitle(self):
        with tempfile.TemporaryDirectory() as directory:
            content = "1\n00:01:02,000 --> 00:01:04,000\nHello world.\n"
            path = self.write_sample(directory, content)
            result = self.run_script(path, "1:05.200", "1:02.000")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("+3.200s", result.stdout)
            with open(path, encoding="utf-8") as handle:
                updated = handle.read()
            self.assertIn("00:01:05,200 --> 00:01:07,200", updated)

    def test_sync_pulls_late_subtitle_earlier(self):
        with tempfile.TemporaryDirectory() as directory:
            content = "1\n00:01:05,200 --> 00:01:07,200\nHello world.\n"
            path = self.write_sample(directory, content)
            result = self.run_script(path, "1:02.000", "1:05.200")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("-3.200s", result.stdout)
            with open(path, encoding="utf-8") as handle:
                updated = handle.read()
            self.assertIn("00:01:02,000 --> 00:01:04,000", updated)

    def test_prompts_when_times_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            content = "1\n00:01:02,000 --> 00:01:04,000\nHello world.\n"
            path = self.write_sample(directory, content)
            result = self.run_script(path, stdin="1:05.200\n1:02.000\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("When does the sentence start?", result.stdout)
            self.assertIn("When does the subtitle start showing?", result.stdout)
            with open(path, encoding="utf-8") as handle:
                updated = handle.read()
            self.assertIn("00:01:05,200 --> 00:01:07,200", updated)

    def test_bad_offset_leaves_file_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_sample(directory)
            result = self.run_script(path, "2.5")
            self.assertEqual(result.returncode, 1)
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), SAMPLE)

    def test_no_cues_leaves_file_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_sample(directory, "not an srt\n")
            result = self.run_script(path, "+1")
            self.assertEqual(result.returncode, 1)
            self.assertIn("No subtitle cues", result.stderr)
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "not an srt\n")

    def test_missing_file(self):
        result = self.run_script("missing-file.srt", "+1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("File not found", result.stderr)

    def test_help_and_usage(self):
        help_result = self.run_script("-h")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("overwritten in place", help_result.stdout)
        usage = self.run_script()
        self.assertEqual(usage.returncode, 1)
        self.assertIn("Usage:", usage.stderr)

    def test_utf8_bom_and_clamp_message(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_sample(directory, "\ufeff1\n00:00:01,000 --> 00:00:02,000\nHi\n")
            result = self.run_script(path, "-5")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Clamped 1 cues", result.stdout)
            with open(path, encoding="utf-8") as handle:
                updated = handle.read()
            self.assertFalse(updated.startswith("\ufeff"))
            self.assertIn("00:00:00,000 --> 00:00:00,000", updated)

    def test_resolve_shift_prompts(self):
        with mock.patch("builtins.input", side_effect=["1:05.2", "1:02"]):
            self.assertEqual(shift.resolve_shift([]), 3200)


if __name__ == "__main__":
    unittest.main()
