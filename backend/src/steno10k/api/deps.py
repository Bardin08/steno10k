from __future__ import annotations

from pathlib import Path

from fastapi import Request

from steno10k.api.configsvc import ConfigService
from steno10k.api.runq import RunQueue
from steno10k.api.storage import Storage


def get_storage(request: Request) -> Storage:
    storage: Storage = request.app.state.storage
    return storage


def get_config_service(request: Request) -> ConfigService:
    config_service: ConfigService = request.app.state.config_service
    return config_service


def get_run_queue(request: Request) -> RunQueue:
    run_queue: RunQueue = request.app.state.run_queue
    return run_queue


def get_data_root(request: Request) -> Path:
    data_root: Path = request.app.state.data_root
    return data_root
