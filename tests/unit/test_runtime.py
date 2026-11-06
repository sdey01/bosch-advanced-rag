from src.runtime import cache_source_fingerprint


def test_cache_source_fingerprint_tracks_pdf_and_embedding_model() -> None:
    original = cache_source_fingerprint("pdf-v1", "embedding-v1")

    assert cache_source_fingerprint("pdf-v1", "embedding-v1") == original
    assert cache_source_fingerprint("pdf-v2", "embedding-v1") != original
    assert cache_source_fingerprint("pdf-v1", "embedding-v2") != original
