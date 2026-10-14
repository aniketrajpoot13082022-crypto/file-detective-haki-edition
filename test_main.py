
import queue
import tempfile
import unittest
from pathlib import Path

from rinkusingh import (
    calculate_hash,
    format_size,
    scan_for_duplicates,
)


class FileDetectiveTests(unittest.TestCase):

    def test_identical_files_are_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)

            (folder / "first.txt").write_text(
                "One Piece", encoding="utf-8"
            )
            (folder / "copy.txt").write_text(
                "One Piece", encoding="utf-8"
            )
            (folder / "different.txt").write_text(
                "Different data", encoding="utf-8"
            )

            groups, stats = scan_for_duplicates(
                folder, queue.Queue()
            )

            self.assertEqual(len(groups), 1)
            self.assertEqual(len(groups[0]["paths"]), 2)
            self.assertEqual(stats["files_seen"], 3)

    def test_different_contents_are_not_duplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)

            (folder / "first.txt").write_text(
                "cat", encoding="utf-8"
            )
            (folder / "second.txt").write_text(
                "dog", encoding="utf-8"
            )

            groups, _ = scan_for_duplicates(
                folder, queue.Queue()
            )

            self.assertEqual(groups, [])

    def test_nested_folders_are_scanned(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            nested = folder / "nested"
            nested.mkdir()

            (folder / "first.txt").write_text(
                "same content", encoding="utf-8"
            )
            (nested / "copy.txt").write_text(
                "same content", encoding="utf-8"
            )

            groups, _ = scan_for_duplicates(
                folder, queue.Queue()
            )

            self.assertEqual(len(groups), 1)
            self.assertEqual(len(groups[0]["paths"]), 2)

    def test_empty_files_are_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)

            (folder / "empty1.txt").write_bytes(b"")
            (folder / "empty2.txt").write_bytes(b"")

            groups, _ = scan_for_duplicates(
                folder, queue.Queue()
            )

            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0]["size"], 0)

    def test_scanning_does_not_change_files(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            first = folder / "first.txt"
            second = folder / "copy.txt"

            first.write_bytes(b"Keep my data safe")
            second.write_bytes(b"Keep my data safe")

            original_first = first.read_bytes()
            original_second = second.read_bytes()

            scan_for_duplicates(folder, queue.Queue())

            self.assertEqual(
                first.read_bytes(), original_first
            )
            self.assertEqual(
                second.read_bytes(), original_second
            )

    def test_identical_files_have_identical_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            first = folder / "a.txt"
            second = folder / "b.txt"

            first.write_text("Haki!", encoding="utf-8")
            second.write_text("Haki!", encoding="utf-8")

            self.assertEqual(
                calculate_hash(first),
                calculate_hash(second)
            )

    def test_file_size_formatting(self):
        self.assertEqual(format_size(0), "0.0 B")
        self.assertEqual(format_size(1024), "1.0 KB")
        self.assertEqual(
            format_size(1024 * 1024), "1.0 MB"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
