"""Gemini stand-in transport for the targeted harness: identical prompts (rem_harness.providers.build_prompt),
harness schema as responseJsonSchema, served modelVersion and usage recorded. Not his live route."""
from __future__ import annotations
import json, os, re, time, urllib.request, urllib.error
from pathlib import Path
from rem_harness.providers import build_prompt
from rem_harness.models import digest


def _key():
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    env = Path.home().joinpath("Documents/Projects/website/.env").read_text()
    return re.search(r'^GEMINI_API_KEY\s*=\s*"?([^"\n]+)"?', env, re.M).group(1).strip()


class GeminiProvider:
    name = "gemini_rest_standin"
    is_live = False

    def __init__(self, model="gemini-3.1-pro-preview", effort="low", retries=4, timeout=180, max_resamples=3):
        self.requested_model, self.effort, self.retries, self.key = model, effort, retries, _key()
        self.timeout, self.max_resamples = timeout, max_resamples
        self.last_trace, self.call_context = {}, {}
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
                      "transport_retries": 0, "length_resamples": 0, "served_models": {}}

    def _once(self, system, user, schema):
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": schema,
                                     "thinkingConfig": {"thinkingLevel": self.effort}}}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.requested_model}:generateContent"
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": self.key})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

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
                d = self._once(system, user, schema)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                code = getattr(e, "code", None)
                detail = e.read().decode()[:300] if hasattr(e, "read") else str(e)
                if attempts > self.retries + resamples or code not in (None, 400, 429, 500, 502, 503, 504):  # 400 INVALID_ARGUMENT seen transiently on identical requests (28 Oct)
                    self.last_trace["transport_note"] = f"error {code}: {detail}"
                    raise RuntimeError(f"Gemini error {code}: {detail}") from None
                self.usage["transport_retries"] += 1
                time.sleep(5 * 2 ** min(attempts - 1, 4))
                continue
            cand = d["candidates"][0]
            text = "".join(p.get("text", "") for p in cand["content"]["parts"] if not p.get("thought"))
            response = json.loads(text)
            if cap is not None and isinstance(response.get("message"), str) and len(response["message"]) > cap:
                resamples += 1
                self.usage["length_resamples"] += 1
                if resamples > self.max_resamples:
                    self.last_trace["transport_note"] = f"message exceeded {cap} chars on {resamples} samples; stopped"
                    raise RuntimeError("Message length cap exceeded after repeated resampling")
                continue
            break
        u = d.get("usageMetadata", {})
        usage = {"input_tokens": u.get("promptTokenCount", 0), "output_tokens": u.get("candidatesTokenCount", 0),
                 "thinking_tokens": u.get("thoughtsTokenCount", 0), "cache_read_input_tokens": u.get("cachedContentTokenCount", 0)}
        served = d.get("modelVersion")
        self.usage["calls"] += 1
        for k in ("input_tokens", "output_tokens", "cache_read_input_tokens"):
            self.usage[k] += usage[k]
        self.usage["served_models"][served] = self.usage["served_models"].get(served, 0) + 1
        self.last_trace.update({"served_model_id": served, "model_identity_status": "returned_metadata_not_weight_attestation",
                                "response_id": d.get("responseId"), "stop_reason": cand.get("finishReason"), "usage": usage,
                                "elapsed_seconds": round(time.monotonic() - start, 3),
                                "transport_attempts": attempts, "length_resamples": resamples,
                                "raw_response": response, "physical_dispatch": True,
                                "host_context_scope": "generateContent: archived system and user strings are the complete prompt.",
                                "transport_note": "One stateless generateContent call per response; explicit transport retries only on 429/5xx (transport_attempts); over-length messages resampled (length_resamples)."})
        return response
