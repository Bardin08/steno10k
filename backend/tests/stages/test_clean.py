from __future__ import annotations

from pathlib import Path

from stages.support import FakeLLM, make_ctx, make_manifest, seed_raw
from steno10k.contracts.stage import RunOptions
from steno10k.contracts.status import StageStatus
from steno10k.stages.clean import CleanStage


def test_name_and_deps() -> None:
    stage = CleanStage()
    assert stage.name == "clean"
    assert stage.depends_on == ["transcribe"]


def test_enabled_gates_on_llm_and_skip_llm() -> None:
    from steno10k.contracts.config import Config

    stage = CleanStage()
    cfg = Config()
    assert stage.enabled(cfg, RunOptions()) is True
    assert stage.enabled(cfg, RunOptions(skip_llm=True)) is False
    cfg.llm.enabled = False
    assert stage.enabled(cfg, RunOptions()) is False


def test_cleans_each_chunk_via_llm(set_dir: Path) -> None:
    seed_raw(set_dir, "rec-1", ["hello raw", "second chunk"])
    llm = FakeLLM(lambda system, user: f"CLEANED::{user}")
    ctx = make_ctx(set_dir, manifest=make_manifest(["rec-1.m4a"]), llm=llm)

    result = CleanStage().run(ctx)

    assert result.status == StageStatus.OK
    assert result.stats["cleaned"] == 2
    d = set_dir / "transcripts_clean" / "rec-1"
    assert (d / "chunk_000.md").read_text(encoding="utf-8") == "CLEANED::hello raw"
    assert (d / "chunk_001.md").read_text(encoding="utf-8") == "CLEANED::second chunk"
    assert all(sys_ and "transcript" in sys_.lower() for sys_, _user in llm.calls)


def test_empty_raw_writes_empty_clean_without_llm_call(set_dir: Path) -> None:
    seed_raw(set_dir, "rec-1", ["   "])
    llm = FakeLLM()
    ctx = make_ctx(set_dir, llm=llm)

    CleanStage().run(ctx)

    path = set_dir / "transcripts_clean" / "rec-1" / "chunk_000.md"
    assert path.read_text(encoding="utf-8") == ""
    assert llm.calls == []


def test_idempotent_skip_unless_force(set_dir: Path) -> None:
    seed_raw(set_dir, "rec-1", ["raw"])
    dst = set_dir / "transcripts_clean" / "rec-1" / "chunk_000.md"
    dst.parent.mkdir(parents=True)
    dst.write_text("EXISTING", encoding="utf-8")

    ctx = make_ctx(set_dir, llm=FakeLLM(lambda s, u: "NEW"))
    result = CleanStage().run(ctx)
    assert dst.read_text(encoding="utf-8") == "EXISTING"
    assert result.stats["skipped"] == 1

    ctx_force = make_ctx(set_dir, force=True, llm=FakeLLM(lambda s, u: "NEW"))
    CleanStage().run(ctx_force)
    assert dst.read_text(encoding="utf-8") == "NEW"


def test_failed_chunk_logged_and_isolated(set_dir: Path) -> None:
    seed_raw(set_dir, "rec-1", ["good", "bad"])

    def responder(system: str, user: str) -> str:
        if user == "bad":
            raise RuntimeError("model exploded")
        return f"ok:{user}"

    ctx = make_ctx(set_dir, llm=FakeLLM(responder))
    ctx.cfg.llm.concurrency = 1
    result = CleanStage().run(ctx)

    assert result.status == StageStatus.OK
    assert result.stats["cleaned"] == 1
    assert result.stats["failed"] == 1
    assert ctx.errors.count == 1
    assert (set_dir / "transcripts_clean" / "rec-1" / "chunk_000.md").exists()
    assert not (set_dir / "transcripts_clean" / "rec-1" / "chunk_001.md").exists()


def test_no_llm_client_skips(set_dir: Path) -> None:
    seed_raw(set_dir, "rec-1", ["raw"])
    ctx = make_ctx(set_dir, llm=None)
    result = CleanStage().run(ctx)
    assert result.status == StageStatus.SKIPPED
