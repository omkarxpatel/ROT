"use client";

import { useMemo } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { oneDark } from "@codemirror/theme-one-dark";
import { EditorView } from "@codemirror/view";

interface EditorProps {
  value: string;
  onChange: (next: string) => void;
}

export function Editor({ value, onChange }: EditorProps) {
  // Memoize the extensions array so CodeMirror doesn't tear down its
  // state on every parent re-render.
  const extensions = useMemo(
    () => [
      EditorView.lineWrapping,
      EditorView.theme({
        "&": { backgroundColor: "transparent" },
        ".cm-gutters": { backgroundColor: "transparent", borderRight: "none" },
        ".cm-activeLineGutter": { backgroundColor: "transparent" },
        ".cm-activeLine": { backgroundColor: "rgba(255,255,255,0.03)" },
      }),
    ],
    [],
  );

  return (
    <div className="h-full w-full">
      <CodeMirror
        value={value}
        height="100%"
        theme={oneDark}
        extensions={extensions}
        onChange={onChange}
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
