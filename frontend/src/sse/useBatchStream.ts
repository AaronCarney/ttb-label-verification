import * as React from "react";
import type { DispositionEnvelope } from "../types/envelopes";
import type { BatchSSEEvent } from "../types/sse";

export interface BatchStreamState {
  events: BatchSSEEvent[];
  error: string | null;
}

type _Action =
  | { type: "push"; event: BatchSSEEvent }
  | { type: "error"; message: string }
  | { type: "reset" };

function _reducer(state: BatchStreamState, action: _Action): BatchStreamState {
  switch (action.type) {
    case "push":
      if (state.events.some((e) => e.label_ref === action.event.label_ref)) {
        return state;
      }
      return { ...state, events: [...state.events, action.event] };
    case "error":
      return { ...state, error: action.message };
    case "reset":
      return { events: [], error: null };
  }
}

// E6 emits named SSE events per ARCH §5.2: label-result, anomaly-advisory,
// stream-end (worker), and override-applied (override endpoint).
// Per D-PE6-03 (post-E6 followups L2 plan), E7 consumes only label-result +
// stream-end; the others are not surfaced in the current UI.
export function useBatchStream(batchId: string): BatchStreamState {
  const [state, dispatch] = React.useReducer(_reducer, { events: [], error: null });

  React.useEffect(() => {
    if (!batchId) return;
    const url = `/batches/${encodeURIComponent(batchId)}/stream`;
    const es = new EventSource(url);

    const _onLabelResult = (msg: MessageEvent) => {
      try {
        const wrapped = JSON.parse(msg.data as string) as {
          batch_id: string;
          queue_position: number;
          envelope: DispositionEnvelope;
        };
        const flat: BatchSSEEvent = {
          ...wrapped.envelope,
          batch_id: wrapped.batch_id,
          queue_position: wrapped.queue_position,
        };
        dispatch({ type: "push", event: flat });
      } catch {
        dispatch({ type: "error", message: "Malformed SSE payload" });
      }
    };
    const _onStreamEnd = () => es.close();

    es.addEventListener("label-result", _onLabelResult);
    es.addEventListener("stream-end", _onStreamEnd);
    es.onerror = () => dispatch({ type: "error", message: "SSE connection error" });

    return () => {
      es.removeEventListener("label-result", _onLabelResult);
      es.removeEventListener("stream-end", _onStreamEnd);
      es.close();
    };
  }, [batchId]);

  return state;
}
