from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from steno10k.contracts.names import StageName


class AudioConfig(BaseModel):
    chunk_seconds: int = 600
    overlap_seconds: int = 15
    min_chunk_seconds: int = 20
    output_format: str = "m4a"


class TranscriptionConfig(BaseModel):
    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "en"
    max_workers: int = 4
    cpu_threads_per_worker: int = 3


class LLMConfig(BaseModel):
    enabled: bool = True
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = ""
    model: str = ""
    temperature: float = 0.2
    max_tokens: int = 4000
    concurrency: int = 2


class OutputConfig(BaseModel):
    summary_filename: str = "summary.md"
    save_merged_raw_transcript: bool = True
    save_merged_clean_transcript: bool = True
    save_bundle_docx: bool = True


class StagesConfig(BaseModel):
    enabled: dict[StageName, bool] = Field(
        default_factory=lambda: {name: True for name in StageName}
    )

    @field_validator("enabled")
    @classmethod
    def _complete_stage_map(cls, value: dict[StageName, bool]) -> dict[StageName, bool]:
        """Fill omitted stages as enabled so the map always carries every stage.

        A partial map (e.g. only the enabled stages listed) is otherwise read
        with opposite defaults by the two consumers: `run_set` treats a missing
        key as enabled, while `resolve_enabled` treats it as disabled — so a run
        executes more stages than the API's cascade preview reports (issue #39).
        Completing the map here makes both agree; explicit `false` is preserved.
        """
        return {name: value.get(name, True) for name in StageName}


class PromptsConfig(BaseModel):
    language: str = "en"
    target_output_language: str = "en"
    override_dir: str | None = None


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    chat_id: int | None = None


class Config(BaseModel):
    audio: AudioConfig = Field(default_factory=AudioConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    stages: StagesConfig = Field(default_factory=StagesConfig)
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
