"use client";

import { useEffect, useMemo, useRef } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { oneDark } from "@codemirror/theme-one-dark";
import { StateEffect, StateField } from "@codemirror/state";
import {
  Decoration,
  type DecorationSet,
  EditorView,
} from "@codemirror/view";

interface EditorProps {
  value: string;
  onChange: (next: string) => void;
  // 1-indexed line number to highlight (the line of the currently-
  // executing top-level statement in animate mode). null disables the
  // highlight; out-of-range values are ignored.
  highlightLine?: number | null;
}

// A `StateEffect` whose payload is the line number (or null to clear).
// A `StateField` listens for the effect and converts it into a line
// decoration. CodeMirror plumbing for "highlight one line, externally
// driven" is enough boilerplate that it lives in this file rather than
// inline in the component body.
const setHighlightLine = StateEffect.define<number | null>();

const lineHighlightField = StateField.define<DecorationSet>({
  create() {
    return Decoration.none;
  },
  update(decorations, tr) {
    let next = decorations.map(tr.changes);
    for (const e of tr.effects) {
      if (e.is(setHighlightLine)) {
        if (e.value === null) {
          next = Decoration.none;
        } else if (e.value >= 1 && e.value <= tr.state.doc.lines) {
          const line = tr.state.doc.line(e.value);
          next = Decoration.set([
            Decoration.line({ class: "cm-rot-current-line" }).range(line.from),
          ]);
        }
      }
    }
    return next;
  },
  provide: (f) => EditorView.decorations.from(f),
});

export function Editor({ value, onChange, highlightLine }: EditorProps) {
  const viewRef = useRef<EditorView | null>(null);

  const extensions = useMemo(
    () => [
      EditorView.lineWrapping,
      lineHighlightField,
      EditorView.theme({
        "&": { backgroundColor: "transparent" },
        ".cm-gutters": { backgroundColor: "transparent", borderRight: "none" },
        ".cm-activeLineGutter": { backgroundColor: "transparent" },
        ".cm-activeLine": { backgroundColor: "rgba(255,255,255,0.03)" },
        // Step-mode current-statement highlight. Amber accent so it
        // reads distinctly from the regular cursor-active line. Border
        // on the gutter mirrors the row so it's visible even when the
        // line is empty.
        ".cm-rot-current-line": {
          backgroundColor: "rgba(245, 158, 11, 0.14)",
          boxShadow: "inset 2px 0 0 rgba(245, 158, 11, 0.7)",
        },
      }),
    ],
    [],
  );

  // Dispatch the highlight effect whenever the prop changes. Guarded
  // against the view not being created yet; once created, the ref is
  // stable for the editor's lifetime.
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    view.dispatch({
      effects: setHighlightLine.of(
        typeof highlightLine === "number" ? highlightLine : null,
      ),
    });
  }, [highlightLine]);

  return (
    <div className="h-full w-full">
      <CodeMirror
        value={value}
        height="100%"
        theme={oneDark}
        extensions={extensions}
        onChange={onChange}
        onCreateEditor={(view) => {
          viewRef.current = view;
        }}
        basicSetup={{
          lineNumbers: true,
          highlightActiveLine: true,
          highlightActiveLineGutter: true,
          foldGutter: false,
          autocompletion: false,
        }}
      />
    </div>
  );
}
