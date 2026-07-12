from __future__ import annotations

import argparse
import re

from steno10k.api.storage import NotFound
from steno10k.cli import output
from steno10k.cli.context import Deps, ExitCode, common_parser

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
        print(str(exc), file=__import__("sys").stderr)
        return ExitCode.USAGE
    return ExitCode.OK


# -- shared ------------------------------------------------------------------


def confirm(assume_yes: bool, prompt: str) -> bool:
    if assume_yes:
        return True
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in {"y", "yes"}
