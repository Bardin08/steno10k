from __future__ import annotations

from steno10k.contracts.status import StageStatus
from steno10k.stages.summarize import SummarizeStage
from tests.stages.support import FakeLLM, make_ctx


def _seed_merged_clean(set_dir, text: str) -> None:
    d = set_dir / "merged"
    d.mkdir(parents=True, exist_ok=True)
    (d / "clean_transcript.md").write_text(text, encoding="utf-8")


def test_name_and_deps():
    stage = SummarizeStage()
    assert stage.name == "summarize"
    assert stage.depends_on == ["merge", "clean"]


def test_writes_summary_from_merged_clean(set_dir):
    _seed_merged_clean(set_dir, "the full clean transcript")
    llm = FakeLLM(lambda system, user: f"SUMMARY of: {user}")
    ctx = make_ctx(set_dir, llm=llm)

    result = SummarizeStage().run(ctx)

    assert result.status == StageStatus.OK
    summary = (set_dir / "summary.md").read_text(encoding="utf-8")
    assert summary == "SUMMARY of: the full clean transcript\n"
    system, user = llm.calls[0]
    assert "en" in system and user == "the full clean transcript"


def test_target_language_is_formatted_into_prompt(set_dir):
    _seed_merged_clean(set_dir, "text")
    llm = FakeLLM()
    ctx = make_ctx(set_dir, llm=llm)
    ctx.cfg.prompts.target_output_language = "French"

    SummarizeStage().run(ctx)

    system, _user = llm.calls[0]
    assert "French" in system
    assert "{target_output_language}" not in system


def test_custom_summary_filename(set_dir):
    _seed_merged_clean(set_dir, "text")
    ctx = make_ctx(set_dir, llm=FakeLLM(lambda s, u: "S"))
    ctx.cfg.output.summary_filename = "notes.md"

    SummarizeStage().run(ctx)

    assert (set_dir / "notes.md").exists()
    assert not (set_dir / "summary.md").exists()


def test_missing_transcript_fails(set_dir):
    ctx = make_ctx(set_dir, llm=FakeLLM())
    result = SummarizeStage().run(ctx)
    assert result.status == StageStatus.FAILED
    assert ctx.errors.count == 1


def test_empty_transcript_fails(set_dir):
    _seed_merged_clean(set_dir, "   ")
    ctx = make_ctx(set_dir, llm=FakeLLM())
    result = SummarizeStage().run(ctx)
    assert result.status == StageStatus.FAILED


def test_idempotent_skip_unless_force(set_dir):
    _seed_merged_clean(set_dir, "text")
    (set_dir / "summary.md").write_text("EXISTING", encoding="utf-8")

    ctx = make_ctx(set_dir, llm=FakeLLM(lambda s, u: "NEW"))
    result = SummarizeStage().run(ctx)
    assert (set_dir / "summary.md").read_text(encoding="utf-8") == "EXISTING"
    assert result.stats.get("skipped") == 1

    ctx_force = make_ctx(set_dir, force=True, llm=FakeLLM(lambda s, u: "NEW"))
    SummarizeStage().run(ctx_force)
    assert (set_dir / "summary.md").read_text(encoding="utf-8") == "NEW\n"


def test_no_llm_client_skips(set_dir):
    _seed_merged_clean(set_dir, "text")
    ctx = make_ctx(set_dir, llm=None)
    assert SummarizeStage().run(ctx).status == StageStatus.SKIPPED
