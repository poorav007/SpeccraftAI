"""Unit tests for safe zip archive reading, Zip-Slip guards, and framework detection."""

import io
import unittest
import zipfile
from speccraft.reader import ArchiveSecurityError, SourceFileReader


class TestZipReaderAndFrameworkDetection(unittest.TestCase):
    """Test suite for zip archive ingestion, zip-slip defense, and framework detection."""

    def setUp(self):
        self.reader = SourceFileReader()

    def test_read_valid_zip_archive(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("main.py", "from fastapi import FastAPI\napp = FastAPI()\n")
            zf.writestr("routers/items.py", "# items\n")
            zf.writestr("notes.txt", "ignore me")

        buf.seek(0)
        sources = self.reader.read_zip_archive(buf.getvalue())
        rel_paths = [s.relative_path for s in sources]

        self.assertIn("main.py", rel_paths)
        self.assertIn("routers/items.py", rel_paths)
        self.assertNotIn("notes.txt", rel_paths)

    def test_zip_slip_attack_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            # Dangerous entry trying to escape sandbox
            zf.writestr("../../etc/passwd", "root:x:0:0:::")

        buf.seek(0)
        with self.assertRaises(ArchiveSecurityError):
            self.reader.read_zip_archive(buf.getvalue())

    def test_archive_file_count_limit_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for i in range(10):
                zf.writestr(f"file_{i}.py", "x = 1\n")

        buf.seek(0)
        # Small file count limit for testing
        with self.assertRaises(ArchiveSecurityError):
            self.reader.read_zip_archive(buf.getvalue(), max_file_count=5)

    def test_detect_framework_fastapi(self):
        sf1 = self.reader.read_code_string("from fastapi import FastAPI\napp = FastAPI()")
        sf2 = self.reader.read_code_string("import math\nprint(math.pi)")
        framework = self.reader.detect_framework([sf1, sf2])
        self.assertEqual(framework, "fastapi")

    def test_detect_framework_flask_and_express(self):
        sf_flask = self.reader.read_code_string("import flask\napp = flask.Flask(__name__)")
        self.assertEqual(self.reader.detect_framework([sf_flask]), "flask")

        sf_js = self.reader.read_code_string(
            "const express = require('express'); const app = express(); app.get('/hi', () => {});",
            virtual_name="app.js",
        )
        self.assertEqual(self.reader.detect_framework([sf_js]), "express")

    def test_detect_framework_unsupported(self):
        sf1 = self.reader.read_code_string("import django\nurlpatterns = []")
        sf2 = self.reader.read_code_string("def hello(): return 'world'")
        framework = self.reader.detect_framework([sf1, sf2])
        self.assertEqual(framework, "unsupported")


if __name__ == "__main__":
    unittest.main()

