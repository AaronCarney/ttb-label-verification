import * as React from "react";
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

export function useBatchStream(batchId: string): BatchStreamState {
  const [state, dispatch] = React.useReducer(_reducer, { events: [], error: null });

  // FRAMING ASSUMPTION (PRD §6.3): each `MessageEvent` carries one whole
  // BatchSSEEvent envelope as JSON in `msg.data`. If E6 instead emits
  // `event:` / `id:` / `retry:` framed multi-line records, attach
  // `addEventListener('label-update', …)` and friends per `event:` name and
  // re-parse here. Test corpus today is single-line `data:` only.
  React.useEffect(() => {
    if (!batchId) return;
    const url = `/batches/${encodeURIComponent(batchId)}/stream`;
    const es = new EventSource(url);
    es.onmessage = (msg) => {
      try {
        const parsed = JSON.parse(msg.data as string) as BatchSSEEvent;
        dispatch({ type: "push", event: parsed });
      } catch {
        dispatch({ type: "error", message: "Malformed SSE payload" });
      }
    };
    es.onerror = () => {
      dispatch({ type: "error", message: "SSE connection error" });
    };
    return () => {
      es.close();
    };
  }, [batchId]);

  return state;
}
