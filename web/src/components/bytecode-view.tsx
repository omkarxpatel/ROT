"use client";

import { useState } from "react";
import { ChevronRight } from "lucide-react";

import type {
  RotChunkDump,
  RotConstant,
  RotFunctionDump,
  RotInstr,
} from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

interface BytecodeViewProps {
  chunk: RotChunkDump | null;
  empty?: string;
}

// Renders a compiled `Chunk` as a numbered list of opcodes plus the
// constant pool and name pool. Nested function-value constants
// render with an expandable disclosure showing their own chunk.
export function BytecodeView({ chunk, empty }: BytecodeViewProps) {
  if (!chunk) {
    return (
      <div className="text-xs text-muted-foreground">
        {empty ?? "(no chunk available)"}
      </div>
    );
  }
  return (
    <div className="space-y-3">
      <CodeListing chunk={chunk} />
      {chunk.constants.length > 0 && <ConstantsPool constants={chunk.constants} />}
      {chunk.names.length > 0 && <NamesPool names={chunk.names} />}
    </div>
  );
}

function CodeListing({ chunk }: { chunk: RotChunkDump }) {
  return (
    <div>
      <div className="mb-1 text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
        Code
      </div>
      <pre className="overflow-x-auto whitespace-pre rounded bg-zinc-900/60 px-3 py-2 font-mono text-[12.5px] leading-relaxed">
        {chunk.code.map((instr, i) => (
          <div key={i} className="flex items-baseline gap-3">
            <span className="w-10 shrink-0 text-right text-zinc-500">
              {i.toString().padStart(3, "0")}
            </span>
            <InstrLine instr={instr} chunk={chunk} />
          </div>
        ))}
      </pre>
    </div>
  );
}

function InstrLine({
  instr,
  chunk,
}: {
  instr: RotInstr;
  chunk: RotChunkDump;
}) {
  const [op, ...args] = instr;
  return (
    <span>
      <span className={cn("font-semibold", opColor(op))}>{op}</span>
      {args.map((arg, i) => (
        <span key={i}>
          {" "}
          <span className="text-cyan-300">{String(arg)}</span>
          {opArgAnnotation(op, i, arg, chunk) && (
            <span className="text-zinc-500">
              {" "}
              {opArgAnnotation(op, i, arg, chunk)}
            </span>
          )}
        </span>
      ))}
    </span>
  );
}

// Color opcodes by category — keep the palette consistent with the
// token-chip / structure-view colors so a reader can pattern-match.
function opColor(op: string): string {
  if (op.startsWith("LOAD_") || op === "POP" || op === "DUP")
    return "text-sky-300";
  if (op.startsWith("STORE_")) return "text-amber-300";
  if (
    op === "ADD" ||
    op === "SUB" ||
    op === "MUL" ||
    op === "DIV" ||
    op === "MOD" ||
    op === "NEG"
  )
    return "text-rose-300";
  if (
    op === "EQ" ||
    op === "NE" ||
    op === "LT" ||
    op === "LE" ||
    op === "GT" ||
    op === "GE" ||
    op === "NOT"
  )
    return "text-purple-300";
  if (op.startsWith("JUMP") || op === "ITER_NEXT" || op === "GET_ITER")
    return "text-emerald-300";
  if (op === "CALL" || op === "RETURN_VALUE" || op === "RETURN")
    return "text-amber-200";
  if (op === "BUILD_LIST" || op === "BUILD_DICT" || op.endsWith("_INDEX"))
    return "text-cyan-200";
  return "text-foreground/80";
}

// Inline annotation for an opcode's argument — e.g. for
// `LOAD_CONST 0` we show `(1)` if constant[0] is the integer 1, so
// the reader doesn't have to scroll to the pool.
function opArgAnnotation(
  op: string,
  argIndex: number,
  arg: unknown,
  chunk: RotChunkDump,
): string | null {
  if (argIndex !== 0 || typeof arg !== "number") return null;
  if (op === "LOAD_CONST") {
    const c = chunk.constants[arg];
    return c == null ? null : `(${formatConstant(c, true)})`;
  }
  if (op === "LOAD_NAME" || op === "STORE_NAME") {
    const n = chunk.names[arg];
    return n == null ? null : `(${n})`;
  }
  return null;
}

function formatConstant(c: RotConstant, inline = false): string {
  if (c === null) return "null";
  if (typeof c === "string") return JSON.stringify(c);
  if (typeof c === "boolean") return c ? "true" : "false";
  if (typeof c === "number") return String(c);
  if (typeof c === "object" && c.__type__ === "RotFunctionValue") {
    return inline ? `<funct ${c.name}>` : `<funct ${c.name}>`;
  }
  return String(c);
}

function ConstantsPool({ constants }: { constants: RotConstant[] }) {
  return (
    <div>
      <div className="mb-1 text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
        Constants
      </div>
      <ul className="space-y-0.5 font-mono text-[12px]">
        {constants.map((c, i) => (
          <li key={i} className="flex items-baseline gap-3">
            <span className="w-6 shrink-0 text-right text-zinc-500">{i}</span>
            <ConstantLine constant={c} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function ConstantLine({ constant }: { constant: RotConstant }) {
  if (
    typeof constant === "object" &&
    constant !== null &&
    constant.__type__ === "RotFunctionValue"
  ) {
    return <FunctionConstant fn={constant} />;
  }
  return (
    <span className={cn("text-emerald-300")}>{formatConstant(constant)}</span>
  );
}

function FunctionConstant({ fn }: { fn: RotFunctionDump }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-left hover:text-foreground"
      >
        <ChevronRight
          className={cn(
            "h-3 w-3 text-muted-foreground transition-transform",
            open && "rotate-90",
          )}
        />
        <span className="text-amber-200">
          &lt;funct {fn.name}
          {fn.params.length > 0 ? `(${fn.params.join(" | ")})` : "()"}&gt;
        </span>
      </button>
      {open && fn.chunk && (
        <div className="mt-1 border-l border-border/40 pl-3">
          <BytecodeView chunk={fn.chunk} />
        </div>
      )}
    </div>
  );
}

function NamesPool({ names }: { names: string[] }) {
  return (
    <div>
      <div className="mb-1 text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
        Names
      </div>
      <ul className="space-y-0.5 font-mono text-[12px]">
        {names.map((n, i) => (
          <li key={i} className="flex items-baseline gap-3">
            <span className="w-6 shrink-0 text-right text-zinc-500">{i}</span>
            <span className="text-sky-300">{n}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
