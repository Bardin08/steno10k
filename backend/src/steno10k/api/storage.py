from __future__ import annotations

import json
import shutil
from pathlib import Path

from steno10k.contracts.domain import Project, Recording, RecordingSet
from steno10k.contracts.ids import new_id
from steno10k.contracts.manifest import Manifest
from steno10k.contracts.slug import resolve_collision, slugify

_PROJECT_FILE = "project.json"
_MANIFEST_FILE = "manifest.json"


class NotFound(Exception):
    """Raised when a requested project or set does not exist on disk."""


class Storage:
    """Filesystem repository over `<data_root>/<project-slug>/<set-slug>/`."""

    def __init__(self, data_root: Path) -> None:
        self._root = data_root

    @property
    def data_root(self) -> Path:
        return self._root

    # -- projects ----------------------------------------------------------

    def create_project(self, title: str) -> Project:
        existing = {p.name for p in self._root.iterdir()} if self._root.is_dir() else set()
        slug = resolve_collision(existing, slugify(title))
        project_dir = self._root / slug
        project_dir.mkdir(parents=True, exist_ok=True)
        project = Project(slug=slug, title=title, id=new_id())
        self._save_project(project)
        return project

    def list_projects(self) -> list[Project]:
        if not self._root.is_dir():
            return []
        projects = []
        for entry in sorted(self._root.iterdir()):
            if (entry / _PROJECT_FILE).is_file():
                projects.append(self.get_project(entry.name))
        return projects

    def get_project(self, slug: str) -> Project:
        project_file = self._root / slug / _PROJECT_FILE
        if not project_file.is_file():
            raise NotFound(f"project not found: {slug}")
        raw = json.loads(project_file.read_text(encoding="utf-8"))
        project = Project(slug=raw["slug"], title=raw["title"], id=raw["id"])
        project.sets = self.list_sets(slug)
        return project

    def delete_project(self, slug: str) -> None:
        project_dir = self._root / slug
        if not (project_dir / _PROJECT_FILE).is_file():
            raise NotFound(f"project not found: {slug}")
        shutil.rmtree(project_dir)

    def _save_project(self, project: Project) -> None:
        project_file = self._root / project.slug / _PROJECT_FILE
        project_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"id": project.id, "slug": project.slug, "title": project.title}
        project_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # -- sets ----------------------------------------------------------

    def create_set(self, project_slug: str, title: str) -> RecordingSet:
        project_dir = self._root / project_slug
        if not (project_dir / _PROJECT_FILE).is_file():
            raise NotFound(f"project not found: {project_slug}")
        existing = {p.name for p in project_dir.iterdir() if p.is_dir()}
        slug = resolve_collision(existing, slugify(title))
        manifest = Manifest(project_slug=project_slug, set_slug=slug, title=title)
        manifest.save(self.set_dir(project_slug, slug) / _MANIFEST_FILE)
        return self.get_set(project_slug, slug)

    def list_sets(self, project_slug: str) -> list[RecordingSet]:
        project_dir = self._root / project_slug
        if not project_dir.is_dir():
            return []
        sets = []
        for entry in sorted(project_dir.iterdir()):
            if entry.is_dir() and (entry / _MANIFEST_FILE).is_file():
                sets.append(self.get_set(project_slug, entry.name))
        return sets

    def get_set(self, project_slug: str, set_slug: str) -> RecordingSet:
        manifest_file = self.set_dir(project_slug, set_slug) / _MANIFEST_FILE
        if not manifest_file.is_file():
            raise NotFound(f"set not found: {project_slug}/{set_slug}")
        manifest = Manifest.load(manifest_file)
        return RecordingSet(
            slug=set_slug,
            title=manifest.title,
            project_slug=project_slug,
            id=manifest.id,
            recordings=manifest.recordings,
            stages={str(k): v for k, v in manifest.stages.items()},
        )

    def delete_set(self, project_slug: str, set_slug: str) -> None:
        set_dir = self.set_dir(project_slug, set_slug)
        if not (set_dir / _MANIFEST_FILE).is_file():
            raise NotFound(f"set not found: {project_slug}/{set_slug}")
        shutil.rmtree(set_dir)

    def add_recordings(self, project_slug: str, set_slug: str, recordings: list[Recording]) -> None:
        manifest_file = self.set_dir(project_slug, set_slug) / _MANIFEST_FILE
        if not manifest_file.is_file():
            raise NotFound(f"set not found: {project_slug}/{set_slug}")
        manifest = Manifest.load(manifest_file)
        manifest.recordings.extend(recordings)
        manifest.save(manifest_file)

    def remove_recording(self, project_slug: str, set_slug: str, normalized_name: str) -> None:
        manifest_file = self.set_dir(project_slug, set_slug) / _MANIFEST_FILE
        if not manifest_file.is_file():
            raise NotFound(f"set not found: {project_slug}/{set_slug}")
        manifest = Manifest.load(manifest_file)
        remaining = [r for r in manifest.recordings if r.normalized_name != normalized_name]
        if len(remaining) == len(manifest.recordings):
            raise NotFound(f"recording not found: {project_slug}/{set_slug}/{normalized_name}")
        manifest.recordings = remaining
        manifest.save(manifest_file)
        recording_file = self.set_dir(project_slug, set_slug) / normalized_name
        if recording_file.is_file():
            recording_file.unlink()

    def set_dir(self, project_slug: str, set_slug: str) -> Path:
        return self._root / project_slug / set_slug

    def manifest_path(self, project_slug: str, set_slug: str) -> Path:
        return self.set_dir(project_slug, set_slug) / _MANIFEST_FILE

    def load_manifest(self, project_slug: str, set_slug: str) -> Manifest:
        manifest_file = self.manifest_path(project_slug, set_slug)
        if not manifest_file.is_file():
            raise NotFound(f"set not found: {project_slug}/{set_slug}")
        return Manifest.load(manifest_file)
