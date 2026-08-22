import asyncio

from kernel.providers.aggregate import aggregate_sse
from kernel.schemas.chat import confidence_to_float


async def _fake_stream():
    yield 'data: [ACL_META]{"confidence":"high","sources":["db:x"]}\n\n'
    yield "data: Olá\\nmundo\n\n"
    yield "data: [DONE]\n\n"


def test_aggregate_sse_parses_meta_and_text() -> None:
    answer, meta = asyncio.run(aggregate_sse(_fake_stream()))
    assert answer == "Olá\nmundo"
    assert meta["confidence"] == "high"
    assert meta["sources"] == ["db:x"]


def test_confidence_mapping() -> None:
    assert confidence_to_float("high") == 0.95
    assert confidence_to_float("medium") == 0.7
    assert confidence_to_float("low") == 0.4
    assert confidence_to_float("nope") == 0.4
