# KataX01 - Priority-Expiry LRU Cache

> Disclaimer: the README itself is slightly unorganized

I came across [this blog](https://death.andgravity.com/lru-cache) by Adrian one day about a big tech interview question
to create a priority-expiry LRU cache.

The topic itself is interesting enough that I stopped reading it as soon as I finished the
requirements section and decided to implement my own solution in Python.

First, I tried to come up with a solution on a paper.
My initial solution involves storing the cache entries in a dictionary, and use other data structure to keep track of
the priority of each entry.

Since I'll be using Python, I want to leverage the standard library to minimize the verbosity of the solution.
Eventually, I decided to go with a solution that uses [heapq](https://docs.python.org/3/library/heapq.html)
and [dataclass](https://docs.python.org/3/library/dataclasses.html)

My final solution involves using 2 internal data structures:

1. a dictionary (`_entries`):
    - to keep track of all cache entries
    - entries will be removed from this dictionary as soon as it is marked as removed
2. a list (`_priorities`):
    - that acts like a heap
    - to keep track of the entries' priorities
    - it is managed using `heapq` and the entry with the lowest priority will be the root of the heap

On top of that, each cache entry will be stored along with other metadata in a dataclass called `Entry`.
The dataclass will be storing the priority, expiry timestamp, cache key, as well as the value.
2 additional attributes `is_removed` and `last_used_at` are also added to allow us to mark an entry as removed, and to
keep track of the last read timestamp.

Python allows us to mark a dataclass as sortable, the `Entry` dataclass is marked with `@dataclass(order=True)` so that
they can be ordered based on priority.
Since the entries should only be sorted by priority, all attributes except `priority` are marked
with `= Field(compare=False)`.

As for the priority of entries, larger value signifies higher priority.
This is not the convention we usually see, but it is to ensure that we can
take advantage of utilities provided in `heapq` as it uses a min heap as opposed to max heap.

While evicting an entry or when an entry is explicitly removed, the entry will be marked as removed by setting
its `is_removed` flag.
It will also be removed from the `_entries` but it will remain in the heap until vacuum is triggered.

About data vacuuming, the cache exposes a method `vacuum()` that allows us to explicitly reconstruct the `_priority`
heap and purge removed entries from memory.

In the code, you will come across snippets that mentioned using a lock instead of a boolean flag, or something about
auto-vacuuming.
Those are merely some ideas I have in mind, but didn't spend more time to develop further.

Some test cases are also added to validate that my code works. 