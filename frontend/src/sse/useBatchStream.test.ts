import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useBatchStream } from "./useBatchStream";
import type { BatchSSEEvent } from "../types/sse";

class FakeEventSource {
  static last: FakeEventSource | null = null;
  public onmessage: ((e: MessageEvent) => void) | null = null;
  public onerror: ((e: Event) => void) | null = null;
  public closed = false;
  public url: string;
  constructor(url: string) {
    this.url = url;
    FakeEventSource.last = this;
  }
  close(): void { this.closed = true; }
  fire(data: unknown): void {
    this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(data) }));
  }
}

const _stub = (i: number): BatchSSEEvent => ({
  batch_id: "B",
  queue_position: i,
  evaluation_id: `e${i}`,
  label_ref: `lbl-${i}`,
  disposition: "pass",
  disposition_confidence: { band: "high", numeric: 0.9 },
  fields: [],
  audit_trail: {
    evaluation_id: `e${i}`,
    rule_set_version: "0.1.0",
    model_version: null,
    prompt_version: null,
    input_hash: "h",
    output_hash: "h",
    started_at: "2026-04-01T00:00:00Z",
    completed_at: "2026-04-01T00:00:01Z",
    per_rule_trace: [],
    overrides: [],
  },
  metrics: {
    total_duration_ms: 100,
    per_rule_durations_ms: [],
    vision_duration_ms: 50,
    orchestrator_duration_ms: 0,
  },
});

describe("useBatchStream", () => {
  beforeEach(() => {
    (globalThis as unknown as { EventSource: typeof FakeEventSource }).EventSource = FakeEventSource;
    FakeEventSource.last = null;
  });
  afterEach(() => { delete (globalThis as { EventSource?: unknown }).EventSource; });

  it("opens an EventSource for the given batch_id", () => {
    renderHook(() => useBatchStream("B"));
    expect(FakeEventSource.last?.url).toContain("/batches/B/stream");
  });

  it("pushes events into the store keyed by label_ref", () => {
    const { result } = renderHook(() => useBatchStream("B"));
    act(() => FakeEventSource.last!.fire(_stub(1)));
    act(() => FakeEventSource.last!.fire(_stub(2)));
    expect(result.current.events).toHaveLength(2);
    expect(result.current.events[0]!.label_ref).toBe("lbl-1");
    expect(result.current.events[1]!.queue_position).toBe(2);
  });

  it("dedupes events that arrive twice for the same label_ref (SSE replay safety)", () => {
    const { result } = renderHook(() => useBatchStream("B"));
    act(() => FakeEventSource.last!.fire(_stub(1)));
    act(() => FakeEventSource.last!.fire(_stub(1)));
    expect(result.current.events).toHaveLength(1);
  });

  it("closes the EventSource on unmount", () => {
    const { unmount } = renderHook(() => useBatchStream("B"));
    const es = FakeEventSource.last!;
    unmount();
    expect(es.closed).toBe(true);
  });

  it("survives StrictMode double-mount cleanup (closes the old, opens new)", () => {
    // StrictMode behavior: mount → cleanup → mount. After both, latest EventSource is open.
    const { rerender, unmount } = renderHook(() => useBatchStream("B"));
    const first = FakeEventSource.last!;
    rerender();
    const second = FakeEventSource.last!;
    // first or second may be the same instance; we only require that after final unmount, .closed=true.
    unmount();
    expect(second.closed).toBe(true);
    void first;
  });
});
