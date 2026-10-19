# Transport setup outside the experimental trace

Two successful model-access/isolation handshakes preceded the archived experiment.
They requested the same `gpt-5.6-luna` alias and did not form any participant state,
select the experimental seed, or contribute outcomes to the study records.
They are additional calls beyond the experiment's declared 342-response path.

An earlier attempt using an obsolete CLI was rejected by the service as requiring
a newer CLI. A separate configuration error occurred before a model request.
These setup events are reported separately rather than counted as experimental
observations. The archived run uses the installed official desktop-bundled CLI,
version `0.162.0-alpha.17.2`, and verifies a ChatGPT login. It does not use API-key
billing, extract tokens, or implement an unofficial authentication endpoint.

The complete experimental request/response record is in
`evidence/luna-smoke/calls.jsonl`. The setup handshakes are not included there;
the statement above is an execution note rather than a full raw setup transcript.
The run manifest is authoritative for the experiment's actual completion status.

The transport stores the explicit study instruction template and user payload,
not every instruction or hidden state added by the host or service. CLI-reported
usage includes that broader context. Successful transport checks do not verify
an immutable model-weight identity or provider-level statistical independence.
