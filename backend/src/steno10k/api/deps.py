from __future__ import annotations

from fastapi import Request

from steno10k.api.configsvc import ConfigService
from steno10k.api.storage import Storage


def get_storage(request: Request) -> Storage:
    storage: Storage = request.app.state.storage
    return storage


def get_config_service(request: Request) -> ConfigService:
    config_service: ConfigService = request.app.state.config_service
    return config_service
