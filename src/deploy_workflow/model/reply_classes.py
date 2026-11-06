"""The error classes of a call record whose ``http_status`` is None, defined once.

The writers (loop, handoff executor, Copilot adapter), the exporter and the reader all use this
vocabulary. Any null-status class outside ``SENT_UNKNOWN`` is ``not_sent``: the call never left.
"""

ADAPTER_ERROR = "AdapterError"
ADAPTER_CLOSED = "AdapterClosed"
PRE_SEND_FAILURE = "PreSendFailure"
MODEL_MISMATCH = "ModelMismatch"
BYOK_ROUTED = "ByokRouted"
AUTO_ROUTED = "AutoRouted"
TOOL_CALL_MISMATCH = "ToolCallMismatch"

# Timeouts that may carry the counts of a usage event received before the cut (Copilot).
USAGE_TIMEOUTS: frozenset[str] = frozenset({"IdleTimeout", "OverallTimeout"})

# Classes of a null-status record whose call may have been sent: the charge is unknown or usage-only.
SENT_UNKNOWN: frozenset[str] = USAGE_TIMEOUTS | {
    "ConnectTimeout",
    "TransportError",
    "ToolCallLost",
    ADAPTER_CLOSED,
    ADAPTER_ERROR,
}

# Refusals the Copilot adapter reports itself (status 200): the body parses as an ok turn by design.
ADAPTER_REFUSALS: frozenset[str] = frozenset(
    {MODEL_MISMATCH, BYOK_ROUTED, AUTO_ROUTED, TOOL_CALL_MISMATCH}
)
