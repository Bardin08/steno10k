from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from steno10k.api.configsvc import ConfigService
from steno10k.api.deps import get_config_service, get_data_root
from steno10k.api.dto import SystemInfoDTO
from steno10k.api.envelope import ok

router = APIRouter(prefix="/api/v1/system", tags=["system"])

WHISPER_MODELS: list[str] = ["tiny", "base", "small", "medium", "large-v3"]


@router.get("")
def get_system_info(
    config_service: Annotated[ConfigService, Depends(get_config_service)],
    data_root: Annotated[Path, Depends(get_data_root)],
) -> dict[str, Any]:
    cfg = config_service.load()
    dto = SystemInfoDTO(
        whisper_models=WHISPER_MODELS,
        current_model=cfg.transcription.model,
        max_workers=cfg.transcription.max_workers,
        data_root=str(data_root),
        llm_key_present=bool(os.environ.get(cfg.llm.api_key_env)),
    )
    return ok(dto.model_dump())
