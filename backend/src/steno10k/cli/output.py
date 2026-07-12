from __future__ import annotations

import json as _json
from typing import Any

from steno10k.api.dto import ProjectDTO, RecordingDTO, SetDTO
from steno10k.contracts.config import Config
from steno10k.contracts.domain import Project, Recording, RecordingSet


def _dump(obj: Any) -> None:
    print(_json.dumps(obj, indent=2))


def emit_projects(projects: list[Project], *, as_json: bool) -> None:
    if as_json:
        _dump([ProjectDTO.from_domain(p).model_dump() for p in projects])
        return
    if not projects:
        print("(no projects)")
        return
    for p in projects:
        icon = f" [{p.icon}]" if p.icon else ""
        print(f"{p.slug:24} {p.title}{icon}  ({len(p.sets)} sets)")


def emit_project(project: Project, *, as_json: bool) -> None:
    if as_json:
        _dump(ProjectDTO.from_domain(project).model_dump())
        return
    print(project.slug)


def emit_sets(sets: list[RecordingSet], *, as_json: bool) -> None:
    if as_json:
        _dump([SetDTO.from_domain(s).model_dump() for s in sets])
        return
    if not sets:
        print("(no sets)")
        return
    for s in sets:
        print(f"{s.slug:24} {s.title}  ({len(s.recordings)} recordings)")


def emit_set(s: RecordingSet, *, as_json: bool) -> None:
    if as_json:
        _dump(SetDTO.from_domain(s).model_dump())
        return
    print(s.slug)


def emit_recordings(recordings: list[Recording], *, as_json: bool) -> None:
    if as_json:
        _dump([RecordingDTO.from_domain(r).model_dump() for r in recordings])
        return
    if not recordings:
        print("(no recordings)")
        return
    for r in recordings:
        print(f"{r.normalized_name:32} <- {r.source_name}")


def emit_status(s: RecordingSet, artifacts: list[str], *, as_json: bool) -> None:
    if as_json:
        payload = SetDTO.from_domain(s).model_dump()
        payload["artifacts"] = artifacts
        _dump(payload)
        return
    print(f"{s.project_slug}/{s.slug}  {s.title}")
    print("recordings:")
    for r in s.recordings:
        print(f"  {r.normalized_name}")
    print("stages:")
    for name, status in s.stages.items():
        print(f"  {name:12} {status}")
    print("artifacts:")
    for a in artifacts:
        print(f"  {a}")


def emit_config(cfg: Config, llm_key_present: bool, *, as_json: bool) -> None:
    if as_json:
        _dump({"config": cfg.model_dump(mode="json"), "llm_key_present": llm_key_present})
        return
    import yaml  # local import: only the human path needs a yaml dump

    print(yaml.safe_dump(cfg.model_dump(mode="json"), sort_keys=False), end="")
    print(f"llm_key_present: {llm_key_present}")
