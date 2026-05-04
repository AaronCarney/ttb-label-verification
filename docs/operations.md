# Operations Triage Cookbook

Log-grep recipes for diagnosing the deployed demo (HF Spaces). Logs are
emitted as JSON-line stdout via `OtelGenAIFormatter` (one record per line,
keys per ARCH §13.1).

## Structured fields you can rely on

Every record carries `ts`, `level`, `msg`, `logger`. The `OtelGenAIFormatter`
whitelist also passes through (when the call site sets them):

| Field | Set by |
|---|---|
| `batch_id` | batch + worker + override + SSE call sites |
| `evaluation_id` | evaluator + override + worker per-label |
| `label_id` | worker per-label, override apply |
| `reason_code` | every call site (defaults to `ENGINE.OK.NONE` on success) |
| `duration_ms` | worker per-label + per-batch, evaluator |
| `error_class` | exception sites |
| `model_version`, `prompt_version`, `rule_set_version` | startup |
| `gen_ai.*` | LLM call sites |

Anything outside that whitelist is dropped silently — if you don't see a
field, it's because the call site wasn't told to emit it.

## Recipes

### "Did the batch even arrive?"

```
grep batch_accepted        # ← landed: msg has agent_id, items, lookahead_k
grep batch_submit_conflict # ← duplicate batch_id (409)
```

Absent both → request never reached the app; check HF Space logs for the HTTP
layer or the route-mount.

### "SSE stream looks stuck / empty"

The full lifecycle, in order:

```
batch_accepted        batch_id=<X>
batch_consume_started batch_id=<X> items=N lookahead_k=K
batch_stream_subscribed batch_id=<X> replay=R subscribers=S
label_result          batch_id=<X> pos=0 disposition=… duration_ms=…
…
batch_consume_finished batch_id=<X> items=N duration_ms=…
batch_stream_closed   batch_id=<X> events=E terminated=true
```

Diagnoses:

| Pattern | Meaning |
|---|---|
| `batch_consume_started` present, no `label_result` | evaluator hung; check next recipe |
| `label_result` events present, `batch_stream_subscribed` absent | UI never connected — front-end SSE wiring or CORS |
| `batch_stream_closed terminated=false` | client disconnected mid-stream (network / tab close) |
| `batch_stream_closed terminated=true` and `events=N` matches `items + 1` | clean end |
| `batch_stream_bus_missing` | bus registry torn down (lifespan shutdown raced the request) |

### "Engine failed on a label"

```
grep engine_failure_routed
```

The `reason_code` tells you where:

| reason_code | Stage |
|---|---|
| `ENGINE.EXTRACTION.UNAVAILABLE` | vision (cloud or paddle) raised |
| `ENGINE.RULES.UNAVAILABLE` | rule engine raised |
| `ENGINE.MODEL.UNAVAILABLE` | orchestrator (LLM) raised |
| `ENGINE.SLA.TIMEOUT` | whole-eval exceeded the per-call SLA |
| `INELIGIBLE.QUALITY.*` | legibility short-circuit (not a failure — by design) |
| `ENGINE.WORKER.UNHANDLED` | exception escaped the evaluator into the worker (rare; full traceback) |

`error_class` carries the Python exception class name when applicable.

### "Override didn't apply"

```
grep override_rejected_unknown_code  # 400 — reason_code not in registry
grep override_rejected_not_found     # 404 — evaluation_id not in any in-flight result
grep override_applied                # 200 — msg has the disposition transition
grep override_registry_loaded        # one-shot at first POST; if absent on first request, registry didn't load
```

If `override_registry_loaded` is absent on first request, the working
directory at process start probably didn't include `rules/reason_codes.yaml`
— verify the container's `WORKDIR` and that `rules/` is copied in.

### "Performance feels off"

Each `label_result` carries `duration_ms` (per-label evaluator wall clock).
`batch_consume_finished` carries the batch-wide `duration_ms`. The NFR-PERF
budget for first-label is set in the L1 plan; the perf canary test
(`tests/test_first_label_perf_canary.py`) holds the regression line.

```
# Slowest 10 labels in a session
grep label_result | jq -r '"\(.duration_ms)\t\(.batch_id)\t\(.label_id)"' | sort -rn | head
```

### "Anomaly fired during a batch"

```
grep anomaly_advisory
```

Carries `advisory_id`, `count`, `window`, and the cluster's `reason_code` —
the same advisory is also broadcast on the SSE stream as `anomaly-advisory`.

### "App came up cleanly"

```
grep app_startup     # versions: model_version, prompt_version, rule_set_version
grep app_shutdown    # eviction counts: evicted_batches, evicted_buses
```

`app_startup` should land within the first second of process boot. If
`rule_set_version` is `0.0.0` after E2 has loaded, the rule-pack loader
didn't fire — boot order regression.

## Greppable event-name index

```
app_startup               app_shutdown
healthz_invoked
batch_accepted            batch_submit_conflict
batch_snapshot_not_found  batch_stream_not_found       batch_stream_bus_missing
batch_stream_subscribed   batch_stream_closed
batch_consume_started     batch_consume_finished
label_result              label_evaluation_failed
anomaly_advisory          batch_producer_failed
override_registry_loaded  override_rejected_unknown_code
override_rejected_not_found                            override_applied
engine_failure_routed
```

These names are stable identifiers — point dashboards and alerts at them
rather than at substring fragments of the `msg` field.

## Secrets check

Per ARCH §12.4 / NFR-SEC-004 the redaction filter strips known content
fields before emission, but the simplest belt-and-braces grep before
sharing logs is:

```
grep -E "sk-[A-Za-z0-9]{20,}|Bearer |X-Api-Key" <log-file>
```

Should return nothing. If it doesn't, halt and audit the offending call
site.
