import * as React from "react";
import { createRoot } from "react-dom/client";
import "./tokens/globals.css";
import { AISuggestionBlock } from "./components/AISuggestionBlock";
import { ConfidenceIndicator } from "./components/ConfidenceIndicator";
import { DispositionPill } from "./components/DispositionPill";
import { EvidencePanel } from "./components/EvidencePanel";
import { FieldCard } from "./components/FieldCard";
import { LiveRegion } from "./components/LiveRegion";
import { NeedsBetterPhotoCard } from "./components/NeedsBetterPhotoCard";
import { OverrideDrawer } from "./components/OverrideDrawer";
import { RawJSONDrawer } from "./components/RawJSONDrawer";
import { RuleVerdict } from "./components/RuleVerdict";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";
import type { DispositionEnvelope } from "./types/envelopes";

// A minimal hard-coded reason-code catalog mirrors rules/reason_codes.yaml.
// E7 ships a small subset; E8 (or a build step) can generate the full set.
//
// ORDER INVARIANT (FR-803 — 3-keystroke override path):
// For each fixture's canonical reason code, this array's FIRST entry that
// shares the same starting letter MUST be that canonical code. The picker
// (T20) auto-selects only when filter narrows to length === 1; otherwise
// ENTER picks `filtered[highlight]` and `highlight` resets to 0 on filter
// change. Combined, that means `O → <letter> → ENTER` lands on the first
// code with that prefix in this array.
//
// Canonical paths verified:
//  - fixture-03 (WARNING.STYLE.HEADING_NOT_BOLD_CAPS): 'w' → highlight 0
//    among 3 W-prefixed codes ↑ — this entry must stay at position 0
//    among W-prefixed entries.
//
// Reorder this array only after re-verifying T30's keyboard test still
// passes. T20 does not assert this invariant; future readers, see also
// the `tests/manual/a11y-smoke.md` step 7 narration.
const _REASON_CODES = [
  { code: "BRAND.NAME.MISMATCH", description: "Brand mismatch" },
  { code: "BRAND.NAME.NEEDS_REVIEW", description: "Brand needs review" },
  { code: "WARNING.STYLE.HEADING_NOT_BOLD_CAPS", description: "Heading not bold caps" },
  { code: "WARNING.LEGIBILITY.LOW_RESOLUTION", description: "Low resolution" },
  { code: "WARNING.LEGIBILITY.GLARE", description: "Glare" },
  { code: "ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND", description: "ABV out of band" },
  { code: "CLASS_TYPE.SOI.NO_MATCH", description: "Class/Type SOI mismatch" },
];

function SingleApp({ envelope }: { envelope: DispositionEnvelope | null }): React.JSX.Element {
  const [overrideOpen, setOverrideOpen] = React.useState(false);
  const [announcement, setAnnouncement] = React.useState("");
  useKeyboardShortcuts({
    onOverride: () => setOverrideOpen(true),
    onEscape: () => setOverrideOpen(false),
  });

  if (!envelope) {
    return (
      <div className="p-4">
        <p>No envelope. Submit a label via <code>POST /labels</code>.</p>
      </div>
    );
  }

  const isNeedsBetterPhoto = envelope.fields.some((f) =>
    f.rule_findings.some((rf) => rf.reason_code.startsWith("WARNING.LEGIBILITY.")),
  );

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">{envelope.label_ref}</h2>
          <p className="font-mono text-xs text-muted-foreground">{envelope.evaluation_id}</p>
        </div>
        <div className="flex items-center gap-3">
          <DispositionPill disposition={envelope.disposition} />
          <ConfidenceIndicator
            band={envelope.disposition_confidence.band}
            numeric={envelope.disposition_confidence.numeric}
          />
          <RawJSONDrawer enabled={document.body.dataset.devMode === "1"} payload={envelope} />
        </div>
      </header>

      {isNeedsBetterPhoto && (
        <NeedsBetterPhotoCard
          reasonCode={envelope.fields[0]!.rule_findings[0]!.reason_code}
          applicantMessage="Please re-submit a higher-resolution photo (≥300 DPI) of the front label."
        />
      )}

      <div className="grid grid-cols-1 gap-4">
        {envelope.fields.map((field) => (
          <FieldCard
            key={field.field_name}
            field={field}
            verdict={field.rule_findings[0] ? <RuleVerdict finding={field.rule_findings[0]} /> : null}
            aiSuggestion={<AISuggestionBlock suggestion={field.ai_suggestion} />}
          />
        ))}
      </div>

      <OverrideDrawer
        open={overrideOpen}
        onOpenChange={setOverrideOpen}
        codes={_REASON_CODES}
        onSubmit={(p) => {
          setAnnouncement(`Override saved: ${p.reasonCode}`);
          setOverrideOpen(false);
        }}
      />
      <LiveRegion message={announcement} />
      <EvidencePanelStub />
    </div>
  );
}

// Small inline placeholder so the module pulls EvidencePanel into the bundle
// for the production runtime; a future task wires citation chip → evidence panel.
function EvidencePanelStub(): React.JSX.Element {
  const [open, setOpen] = React.useState(false);
  void open;
  return (
    <EvidencePanel
      open={false}
      onOpenChange={setOpen}
      citation=""
      regulationText=""
      evidenceText=""
    />
  );
}

function _readEnvelope(): DispositionEnvelope | null {
  const tag = document.getElementById("envelope");
  if (!tag) return null;
  try {
    return JSON.parse(tag.textContent ?? "null") as DispositionEnvelope | null;
  } catch {
    return null;
  }
}

// Exported so the unit test can call it explicitly per-test (Vitest caches
// modules — relying on the auto-mount side effect would render only on the
// first `it` block). Production code path uses the auto-mount below.
export function mount(): void {
  const root = document.getElementById("root");
  if (!root) return;
  const envelope = _readEnvelope();
  createRoot(root).render(
    <React.StrictMode>
      <SingleApp envelope={envelope} />
    </React.StrictMode>,
  );
  root.setAttribute("data-mounted", "true");
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
}
