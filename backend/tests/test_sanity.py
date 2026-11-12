import unittest

class TestBackendSanity(unittest.TestCase):
    def test_environment_ready(self):
        """Verifies backend test discovery works in CI."""
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()