from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from steno10k.api.configsvc import ConfigService
from steno10k.api.deps import get_config_service, get_data_root
from steno10k.api.dto import Envelope
from steno10k.api.envelope import ApiError, ok
from steno10k.lib.prompts import PROMPT_NAMES, default_prompt

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])


class PromptDTO(BaseModel):
    name: str
    source: str  # "default" | "override"
    content: str


class PromptUpdate(BaseModel):
    content: str


def _override_dir(config_service: ConfigService, data_root: Path) -> Path:
    cfg = config_service.load()
    override_dir = cfg.prompts.override_dir
    return Path(override_dir) if override_dir else data_root / "prompt_overrides"


def _override_path(config_service: ConfigService, data_root: Path, name: str) -> Path:
    return _override_dir(config_service, data_root) / f"{name}.md"


def _dto(config_service: ConfigService, data_root: Path, name: str) -> PromptDTO:
    override_path = _override_path(config_service, data_root, name)
    if override_path.is_file():
        content = override_path.read_text(encoding="utf-8")
        return PromptDTO(name=name, source="override", content=content)
    return PromptDTO(name=name, source="default", content=default_prompt(name))


def _require_known(name: str) -> None:
    if name not in PROMPT_NAMES:
        raise ApiError(404, "prompt_not_found", f"prompt not found: {name}")


@router.get("", response_model=Envelope[list[PromptDTO]])
def list_prompts(
    config_service: Annotated[ConfigService, Depends(get_config_service)],
    data_root: Annotated[Path, Depends(get_data_root)],
) -> dict[str, Any]:
    return ok([_dto(config_service, data_root, name).model_dump() for name in sorted(PROMPT_NAMES)])


@router.put("/{name}", response_model=Envelope[PromptDTO])
def put_prompt(
    name: str,
    body: PromptUpdate,
    config_service: Annotated[ConfigService, Depends(get_config_service)],
    data_root: Annotated[Path, Depends(get_data_root)],
) -> dict[str, Any]:
    _require_known(name)
    override_path = _override_path(config_service, data_root, name)
    override_path.parent.mkdir(parents=True, exist_ok=True)
    override_path.write_text(body.content, encoding="utf-8")
    return ok(_dto(config_service, data_root, name).model_dump())


@router.post("/{name}/reset", response_model=Envelope[PromptDTO])
def reset_prompt(
    name: str,
    config_service: Annotated[ConfigService, Depends(get_config_service)],
    data_root: Annotated[Path, Depends(get_data_root)],
) -> dict[str, Any]:
    _require_known(name)
    override_path = _override_path(config_service, data_root, name)
    override_path.unlink(missing_ok=True)
    return ok(_dto(config_service, data_root, name).model_dump())
