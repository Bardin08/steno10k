from __future__ import annotations

from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_pool[T, R](
    items: list[T],
    fn: Callable[[T], R],
    concurrency: int,
) -> Iterator[tuple[T, R | None, Exception | None]]:
    """Run `fn(item)` over `items`, yielding `(item, result, error)` per item.

    `fn` is caller-supplied (LLM call + file I/O), so any failure is reported as
    the third tuple element rather than raised — one bad item cannot kill the pool.
    `concurrency <= 1` runs inline, preserving input order; otherwise a bounded
    `ThreadPoolExecutor` runs up to `concurrency` at once (completion order).
    """
    if not items:
        return
    if concurrency <= 1:
        for it in items:
            try:
                yield it, fn(it), None
            except Exception as e:  # isolation: one bad item must not kill the pool
                yield it, None, e
        return
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {ex.submit(fn, it): it for it in items}
        for fut in as_completed(futures):
            it = futures[fut]
            try:
                yield it, fut.result(), None
            except Exception as e:  # isolation: one bad item must not kill the pool
                yield it, None, e
