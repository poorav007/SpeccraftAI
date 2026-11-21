"""Automated performance benchmark verifying < 2.0s parse requirement for 10,000 LOC."""

import statistics
import time
import unittest
from pathlib import Path

from speccraft.route_extractor import RouteExtractor


class Test10kLineBenchmark(unittest.TestCase):
    """PRD Evaluation Requirement: Static AST extraction of 10,000 lines must complete in < 2.0 seconds."""

    @classmethod
    def setUpClass(cls):
        cls.synthetic_dir = Path(__file__).parent.parent / "samples" / "synthetic_10k" / "synthetic_app"
        # If synthetic_app doesn't exist, generate it
        if not cls.synthetic_dir.exists():
            from speccraft.samples.synthetic_10k.generate_10k import generate_synthetic_codebase
            generate_synthetic_codebase(cls.synthetic_dir, 10000)

        cls.extractor = RouteExtractor()

    def test_10k_lines_under_two_seconds(self):
        """Verify 10,000-line codebase parses in under 2.0 seconds (median of timed runs)."""
        # 1 Warm-up run
        warmup_res = self.extractor.extract_from_path(self.synthetic_dir)
        self.assertGreaterEqual(warmup_res.total_loc, 9500, f"Expected ~10k LOC, got {warmup_res.total_loc}")
        self.assertGreater(len(warmup_res.endpoints), 100, "Expected > 100 extracted routes")

        # 3 Timed runs
        durations = []
        for _ in range(3):
            t0 = time.perf_counter()
            res = self.extractor.extract_from_path(self.synthetic_dir)
            t1 = time.perf_counter()
            durations.append(t1 - t0)

        median_duration = statistics.median(durations)
        throughput = warmup_res.total_loc / median_duration

        print(
            f"\n[BENCHMARK REPORT] Scanned {warmup_res.total_loc} LOC across {warmup_res.files_scanned} files "
            f"in {median_duration * 1000.0:.2f}ms (Throughput: {throughput:.0f} lines/sec). "
            f"Found {len(warmup_res.endpoints)} endpoints, {len(warmup_res.schemas)} schemas."
        )

        # STRICT PRD TARGET: Under 2.0 seconds
        self.assertLess(
            median_duration,
            2.0,
            f"Benchmark failed: 10k LOC took {median_duration:.3f}s, exceeding the 2.0s PRD limit!",
        )


if __name__ == "__main__":
    unittest.main()

