"""Unit tests for SourceFileReader and path traversal safety guards."""

import tempfile
import unittest
from pathlib import Path

from speccraft.reader import SourceFileReader
from speccraft.utils.path_safety import FileTooLargeError, PathSecurityError, validate_safe_path
from speccraft.utils.timing import Timer


class TestSourceFileReader(unittest.TestCase):
    """Test suite for safe source code reader and security guards."""

    def setUp(self):
        self.reader = SourceFileReader(max_file_size=1024 * 100)  # 100 KB limit for tests
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name).resolve()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_code_string(self):
        code = "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/')\ndef root():\n    return {'msg': 'ok'}\n"
        source = self.reader.read_code_string(code, virtual_name="test_snippet.py")
        self.assertEqual(source.relative_path, "test_snippet.py")
        self.assertIsNone(source.absolute_path)
        self.assertEqual(source.loc, 7)
        self.assertIn("@app.get('/')", source.content)

    def test_read_file_success(self):
        file_path = self.base_path / "sample.py"
        file_path.write_text("print('hello world')\nx = 1\n", encoding="utf-8")

        source = self.reader.read_file(file_path, base_dir=self.base_path)
        self.assertEqual(source.relative_path, "sample.py")
        self.assertEqual(source.loc, 2)
        self.assertIn("print('hello world')", source.content)

    def test_path_traversal_blocked(self):
        # Attempt to access outside the base directory using ../
        outside_file = self.base_path.parent / "outside.py"
        with self.assertRaises(PathSecurityError):
            validate_safe_path(outside_file, base_dir=self.base_path)

    def test_file_too_large_rejected(self):
        small_reader = SourceFileReader(max_file_size=50)  # 50 bytes limit
        oversized = "a" * 100
        with self.assertRaises(FileTooLargeError):
            small_reader.read_code_string(oversized)

    def test_read_directory_skips_ignored(self):
        # Create normal files
        (self.base_path / "main.py").write_text("# main file\n", encoding="utf-8")
        sub_dir = self.base_path / "routers"
        sub_dir.mkdir()
        (sub_dir / "items.py").write_text("# items route\n", encoding="utf-8")

        # Create ignored folder (__pycache__, .git)
        cache_dir = self.base_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "items.cpython-311.py").write_text("# bytecode dummy\n", encoding="utf-8")

        # Create non-python file
        (self.base_path / "notes.txt").write_text("plain text", encoding="utf-8")

        results = self.reader.read_directory(self.base_path)
        rel_paths = [r.relative_path for r in results]

        self.assertIn("main.py", rel_paths)
        self.assertIn("routers/items.py", rel_paths)
        self.assertNotIn("notes.txt", rel_paths)
        # Verify ignored folder was never read
        self.assertFalse(any("__pycache__" in p for p in rel_paths))

    def test_timer_utility(self):
        with Timer() as timer:
            _ = sum(i * i for i in range(1000))
        self.assertGreater(timer.duration_ms, 0.0)


if __name__ == "__main__":
    unittest.main()

