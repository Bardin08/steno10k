from __future__ import annotations

from steno10k.stages._pool import run_pool


def test_empty_items_yields_nothing():
    assert list(run_pool([], lambda x: x, concurrency=4)) == []


def test_inline_preserves_order_and_results():
    out = list(run_pool([1, 2, 3], lambda x: x * 10, concurrency=1))
    assert out == [(1, 10, None), (2, 20, None), (3, 30, None)]


def test_inline_captures_error_without_raising():
    def fn(x):
        if x == 2:
            raise ValueError("boom")
        return x

    out = list(run_pool([1, 2, 3], fn, concurrency=1))
    assert out[0] == (1, 1, None)
    item, result, err = out[1]
    assert item == 2 and result is None and isinstance(err, ValueError)
    assert out[2] == (3, 3, None)


def test_pooled_runs_all_items_and_isolates_failure():
    def fn(x):
        if x == 2:
            raise ValueError("boom")
        return x * 10

    out = {item: (result, err) for item, result, err in run_pool([1, 2, 3], fn, concurrency=3)}
    assert out[1] == (10, None)
    assert out[3] == (30, None)
    result, err = out[2]
    assert result is None and isinstance(err, ValueError)
