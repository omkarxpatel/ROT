# ROT Playground (web)

A browser-only playground for the [ROT programming language](https://github.com/omkarxpatel/ROT). Write `.rot` code in the editor, click **Run**, and watch the lex → parse → interpret pipeline run live. Everything executes in your browser via [Pyodide](https://pyodide.org/) — there is no backend.

## Layout

```
+--------------------------------------------------------+
|  ROT Playground          v2.25.x   [Examples ▾]  [Run] |
+--------------------------------------+-----------------+
|                                      |  Output         |
|  Code editor (CodeMirror)            |                 |
|                                      +-----------------+
|                                      |  Pipeline       |
|                                      |  ▾ Tokens       |
|                                      |  ▾ AST          |
|                                      |  ▾ Trace        |
+--------------------------------------+-----------------+
```

## Tech stack

- Next.js 15 (App Router) + React 19 + TypeScript (strict)
- Tailwind CSS 3 + shadcn/ui (Button, Card, Select, Accordion, ScrollArea)
- CodeMirror 6 via `@uiw/react-codemirror` with the One Dark theme
- Framer Motion for the pipeline animations
- Pyodide 0.27 loaded from the JSDelivr CDN

## How ROT runs in the browser

The `rot/` Python package lives one directory up (`../rot/`). At build/dev time, `scripts/copy-rot.mjs` copies every `rot/*.py` into `public/rot_package/` and every `examples/*.rot` into `public/rot_examples/`. On the first **Run** click, the runtime:

1. Injects the Pyodide loader script from JSDelivr (~10MB cold; cached after).
2. Fetches `/rot_package/manifest.json`, then each `.py` listed, and writes them into Pyodide's virtual filesystem under `/rot/`.
3. `import rot` works inside Pyodide; a small Python bridge (`rot_compile_and_run(source)`) lex/parse/interprets the code, captures stdout, and returns a JSON dict (tokens, AST, output, error, timings).

Subsequent runs re-use the cached Pyodide instance — only the first run pays the cold-start cost.

## Local development

```bash
cd web
npm install            # one-time
npm run dev            # http://localhost:3000
```

The `predev` / `prebuild` hooks run `scripts/copy-rot.mjs` automatically, so `public/rot_package/` and `public/rot_examples/` are kept in sync with `../rot/` and `../examples/`. Re-run `npm run dev` (or just `node scripts/copy-rot.mjs`) after editing files outside of `web/`.

## Build & deploy

```bash
npm run build          # static-ish .next build
npm run start          # serve the production build locally
```

Deploys to Vercel with zero config — just point the project at `web/` as the root directory and Vercel's Next.js preset will do the rest. There is no backend; Vercel serves the Next.js output and Pyodide pulls everything else from the CDN.

```bash
# from inside web/:
vercel deploy
```

## Conventions

- TypeScript strict mode.
- No emojis in UI strings.
- Pyodide is loaded lazily on the first Run click — the page is usable (editor renders, examples can be browsed) even if Pyodide fails to load. Errors surface in the Output pane.
- The site is intentionally a thin shell over the real `rot/` package — there is no copy of ROT's logic in JS. Whatever the Python interpreter does, the playground does.

## Files of interest

```
src/app/page.tsx                  # the playground layout
src/lib/pyodide-runtime.ts        # Pyodide loader + Python bridge
src/lib/examples.ts               # example metadata + fetcher
src/components/editor.tsx         # CodeMirror wrapper
src/components/pipeline-panel.tsx # tokens + AST + trace
src/components/output-panel.tsx   # stdout + error rendering
scripts/copy-rot.mjs              # build-time copy of ../rot/ -> public/
```

## Known limitations

- Pyodide cold-start is ~3–6s on a typical connection. After the first run, subsequent runs execute in single-digit milliseconds for small programs.
- No ROT-specific syntax highlighting yet — the editor is generic text with line numbers.
- AST serialization uses `dataclasses.asdict` recursively; cyclic structures (none in ROT today) would break.
- The trace pane is a static dump of timings + captured stdout + the formatted error — there is no step-through execution yet.

## Suggested next features

- CodeMirror language mode for ROT (keyword highlighting, brace matching).
- Share-link with editor state encoded in the URL.
- Step-through execution with the runtime pausing between statements.
- Save / load to LocalStorage.
- A "Trace tokens" mode where clicking a token highlights its source span.
