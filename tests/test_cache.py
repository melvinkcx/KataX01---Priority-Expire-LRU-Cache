import time

from src.cache import Cache


def get_timestamp_from_now(add_ms: int) -> int:
    return int(time.time()) + add_ms


def test_add_entry():
    cache = Cache()

    cache.add(key="key_3", value="value_3", priority=50, expiry=get_timestamp_from_now(add_ms=10_000))
    cache.add(key="key_2", value="value_2", priority=100, expiry=get_timestamp_from_now(add_ms=10_000))
    cache.add(key="key_1", value="value_1", priority=150, expiry=get_timestamp_from_now(add_ms=10_000))

    assert len(cache._entries) == len(cache._priority) == 3


def test_add_entry_beyond_max_size():
    cache = Cache(max_size=3)

    expiry = get_timestamp_from_now(add_ms=10_000)
    cache.add(key="key_4", value="value_4", priority=30, expiry=expiry)  # will be replaced
    cache.add(key="key_3", value="value_3", priority=50, expiry=expiry)
    cache.add(key="key_2", value="value_2", priority=100, expiry=expiry)
    cache.add(key="key_1", value="value_1", priority=150, expiry=expiry)

    assert len(cache._entries) == 3
    assert len([entry for entry in cache._priority if entry.is_valid()]) == 3
    assert cache.list_keys() == ["key_3", "key_2", "key_1"]
    assert cache.get(key="key_4") is None


def test_get_entry():
    cache = Cache()

    value, entry = cache.get("key_1"), cache.peek("key_1")
    assert value is None
    assert entry is None

    expiry = get_timestamp_from_now(add_ms=10_000)
    cache.add(key="key_1", value="value_1", priority=100, expiry=expiry)

    value = cache.get("key_1")
    assert value == "value_1"

    entry = cache.peek("key_1")
    assert entry.key == "key_1"
    assert entry.value == "value_1"
    assert entry.is_valid()
    assert entry.priority == 100
    assert entry.expiry == expiry
    assert entry.last_used_at is not None


def test_peek_entry():
    cache = Cache()
    cache.add(key="key_1", value="value_1", priority=100, expiry=get_timestamp_from_now(add_ms=10_000))

    entry = cache.peek("key_1")
    assert entry.key == "key_1"
    assert entry.last_used_at is None  # peek shouldn't affect last_used_at


def test_eviction__same_priority_n_expiry_n_lru():
    cache = Cache(max_size=3)
    expiry = get_timestamp_from_now(add_ms=10_000)

    cache.add(key="key_1", value="value_1", priority=100, expiry=expiry)
    cache.add(key="key_2", value="value_2", priority=100, expiry=expiry)
    cache.add(key="key_3", value="value_3", priority=100, expiry=expiry)
    cache.add(key="key_4", value="value_4", priority=100, expiry=expiry)

    assert cache.list_keys() == ["key_2", "key_3", "key_4"]


def test_eviction__same_priority_n_expiry_not_lru_1():
    cache = Cache(max_size=3)
    expiry = get_timestamp_from_now(add_ms=10_000)

    cache.add(key="key_1", value="value_1", priority=100, expiry=expiry)
    cache.get("key_1")

    cache.add(key="key_2", value="value_2", priority=100, expiry=expiry)  # should be evicted

    cache.add(key="key_3", value="value_3", priority=100, expiry=expiry)
    cache.get("key_3")

    cache.add(key="key_4", value="value_4", priority=100, expiry=expiry)
    cache.get("key_4")

    assert cache.list_keys() == ["key_1", "key_3", "key_4"]


def test_eviction__same_priority_n_expiry_not_lru_2():
    cache = Cache(max_size=3)
    now, expiry = get_timestamp_from_now(add_ms=0), get_timestamp_from_now(add_ms=10_000)

    cache.add(key="key_1", value="value_1", priority=100, expiry=expiry)
    cache.peek(key="key_1").last_used_at = now - 1_000

    cache.add(key="key_2", value="value_2", priority=100, expiry=expiry)  # should be evicted
    cache.peek(key="key_2").last_used_at = now - 5_000

    cache.add(key="key_3", value="value_3", priority=100, expiry=expiry)
    cache.peek(key="key_3").last_used_at = now - 1_000

    cache.add(key="key_4", value="value_4", priority=100, expiry=expiry)

    assert cache.list_keys() == ["key_1", "key_3", "key_4"]


def test_remove_entry():
    cache = Cache(max_size=3)

    cache.add(key="key_1", value="value_1", priority=100, expiry=get_timestamp_from_now(add_ms=10_000))
    cache.remove(key="key_1")

    assert cache.list_keys() == []
    assert cache._priority[0].is_removed


def test_vacuum():
    cache = Cache(max_size=3)
    expiry = get_timestamp_from_now(add_ms=10_000)

    cache.add(key="key_1", value="value_1", priority=100, expiry=expiry)
    cache.add(key="key_2", value="value_2", priority=100, expiry=expiry)
    cache.add(key="key_3", value="value_3", priority=100, expiry=expiry)
    cache.remove("key_1")
    cache.remove("key_3")

    assert cache.list_keys() == ["key_2"]
    assert len(cache._priority) == 3
    assert len([entry for entry in cache._priority if entry.is_removed]) == 2

    cache.vacuum()
    assert len(cache._priority) == 1
    assert cache._priority[0] == cache.peek("key_2")
