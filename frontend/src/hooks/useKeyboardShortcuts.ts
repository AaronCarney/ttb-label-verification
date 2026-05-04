import * as React from "react";

export interface KeyboardShortcuts {
  onOverride?: () => void;
  onNext?: () => void;
  onPrev?: () => void;
  onEscape?: () => void;
  onEnter?: () => void;
}

function _isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (target.isContentEditable) return true;
  return false;
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcuts): void {
  const ref = React.useRef(shortcuts);
  React.useEffect(() => {
    ref.current = shortcuts;
  }, [shortcuts]);

  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (_isTypingTarget(e.target)) return;
      const { onOverride, onNext, onPrev, onEscape, onEnter } = ref.current;
      switch (e.key) {
        case "o":
        case "O":
          if (onOverride) {
            e.preventDefault();
            onOverride();
          }
          break;
        case "j":
        case "J":
          if (onNext) {
            e.preventDefault();
            onNext();
          }
          break;
        case "k":
        case "K":
          if (onPrev) {
            e.preventDefault();
            onPrev();
          }
          break;
        case "Escape":
          if (onEscape) onEscape();
          break;
        case "Enter":
          if (onEnter) onEnter();
          break;
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);
}
