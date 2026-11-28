"""Tests for incremental SHA-256 AST parsing & cache eviction."""

from pathlib import Path

from speccraft.route_extractor import RouteExtractor


def test_incremental_cache_hits_misses_and_selective_reparse(tmp_path: Path):
    app_dir = tmp_path / "proj"
    app_dir.mkdir()
    cache_file = tmp_path / ".speccraft_cache.json"

    f1 = app_dir / "a.py"
    f2 = app_dir / "b.py"
    f1.write_text(
        'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/a")\ndef get_a(): return {}\n',
        encoding="utf-8",
    )
    f2.write_text(
        'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/b")\ndef get_b(): return {}\n',
        encoding="utf-8",
    )

    extractor = RouteExtractor()

    # Run 1: cold cache -> 0 hits, 2 misses
    r1 = extractor.extract_from_path(app_dir, incremental=True, cache_path=cache_file)
    assert r1.cache_hits == 0
    assert r1.cache_misses == 2
    assert len(r1.endpoints) == 2

    # Run 2: unchanged -> 2 hits, 0 misses
    r2 = extractor.extract_from_path(app_dir, incremental=True, cache_path=cache_file)
    assert r2.cache_hits == 2
    assert r2.cache_misses == 0
    assert len(r2.endpoints) == 2

    # Modify only b.py -> 1 hit (a.py), 1 miss (b.py)
    f2.write_text(
        'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/b")\ndef get_b(): return {}\n@app.post("/b2")\ndef post_b2(): return {}\n',
        encoding="utf-8",
    )
    r3 = extractor.extract_from_path(app_dir, incremental=True, cache_path=cache_file)
    assert r3.cache_hits == 1
    assert r3.cache_misses == 1
    assert len(r3.endpoints) == 3

    # Delete a.py -> evicted cleanly, 1 hit (b.py), 0 misses
    f1.unlink()
    r4 = extractor.extract_from_path(app_dir, incremental=True, cache_path=cache_file)
    assert r4.cache_hits == 1
    assert r4.cache_misses == 0
    assert len(r4.endpoints) == 2

