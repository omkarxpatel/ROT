"use client";

import { useEffect, useMemo, useRef } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { oneDark } from "@codemirror/theme-one-dark";
import {
  HighlightStyle,
  StreamLanguage,
  syntaxHighlighting,
} from "@codemirror/language";
import { StateEffect, StateField } from "@codemirror/state";
import {
  Decoration,
  type DecorationSet,
  EditorView,
} from "@codemirror/view";
import { tags as t } from "@lezer/highlight";

interface EditorProps {
  value: string;
  onChange: (next: string) => void;
  // 1-indexed line number to highlight (the line of the currently-
  // executing top-level statement in animate mode). null disables the
  // highlight; out-of-range values are ignored.
  highlightLine?: number | null;
  // When the parent dispatches a "jump to this position" request (e.g.
  // user clicked a token chip in the Step panel), the editor moves the
  // cursor there and scrolls it into view. `key` increments per
  // request so repeated jumps to the same coordinates still re-fire.
  jumpTo?: { line: number; col: number; key: number } | null;
  // 1-indexed inclusive line range to highlight when the user hovers
  // an AST node in the Step panel. Painted as a subtle sky-blue tint
  // distinct from the amber active-step highlight. null clears it.
  hoverRange?: { startLine: number; endLine: number } | null;
}

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

// Multi-line hover range — painted in a sky-blue tint, distinct from
// the amber "current statement" decoration. Driven externally via the
// `hoverRange` prop; cleared when the parent dispatches null.
const setHoverRange = StateEffect.define<{
  startLine: number;
  endLine: number;
} | null>();

const hoverRangeField = StateField.define<DecorationSet>({
  create() {
    return Decoration.none;
  },
  update(decorations, tr) {
    let next = decorations.map(tr.changes);
    for (const e of tr.effects) {
      if (e.is(setHoverRange)) {
        if (e.value === null) {
          next = Decoration.none;
        } else {
          const start = Math.max(1, e.value.startLine);
          const end = Math.min(e.value.endLine, tr.state.doc.lines);
          const lines = [];
          for (let n = start; n <= end; n++) {
            const line = tr.state.doc.line(n);
            lines.push(
              Decoration.line({ class: "cm-rot-hover-range" }).range(line.from),
            );
          }
          next = Decoration.set(lines);
        }
      }
    }
    return next;
  },
  provide: (f) => EditorView.decorations.from(f),
});

// ─── ROT syntax highlighting ────────────────────────────────────────
// A regex-based StreamLanguage that mirrors the ROT lexer's surface.
// The palette intentionally matches the token-chip palette in
// `tokens-view.tsx` so that source colors and chip colors line up:
//   keyword → purple, identifier → sky, number → cyan, string →
//   amber, operator → rose, punctuation → zinc, comment → zinc-500.
// A user who reads the editor and then watches tokens fly down in
// the Step panel sees the lineage as a color match.

const ROT_KEYWORDS = new Set([
  "funct", "if", "elseif", "else", "while", "for", "return", "let",
  "true", "false", "null", "this", "super", "class", "init", "in",
  "and", "or", "not", "try", "catch", "finally", "throw", "break",
  "continue", "import",
]);

interface RotLexState {
  // Tracks an open f-string spanning lines (rare in ROT but defensive).
  inFString: boolean;
}

const rotLanguage = StreamLanguage.define<RotLexState>({
  startState: () => ({ inFString: false }),
  token(stream) {
    if (stream.eatSpace()) return null;
    // Line comments
    if (stream.match("//")) {
      stream.skipToEnd();
      return "comment";
    }
    // String literals — both regular and f-strings render as one
    // string-colored span. Embedded `{expr}` inside an f-string is
    // not separately colored at this level.
    if (stream.match(/^f"/) || stream.match(/^"/)) {
      while (!stream.eol()) {
        const ch = stream.next();
        if (ch === "\\") {
          stream.next();
          continue;
        }
        if (ch === '"') return "string";
      }
      return "string";
    }
    // Numbers — floats first so `1.5` doesn't tokenize as `1` + `.5`.
    if (stream.match(/^\d+\.\d+/)) return "number";
    if (stream.match(/^\d+/)) return "number";
    // Multi-char operators before single-char.
    if (stream.match(/^(==|!=|<=|>=|\+=|-=|\*=|\/=|%=)/)) return "operator";
    if (stream.match(/^[+\-*/%<>=!]/)) return "operator";
    // Punctuation: braces, brackets, comma, pipe, colon, dot.
    if (stream.match(/^[(){}[\]|,.:;]/)) return "punctuation";
    // Identifiers and keywords.
    if (stream.match(/^[A-Za-z_][A-Za-z0-9_]*/)) {
      const word = stream.current();
      if (ROT_KEYWORDS.has(word)) return "keyword";
      return "variableName";
    }
    // Fallback: consume one char to avoid stalling.
    stream.next();
    return null;
  },
});

