"""Inspeção desacoplada do Kernel (SDK interno + recorder)."""

from __future__ import annotations

from kernel.inspect.recorder import (
    PipelineRecord,
    PipelineRecorder,
    get_recorder,
    reset_recorder_for_tests,
)
from kernel.inspect.sdk import (
    context as inspect_context,
    disciplines as inspect_disciplines,
    memory_session as inspect_memory_session,
    metrics as inspect_metrics,
    models as inspect_models,
    pipeline as inspect_pipeline,
    prompt as inspect_prompt,
    rag as inspect_rag,
    rag_config as inspect_rag_config,
    rag_query as inspect_rag_query,
    system as inspect_system,
)

__all__ = [
    "PipelineRecord",
    "PipelineRecorder",
    "get_recorder",
    "reset_recorder_for_tests",
    "inspect_context",
    "inspect_disciplines",
    "inspect_memory_session",
    "inspect_metrics",
    "inspect_models",
    "inspect_pipeline",
    "inspect_prompt",
    "inspect_rag",
    "inspect_rag_config",
    "inspect_rag_query",
    "inspect_system",
]
