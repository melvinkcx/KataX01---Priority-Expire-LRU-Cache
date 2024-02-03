import heapq
import logging
import time
from dataclasses import dataclass, field
from typing import Any, TypeAlias

logger = logging.getLogger(__name__)

EntryValue: TypeAlias = Any


def get_timestamp() -> int:
    return int(time.time())


@dataclass(order=True)
class Entry:
    priority: int  # the larger the value, the higher the priority for now, will be fixed later
    expiry: int = field(compare=False)  # monotonic time
    key: str = field(compare=False)
    value: EntryValue = field(compare=False)
    is_removed: bool = field(default=False, compare=False)
    last_used_at: int = field(default=None, compare=False)

    def get_value(self) -> EntryValue | None:
        if not self.is_valid():
            return

        self.last_used_at = get_timestamp()
        return self.value

    def is_valid(self) -> bool:
        return not self.is_expired() and not self.is_removed

    def is_expired(self) -> bool:
        return get_timestamp() > self.expiry


class Cache:
    def __init__(self, max_size: int = 10):
        self._max_size: int = max_size
        self._entries: dict[str, EntryValue] = {}
        self._priority: list[EntryValue] = []  # A heap structure
        self._is_vacuuming: bool = False  # FIXME Use a lock
        # TODO add a counter to track eviction, we can run vaccum automatically after a threshold is met

    def add(self, key: str, value: EntryValue, priority: int, expiry: int):
        self._ensure_not_vacuuming()

        entry = Entry(priority=priority, expiry=expiry, value=value, key=key)

        if entry.key in self._entries:
            self.remove(entry)

        if len(self._entries) >= self._max_size:
            self.evict()

        self._entries[entry.key] = entry
        heapq.heappush(self._priority, entry)

    def remove(self, key: str) -> None:
        self._ensure_not_vacuuming()

        if key not in self._entries:
            return

        self._entries[key].is_removed = True
        del self._entries[key]

    def get(self, key: str) -> EntryValue:
        entry: Entry = self._entries.get(key)
        if entry is None:
            return

        return entry.get_value()

    def peek(self, key: str) -> EntryValue:
        return self._entries.get(key)

    def evict(self):
        self._ensure_not_vacuuming()

        if len(self._entries) <= 1:
            return

        # Check if there are multiple entries with the same priority
        entries_w_equal_priority = self._get_entries_with_equal_priority()
        if len(entries_w_equal_priority) == 1:
            entry = entries_w_equal_priority[0]
        else:
            entry = self._select_lru_entry(entries_w_equal_priority)

        # Actual removal
        logger.debug(f"Entry<{entry.key}> is marked as removed")
        entry.is_removed = True
        del self._entries[entry.key]

    def vacuum(self):
        self._is_vacuuming = True

        _new_priority = []
        for entry in self._priority:
            if entry.is_valid():
                heapq.heappush(_new_priority, entry)

        self._priority = _new_priority

        assert len(self._priority) == len(self._entries)

        self._is_vacuuming = False

    def _ensure_not_vacuuming(self):
        if self._is_vacuuming:
            raise RuntimeError("Cache is vacuuming")

    def _select_lru_entry(self, entries: list[Entry]):
        last_used_at = get_timestamp()
        selected_entry = entries[0]

        for entry in entries:
            if not entry.last_used_at:
                selected_entry = entry
                break

            if entry.last_used_at < last_used_at:
                last_used_at = entry.last_used_at
                selected_entry = entry

        return selected_entry

    def _get_entries_with_equal_priority(self):
        peek_ranges = range(2, len(self._priority) + 1)
        entries_w_equal_priority = [self._priority[0]]
        for peek_range in peek_ranges:
            entries_in_range = heapq.nsmallest(peek_range, self._priority)
            if len(set((e.priority for e in entries_in_range))) != 1:  # all priority are equal
                entries_w_equal_priority = heapq.nsmallest(peek_range - 1, self._priority)
                break
            elif peek_range == len(self._priority):  # the whole entries have the same priority
                entries_w_equal_priority = entries_in_range

        return entries_w_equal_priority

    def list_keys(self) -> list[str]:
        return list(self._entries.keys())