const rotHighlight = HighlightStyle.define([
  { tag: t.keyword, color: "#c4b5fd" },        // purple-300
  { tag: t.string, color: "#fcd34d" },         // amber-300
  { tag: t.number, color: "#67e8f9" },         // cyan-300
  { tag: t.variableName, color: "#7dd3fc" },   // sky-300
  { tag: t.operator, color: "#fda4af" },       // rose-300
  { tag: t.punctuation, color: "#d4d4d8" },    // zinc-300
  { tag: t.comment, color: "#71717a", fontStyle: "italic" }, // zinc-500
]);

export function Editor({
  value,
  onChange,
  highlightLine,
  jumpTo,
  hoverRange,
}: EditorProps) {
  const viewRef = useRef<EditorView | null>(null);

  const extensions = useMemo(
    () => [
      EditorView.lineWrapping,
      lineHighlightField,
      hoverRangeField,
      rotLanguage,
      // Listed AFTER oneDark so this style wins on overlapping tags.
      syntaxHighlighting(rotHighlight),
      EditorView.theme({
        "&": { backgroundColor: "transparent" },
        ".cm-gutters": { backgroundColor: "transparent", borderRight: "none" },
        ".cm-activeLineGutter": { backgroundColor: "transparent" },
        ".cm-activeLine": { backgroundColor: "rgba(255,255,255,0.03)" },
        ".cm-rot-current-line": {
          backgroundColor: "rgba(245, 158, 11, 0.22)",
          boxShadow: "inset 3px 0 0 rgba(245, 158, 11, 0.95)",
          animation: "rot-line-pulse 0.85s ease-out",
        },
        "@keyframes rot-line-pulse": {
          "0%": {
            backgroundColor: "rgba(245, 158, 11, 0.55)",
            boxShadow:
              "inset 3px 0 0 rgba(245, 158, 11, 1), 0 0 18px 6px rgba(245, 158, 11, 0.5)",
          },
          "100%": {
            backgroundColor: "rgba(245, 158, 11, 0.22)",
            boxShadow:
              "inset 3px 0 0 rgba(245, 158, 11, 0.95), 0 0 0 0 rgba(245, 158, 11, 0)",
          },
        },
        // Hover-range decoration — sky blue, distinct from the amber
        // current-step line so the two can coexist without confusion.
        ".cm-rot-hover-range": {
          backgroundColor: "rgba(56, 189, 248, 0.12)",
          boxShadow: "inset 2px 0 0 rgba(56, 189, 248, 0.6)",
        },
      }),
    ],
    [],
  );

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    view.dispatch({
      effects: setHighlightLine.of(
        typeof highlightLine === "number" ? highlightLine : null,
      ),
    });
  }, [highlightLine]);

  // Imperative cursor jump on `jumpTo.key` change. Clamps the line
  // and col to document bounds, sets the selection anchor at the
  // resolved position, and scrolls it into view.
  useEffect(() => {
    if (!jumpTo) return;
    const view = viewRef.current;
    if (!view) return;
    const lineNum = Math.max(
      1,
      Math.min(jumpTo.line, view.state.doc.lines),
    );
    const lineInfo = view.state.doc.line(lineNum);
    const col = Math.max(0, jumpTo.col - 1);
    const pos = Math.min(lineInfo.from + col, lineInfo.to);
    view.dispatch({
      selection: { anchor: pos },
      scrollIntoView: true,
    });
    view.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jumpTo?.key]);

  // Hover range — fires whenever the parent's range changes. Cheap to
  // dispatch on every render because we pass through to the state
  // field which diffs decoration sets.
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    view.dispatch({
      effects: setHoverRange.of(hoverRange ?? null),
    });
  }, [hoverRange?.startLine, hoverRange?.endLine, hoverRange]);

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
