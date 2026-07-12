from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from steno10k.api.configsvc import ConfigService
from steno10k.api.deps import get_config_service
from steno10k.api.dto import Envelope, PutConfigResult
from steno10k.api.envelope import ok
from steno10k.api.stages import STAGE_DEPS
from steno10k.contracts.config import Config

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("", response_model=Envelope[Config])
def get_config(
    config_service: Annotated[ConfigService, Depends(get_config_service)],
) -> dict[str, Any]:
    cfg = config_service.load()
    return ok(cfg.model_dump(mode="json"))


@router.put("", response_model=Envelope[PutConfigResult])
def put_config(
    body: Config, config_service: Annotated[ConfigService, Depends(get_config_service)]
) -> dict[str, Any]:
    config_service.save(body)
    _enabled, cascaded = config_service.resolve(body, STAGE_DEPS)
    return ok(
        {
            "config": body.model_dump(mode="json"),
            "cascaded_off": sorted(str(name) for name in cascaded),
        }
    )


@router.get("/defaults", response_model=Envelope[Config])
def get_defaults() -> dict[str, Any]:
    return ok(Config().model_dump(mode="json"))
