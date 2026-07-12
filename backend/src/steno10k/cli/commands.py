from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

from steno10k.api.storage import NotFound
from steno10k.cli import output
from steno10k.cli.context import Deps, ExitCode, common_parser, load_config
from steno10k.contracts.domain import Recording
from steno10k.lib.ingest import SUPPORTED_EXTENSIONS, normalized_filename

_ICON_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def validate_icon(value: str) -> str:
    """Accept a Phosphor icon name (kebab-case); reject emoji and other non-names."""
    if not _ICON_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid icon name {value!r}: use a Phosphor icon name in kebab-case "
            "(e.g. 'book', 'wave-sine'); emoji are not allowed"
        )
    return value


# -- projects ----------------------------------------------------------------


def add_projects(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = sub.add_parser("projects", help="manage projects")
    psub = p.add_subparsers(dest="projects_cmd", required=True)

    lst = psub.add_parser("list", parents=[common_parser()], help="list projects")
    lst.set_defaults(func=cmd_projects_list)

    cr = psub.add_parser("create", parents=[common_parser()], help="create a project")
    cr.add_argument("title")
    cr.add_argument(
        "--icon", type=validate_icon, default=None, help="Phosphor icon name (never emoji)"
    )
    cr.set_defaults(func=cmd_projects_create)

    dl = psub.add_parser("delete", parents=[common_parser()], help="delete a project")
    dl.add_argument("project")
    dl.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    dl.set_defaults(func=cmd_projects_delete)


def cmd_projects_list(args: argparse.Namespace, deps: Deps) -> int:
    output.emit_projects(deps.storage.list_projects(), as_json=deps.json)
    return ExitCode.OK


def cmd_projects_create(args: argparse.Namespace, deps: Deps) -> int:
    project = deps.storage.create_project(args.title, icon=args.icon)
    output.emit_project(project, as_json=deps.json)
    return ExitCode.OK


def cmd_projects_delete(args: argparse.Namespace, deps: Deps) -> int:
    if not confirm(args.yes, f"Delete project {args.project!r} and all its data?"):
        return ExitCode.OK
    try:
        deps.storage.delete_project(args.project)
    except NotFound as exc:
        print(str(exc), file=sys.stderr)
        return ExitCode.USAGE
    return ExitCode.OK


# -- sets --------------------------------------------------------------------


def add_sets(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = sub.add_parser("sets", help="manage recording sets")
    ssub = p.add_subparsers(dest="sets_cmd", required=True)

    lst = ssub.add_parser("list", parents=[common_parser()], help="list sets in a project")
    lst.add_argument("project")
    lst.set_defaults(func=cmd_sets_list)

    cr = ssub.add_parser("create", parents=[common_parser()], help="create a set")
    cr.add_argument("project")
    cr.add_argument("title")
    cr.set_defaults(func=cmd_sets_create)

    dl = ssub.add_parser("delete", parents=[common_parser()], help="delete a set")
    dl.add_argument("project")
    dl.add_argument("set_", metavar="SET")
    dl.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    dl.set_defaults(func=cmd_sets_delete)


def cmd_sets_list(args: argparse.Namespace, deps: Deps) -> int:
    try:
        deps.storage.get_project(args.project)
    except NotFound as exc:
        print(str(exc), file=sys.stderr)
        return ExitCode.USAGE
    output.emit_sets(deps.storage.list_sets(args.project), as_json=deps.json)
    return ExitCode.OK


def cmd_sets_create(args: argparse.Namespace, deps: Deps) -> int:
    try:
        s = deps.storage.create_set(args.project, args.title)
    except NotFound as exc:
        print(str(exc), file=sys.stderr)
        return ExitCode.USAGE
    output.emit_set(s, as_json=deps.json)
    return ExitCode.OK


def cmd_sets_delete(args: argparse.Namespace, deps: Deps) -> int:
    if not confirm(args.yes, f"Delete set {args.project}/{args.set_!r} and all its data?"):
        return ExitCode.OK
    try:
        deps.storage.delete_set(args.project, args.set_)
    except NotFound as exc:
        print(str(exc), file=sys.stderr)
        return ExitCode.USAGE
    return ExitCode.OK


# -- import ------------------------------------------------------------------


def add_import(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = sub.add_parser("import", parents=[common_parser()], help="import audio files into a set")
    p.add_argument("project")
    p.add_argument("set_", metavar="SET")
    p.add_argument("files", nargs="+", metavar="FILE")
    p.set_defaults(func=cmd_import)


def cmd_import(args: argparse.Namespace, deps: Deps) -> int:
    try:
        deps.storage.get_set(args.project, args.set_)
    except NotFound as exc:
        print(str(exc), file=sys.stderr)
        return ExitCode.USAGE
    set_dir = deps.storage.set_dir(args.project, args.set_)

    sources = [Path(f) for f in args.files]
    for src in sources:
        if src.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(f"unsupported file type: {src.name}", file=sys.stderr)
            return ExitCode.USAGE
        if not src.is_file():
            print(f"file not found: {src}", file=sys.stderr)
            return ExitCode.USAGE

    existing = {p.name for p in set_dir.iterdir()}
    recordings: list[Recording] = []
    for src in sources:
        norm = normalized_filename(src.name, existing)
        existing.add(norm)
        shutil.copyfile(src, set_dir / norm)
        recordings.append(Recording(source_name=src.name, normalized_name=norm))

    deps.storage.add_recordings(args.project, args.set_, recordings)
    output.emit_recordings(recordings, as_json=deps.json)
    return ExitCode.OK


# -- recordings --------------------------------------------------------------


def add_recordings(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = sub.add_parser("recordings", help="manage recordings in a set")
    rsub = p.add_subparsers(dest="recordings_cmd", required=True)

    lst = rsub.add_parser("list", parents=[common_parser()], help="list recordings in a set")
    lst.add_argument("project")
    lst.add_argument("set_", metavar="SET")
    lst.set_defaults(func=cmd_recordings_list)

    rm = rsub.add_parser("rm", parents=[common_parser()], help="remove a recording from a set")
    rm.add_argument("project")
    rm.add_argument("set_", metavar="SET")
    rm.add_argument("recording", help="normalized recording filename")
    rm.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    rm.set_defaults(func=cmd_recordings_rm)


def cmd_recordings_list(args: argparse.Namespace, deps: Deps) -> int:
    try:
        s = deps.storage.get_set(args.project, args.set_)
    except NotFound as exc:
        print(str(exc), file=sys.stderr)
        return ExitCode.USAGE
    output.emit_recordings(s.recordings, as_json=deps.json)
    return ExitCode.OK


def cmd_recordings_rm(args: argparse.Namespace, deps: Deps) -> int:
    prompt = f"Remove recording {args.recording!r} from {args.project}/{args.set_}?"
    if not confirm(args.yes, prompt):
        return ExitCode.OK
    try:
        deps.storage.remove_recording(args.project, args.set_, args.recording)
    except NotFound as exc:
        print(str(exc), file=sys.stderr)
        return ExitCode.USAGE
    return ExitCode.OK


# -- status ------------------------------------------------------------------


def add_status(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = sub.add_parser(
        "status",
        parents=[common_parser()],
        help="show a set's recordings, stages, artifacts",
    )
    p.add_argument("project")
    p.add_argument("set_", metavar="SET")
    p.set_defaults(func=cmd_status)


def cmd_status(args: argparse.Namespace, deps: Deps) -> int:
    try:
        s = deps.storage.get_set(args.project, args.set_)
    except NotFound as exc:
        print(str(exc), file=sys.stderr)
        return ExitCode.USAGE
    set_dir = deps.storage.set_dir(args.project, args.set_)
    recorded = {r.normalized_name for r in s.recordings}
    artifacts = sorted(
        f.name
        for f in set_dir.iterdir()
        if f.is_file() and f.name not in recorded and f.name != "manifest.json"
    )
    output.emit_status(s, artifacts, as_json=deps.json)
    return ExitCode.OK


# -- config ------------------------------------------------------------------


def add_config(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = sub.add_parser("config", help="inspect configuration")
    csub = p.add_subparsers(dest="config_cmd", required=True)
    show = csub.add_parser("show", parents=[common_parser()], help="print resolved config")
    show.set_defaults(func=cmd_config_show)


def cmd_config_show(args: argparse.Namespace, deps: Deps) -> int:
    cfg = load_config(deps)
    llm_key_present = bool(os.environ.get(cfg.llm.api_key_env))
    output.emit_config(cfg, llm_key_present, as_json=deps.json)
    return ExitCode.OK


# -- shared ------------------------------------------------------------------


def confirm(assume_yes: bool, prompt: str) -> bool:
    if assume_yes:
        return True
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in {"y", "yes"}
