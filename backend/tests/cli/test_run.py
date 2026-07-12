from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from steno10k.cli import run as run_mod
from steno10k.cli.app import main
from steno10k.contracts.config import Config
from steno10k.contracts.names import StageName
from steno10k.contracts.registry import StageRegistry
from steno10k.contracts.stage import RunOptions, StageContext, StageResult
from steno10k.contracts.status import StageStatus


@dataclass
class _StubStage:
    name: StageName
    status: StageStatus
    depends_on: list[StageName] = field(default_factory=list)

    def enabled(self, cfg: Config, opts: RunOptions) -> bool:
        return True

    def run(self, ctx: StageContext) -> StageResult:
        return StageResult(status=self.status)


def _seed_set(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> list[str]:
    root = ["--data-root", str(tmp_path)]
    main(["projects", "create", "Bio", *root])
    main(["sets", "create", "bio", "L1", *root])
    capsys.readouterr()
    return root


def test_run_success_exits_0(  # type: ignore[no-untyped-def]
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    root = _seed_set(tmp_path, capsys)
    reg = StageRegistry([_StubStage(StageName.NORMALIZE, StageStatus.OK)])
    monkeypatch.setattr(run_mod, "build_registry", lambda: reg)

    assert main(["run", "bio", "l1", *root]) == 0
    out = capsys.readouterr().out
    assert "normalize" in out


def test_run_stage_failure_exits_1(  # type: ignore[no-untyped-def]
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    root = _seed_set(tmp_path, capsys)
    reg = StageRegistry([_StubStage(StageName.NORMALIZE, StageStatus.FAILED)])
    monkeypatch.setattr(run_mod, "build_registry", lambda: reg)

    assert main(["run", "bio", "l1", *root]) == 1


def test_run_unknown_set_exits_2(tmp_path: Path) -> None:
    assert main(["run", "nope", "nope", "--data-root", str(tmp_path)]) == 2


def test_run_maps_run_options(  # type: ignore[no-untyped-def]
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    root = _seed_set(tmp_path, capsys)
    captured: dict[str, RunOptions] = {}

    def _fake_execute(deps, project, set_, opts, *, registry=None, verbose=False, as_json=False):  # type: ignore[no-untyped-def]
        captured["opts"] = opts
        return 0

    monkeypatch.setattr(run_mod, "execute_run", _fake_execute)

    assert main(["run", "bio", "l1", "--from", "transcribe", "--skip-llm", "--force", *root]) == 0
    opts = captured["opts"]
    assert opts.from_stage is StageName.TRANSCRIBE
    assert opts.skip_llm is True
    assert opts.force is True
    assert opts.only is None


def test_run_only_and_from_are_mutually_exclusive(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _seed_set(tmp_path, capsys)
    with pytest.raises(SystemExit) as exc:
        main(["run", "bio", "l1", "--only", "chunk", "--from", "merge", *root])
    assert exc.value.code == 2
