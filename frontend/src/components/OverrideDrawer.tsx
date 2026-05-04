import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import * as React from "react";
import { cn } from "../lib/cn";
import { ReasonCodePicker, type ReasonCodeEntry } from "./ReasonCodePicker";

export interface OverrideSubmitPayload {
  reasonCode: string;
  justification: string;
}

export interface OverrideDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  codes: ReasonCodeEntry[];
  onSubmit: (payload: OverrideSubmitPayload) => void;
  className?: string;
}

export function OverrideDrawer({
  open,
  onOpenChange,
  codes,
  onSubmit,
  className,
}: OverrideDrawerProps): React.JSX.Element {
  const [selectedCode, setSelectedCode] = React.useState<string | null>(null);
  const [justification, setJustification] = React.useState("");

  React.useEffect(() => {
    if (!open) {
      setSelectedCode(null);
      setJustification("");
    }
  }, [open]);

  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Enter" && selectedCode) {
        e.preventDefault();
        onSubmit({ reasonCode: selectedCode, justification });
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, selectedCode, justification, onSubmit]);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/50" />
        <Dialog.Content
          aria-describedby="override-help"
          className={cn(
            "fixed right-0 top-0 z-50 flex h-full w-[min(560px,90vw)] flex-col gap-4 bg-background p-6 shadow-lg",
            className,
          )}
        >
          <header className="flex items-center justify-between">
            <Dialog.Title className="text-lg font-semibold">Override disposition</Dialog.Title>
            <Dialog.Close aria-label="Close" className="rounded-md p-1 hover:bg-muted">
              <X aria-hidden className="h-5 w-5" />
            </Dialog.Close>
          </header>
          <p id="override-help" className="text-sm text-muted-foreground">
            Type a reason-code prefix. The picker resolves on the first keystroke
            when the prefix is unique. Press <kbd>Enter</kbd> to submit.
          </p>
          <ReasonCodePicker codes={codes} onSelect={setSelectedCode} />
          {selectedCode && (
            <p className="rounded-md border border-border bg-muted p-2 text-sm">
              Selected: <span className="font-mono">{selectedCode}</span>
            </p>
          )}
          <label className="text-sm">
            Justification (optional)
            <textarea
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-md border border-border bg-background p-2 text-sm focus-visible:ring-2 focus-visible:ring-ring"
            />
          </label>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="rounded-md border border-border px-3 py-1 text-sm hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={!selectedCode}
              onClick={() => selectedCode && onSubmit({ reasonCode: selectedCode, justification })}
              className="rounded-md bg-primary px-3 py-1 text-sm text-primary-foreground disabled:opacity-50"
            >
              Submit override
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
