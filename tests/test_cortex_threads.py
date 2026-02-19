from support_agent.cortex_agent.rest_client import (
    _extract_assistant_text_from_response,
    _iter_sse_events,
)


def test_iter_sse_events_groups_blocks():
    lines = [
        "event: metadata",
        'data: {"metadata": {"role": "user", "message_id": 123}}',
        "",
        "event: metadata",
        'data: {"metadata": {"role": "assistant", "message_id": 456}}',
        "",
        "event: response",
        'data: {"role": "assistant", "content": [{"type": "text", "text": "Hi"}]}',
        "",
    ]

    events = list(_iter_sse_events(lines))
    assert events[0][0] == "metadata"
    assert '"message_id": 123' in events[0][1]
    assert events[1][0] == "metadata"
    assert '"message_id": 456' in events[1][1]
    assert events[2][0] == "response"


def test_extract_assistant_text_from_response_text_only():
    payload = {
        "role": "assistant",
        "content": [
            {"type": "thinking", "thinking": {"text": "..."}},
            {"type": "text", "text": "Line 1"},
            {"type": "text", "text": "Line 2"},
        ],
    }
    assert _extract_assistant_text_from_response(payload) == "Line 1\nLine 2"
