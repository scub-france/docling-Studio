from infra.preview_cache import PreviewCache


def test_preview_cache_evicts_oldest_image_to_stay_within_byte_budget():
    cache = PreviewCache(max_bytes=6)
    first = ("a.pdf", 1, 1, 1, 150, "png")
    second = ("a.pdf", 1, 1, 2, 150, "png")
    third = ("a.pdf", 1, 1, 3, 150, "png")

    cache.put(first, b"aaa")
    cache.put(second, b"bb")
    assert cache.get(first) == b"aaa"  # A recently used page survives eviction.
    cache.put(third, b"ccc")

    assert cache.get(first) == b"aaa"
    assert cache.get(second) is None
    assert cache.get(third) == b"ccc"


def test_preview_cache_skips_image_larger_than_budget():
    cache = PreviewCache(max_bytes=2)
    key = ("a.pdf", 1, 1, 1, 150, "png")
    cache.put(key, b"abc")
    assert cache.get(key) is None
