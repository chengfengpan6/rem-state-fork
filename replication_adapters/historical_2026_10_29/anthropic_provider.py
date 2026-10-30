"""Stand-in transport for Chengfeng's targeted REM harness: identical system text, instruction
text and v2 payload encoding (rem_harness.providers.build_prompt), sent to a Claude model through
the official Anthropic SDK with the harness's own JSON schema as a structured-output constraint.
is_live is False so the harness treats this as a stand-in, not his gpt-5.6-luna live route.
Second-provider replication of the instrument, not a result about gpt-5.6-luna."""
from __future__ import annotations
import json, time
import anthropic
from rem_harness.providers import build_prompt
from rem_harness.models import digest

STRIP = {"minimum", "maximum", "minItems", "maxItems", "exclusiveMinimum", "exclusiveMaximum"}


def api_schema(schema):
    """The Messages API structured-output grammar rejects numeric bounds and array sizes; drop them for the
    API only. maxLength is accepted but not enforced. The harness validates every response against the
    full schema (rem_harness.schemas.validate_response); over-length messages are resampled (counted)."""
    if isinstance(schema, dict):
        return {k: api_schema(v) for k, v in schema.items() if k not in STRIP}
    if isinstance(schema, list):
        return [api_schema(v) for v in schema]
    return schema


RETRYABLE = (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.APITimeoutError,
             anthropic.InternalServerError)


class ClaudeProvider:
    name = "anthropic_api_standin"
    is_live = False

    def __init__(self, model="claude-opus-5-5", effort="low", retries=4, timeout=180.0, max_resamples=3):
        self.requested_model, self.effort, self.retries, self.max_resamples = model, effort, retries, max_resamples
        self.client = anthropic.Anthropic(timeout=timeout, max_retries=0)  # retries are explicit and recorded
        self.last_trace, self.call_context = {}, {}
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
                      "transport_retries": 0, "length_resamples": 0, "served_models": {}}

    def _once(self, system, user, schema):
        return self.client.messages.create(
            model=self.requested_model, max_tokens=4096, system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": api_schema(schema)}})

    def complete(self, kind, payload, schema):
        system, user = build_prompt(kind, payload, schema)
        cap = schema.get("properties", {}).get("message", {}).get("maxLength")
        self.last_trace = {"provider": self.name, "requested_model": self.requested_model, "effort": self.effort,
                           "system_template": system, "user_prompt": user, "schema_sha256": digest(schema),
                           "physical_dispatch": False}
        start, attempts, resamples = time.monotonic(), 0, 0
        while True:
            attempts += 1
            try:
                self.last_trace["physical_dispatch"] = True
                r = self._once(system, user, schema)
            except RETRYABLE as e:
                if attempts > self.retries + resamples:
                    self.last_trace["transport_note"] = f"gave up after {attempts} attempts: {type(e).__name__}"
                    raise
                self.usage["transport_retries"] += 1
                time.sleep(5 * 2 ** min(attempts - 1, 4))
                continue
            if r.stop_reason == "refusal":
                self.last_trace["transport_note"] = "refusal stop reason; run stopped, no retry"
                raise RuntimeError("Claude declined the request (stop_reason=refusal)")
            text = next(b.text for b in r.content if b.type == "text")
            response = json.loads(text)
            if cap is not None and isinstance(response.get("message"), str) and len(response["message"]) > cap:
                resamples += 1
                self.usage["length_resamples"] += 1
                if resamples > self.max_resamples:
                    self.last_trace["transport_note"] = f"message exceeded {cap} chars on {resamples} samples; stopped"
                    raise RuntimeError("Message length cap exceeded after repeated resampling")
                continue
            break
        u = r.usage
        usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                 "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
                 "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0}
        self.usage["calls"] += 1
        for k in ("input_tokens", "output_tokens", "cache_read_input_tokens"):
            self.usage[k] += usage[k]
        self.usage["served_models"][r.model] = self.usage["served_models"].get(r.model, 0) + 1
        self.last_trace.update({
            "served_model_id": r.model, "model_identity_status": "returned_metadata_not_weight_attestation",
            "response_id": r.id, "stop_reason": r.stop_reason, "usage": usage,
            "elapsed_seconds": round(time.monotonic() - start, 3),
            "transport_attempts": attempts, "length_resamples": resamples,
            "raw_response": response, "physical_dispatch": True,
            "api_schema_note": "numeric bounds and array sizes stripped for the API grammar; full schema enforced by the harness validator",
            "host_context_scope": "Messages API: the archived system and user strings are the complete prompt; no host-added context.",
            "transport_note": "One stateless Messages API call per response; thinking at the stated effort, not archived; "
                              "explicit transport retries only on 429/5xx/connection errors (transport_attempts); "
                              "over-length messages resampled (length_resamples)."})
        return response
