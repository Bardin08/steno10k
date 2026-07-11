from __future__ import annotations

from steno10k.contracts.status import StageStatus
from steno10k.stages.merge import MergeStage
from tests.stages.support import make_ctx, make_manifest, seed_clean, seed_raw


def test_name_and_deps():
    stage = MergeStage()
    assert stage.name == "merge"
    assert stage.depends_on == ["transcribe"]


def test_merges_raw_and_clean(set_dir):
    seed_raw(set_dir, "rec-1", ["raw a", "raw b"])
    seed_clean(set_dir, "rec-1", ["clean a", "clean b"])
    ctx = make_ctx(set_dir, manifest=make_manifest(["rec-1.m4a"]))

    result = MergeStage().run(ctx)

    assert result.status == StageStatus.OK
    raw_md = (set_dir / "merged" / "raw_transcript.md").read_text(encoding="utf-8")
    clean_md = (set_dir / "merged" / "clean_transcript.md").read_text(encoding="utf-8")
    assert "## rec-1" in raw_md and "### chunk_000" in raw_md
    assert "raw a" in raw_md and "raw b" in raw_md
    assert "clean a" in clean_md and "clean b" in clean_md


def test_raw_only_when_clean_disabled(set_dir):
    seed_raw(set_dir, "rec-1", ["only raw"])
    ctx = make_ctx(set_dir)
    ctx.cfg.output.save_merged_clean_transcript = False

    result = MergeStage().run(ctx)

    assert (set_dir / "merged" / "raw_transcript.md").exists()
    assert not (set_dir / "merged" / "clean_transcript.md").exists()
    assert result.stats == {"raw": 1, "clean": 0}


def test_recording_order_follows_manifest(set_dir):
    seed_raw(set_dir, "b-rec", ["from b"])
    seed_raw(set_dir, "a-rec", ["from a"])
    ctx = make_ctx(set_dir, manifest=make_manifest(["b-rec.m4a", "a-rec.m4a"]))

    MergeStage().run(ctx)

    raw_md = (set_dir / "merged" / "raw_transcript.md").read_text(encoding="utf-8")
    assert raw_md.index("## b-rec") < raw_md.index("## a-rec")


def test_unreadable_chunk_skipped_without_orphan_header(set_dir):
    seed_raw(set_dir, "rec-1", ["good chunk"])  # writes chunk_000.txt
    bad = set_dir / "transcripts_raw" / "rec-1" / "chunk_001.txt"
    bad.write_bytes(b"\xff\xfe\xff")  # invalid UTF-8 -> read fails
    ctx = make_ctx(set_dir)

    result = MergeStage().run(ctx)

    raw_md = (set_dir / "merged" / "raw_transcript.md").read_text(encoding="utf-8")
    assert "### chunk_000" in raw_md and "good chunk" in raw_md
    assert "### chunk_001" not in raw_md  # no orphan header for the unreadable chunk
    assert ctx.errors.count == 1
    assert result.stats["raw"] == 1


def test_no_inputs_writes_nothing(set_dir):
    ctx = make_ctx(set_dir)
    result = MergeStage().run(ctx)
    assert not (set_dir / "merged" / "raw_transcript.md").exists()
    assert result.stats == {"raw": 0, "clean": 0}
