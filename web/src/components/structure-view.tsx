"use client";

import { Fragment, useMemo } from "react";
import { motion } from "framer-motion";

import type { AstNode, AstValue } from "@/lib/pyodide-runtime";

interface StructureViewProps {
  ast: AstNode | null;
  // Per-Step delay so the Structure stage animates in after the
  // Read stage.
  baseDelaySec?: number;
  // Re-keyed by stepIndex so the entrance animation re-fires on
  // every step.
  stepKey: number;
}

// Renders an AST statement as pretty-printed source-like code with
// semantic coloring. Replaces the v2.26.x AST tree which was dense
// and hard to read. The output reads like normalized ROT code — for
// a one-line statement it's the same as the source, for multi-line
// blocks (if / while / for / funct) the structure is visible via
// indentation.
export function StructureView({
  ast,
  baseDelaySec = 0,
  stepKey,
}: StructureViewProps) {
  const rendered = useMemo(() => (ast ? renderNode(ast, 0) : []), [ast]);

  if (!ast || rendered.length === 0) {
    return (
      <div className="text-xs text-muted-foreground">
        (no parsed statement available)
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      <motion.div
        key={`label-${stepKey}`}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: baseDelaySec, ease: "easeOut" }}
        className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground"
      >
        {structureLabel(ast)}
      </motion.div>
      <motion.pre
        key={`code-${stepKey}`}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: 0.45,
          delay: baseDelaySec + 0.08,
          ease: [0.16, 1, 0.3, 1],
        }}
        className="overflow-x-auto whitespace-pre rounded bg-zinc-900/60 px-3 py-2 font-mono text-[12.5px] leading-relaxed"
      >
        {rendered.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </motion.pre>
    </div>
  );
}

// ─── Labels ─────────────────────────────────────────────────────

function structureLabel(node: AstNode): string {
  const map: Record<string, string> = {
    Assign: "Assignment",
    LetStmt: "Let binding",
    ExprStmt: "Expression",
    IfStmt: "Conditional",
    WhileStmt: "Loop (while)",
    ForStmt: "Loop (for)",
    FuncDef: "Function definition",
    ClassDef: "Class definition",
    Return: "Return",
    TryCatch: "Try / catch",
    ThrowStmt: "Throw",
    ImportStmt: "Import",
    BreakStmt: "Break",
    ContinueStmt: "Continue",
    IndexAssign: "Index assignment",
    MemberAssign: "Field assignment",
  };
  return map[node.__type__] ?? node.__type__;
}

// ─── Pretty-print: statements (multi-line) ──────────────────────

// Render a statement-level node as JSX lines. Indent levels expand
// for nested block-bearing statements (if / while / for / funct /
// class / try).
function renderNode(node: AstValue, indent: number): React.ReactNode[] {
  if (node === null || typeof node !== "object" || Array.isArray(node)) {
    return [<Text key="x">{`${pad(indent)}${String(node)}`}</Text>];
  }
  const n = node as AstNode;
  const ind = pad(indent);

  switch (n.__type__) {
    case "ExprStmt":
      return [
        <Line key="0">
          {ind}
          {renderInline(n.expr as AstNode)}
        </Line>,
      ];

    case "Assign": {
      const op = typeof n.op === "string" ? n.op : "=";
      return [
        <Line key="0">
          {ind}
          <Name>{String(n.name)}</Name>
          {" "}
          <Punct>{op === "=" ? "=" : op}</Punct>
          {" "}
          {renderInline(n.value as AstNode)}
        </Line>,
      ];
    }

    case "LetStmt":
      return [
        <Line key="0">
          {ind}
          <Keyword>let</Keyword>
          {" "}
          <Name>{String(n.name)}</Name>
          {" "}
          <Punct>=</Punct>
          {" "}
          {renderInline(n.value as AstNode)}
        </Line>,
      ];

    case "IfStmt": {
      const lines: React.ReactNode[] = [];
      lines.push(
        <Line key="if">
          {ind}
          <Keyword>if</Keyword>
          {" "}
          <Punct>(</Punct>
          {renderInline(n.cond as AstNode)}
          <Punct>)</Punct>
          {" "}
          <Punct>{"{"}</Punct>
        </Line>,
      );
      lines.push(...renderBlock(n.then_block as AstNode, indent + 1));
      const elifs = (n.elif_branches as AstNode[]) ?? [];
      for (let i = 0; i < elifs.length; i++) {
        const branch = elifs[i];
        lines.push(
          <Line key={`elif-${i}`}>
            {ind}
            <Punct>{"}"}</Punct>
            {" "}
            <Keyword>elseif</Keyword>
            {" "}
            <Punct>(</Punct>
            {renderInline(branch.cond as AstNode)}
            <Punct>)</Punct>
            {" "}
            <Punct>{"{"}</Punct>
          </Line>,
        );
        lines.push(...renderBlock(branch.body as AstNode, indent + 1));
      }
      if (n.else_block) {
        lines.push(
          <Line key="else">
            {ind}
            <Punct>{"}"}</Punct>
            {" "}
            <Keyword>else</Keyword>
            {" "}
            <Punct>{"{"}</Punct>
          </Line>,
        );
        lines.push(...renderBlock(n.else_block as AstNode, indent + 1));
      }
      lines.push(
        <Line key="close">
          {ind}
          <Punct>{"}"}</Punct>
        </Line>,
      );
      return lines;
    }

    case "WhileStmt": {
      const lines: React.ReactNode[] = [
        <Line key="w">
          {ind}
          <Keyword>while</Keyword>
          {" "}
          <Punct>(</Punct>
          {renderInline(n.cond as AstNode)}
          <Punct>)</Punct>
          {" "}
          <Punct>{"{"}</Punct>
        </Line>,
        ...renderBlock(n.body as AstNode, indent + 1),
        <Line key="close">
          {ind}
          <Punct>{"}"}</Punct>
        </Line>,
      ];
      return lines;
    }

    case "ForStmt": {
      const lines: React.ReactNode[] = [
        <Line key="f">
          {ind}
          <Keyword>for</Keyword>
          {" "}
          <Name>{String(n.var)}</Name>
          {" "}
          <Keyword>in</Keyword>
          {" "}
          {renderInline(n.iter as AstNode)}
          {" "}
          <Punct>{"{"}</Punct>
        </Line>,
        ...renderBlock(n.body as AstNode, indent + 1),
        <Line key="close">
          {ind}
          <Punct>{"}"}</Punct>
        </Line>,
      ];
      return lines;
    }

    case "FuncDef": {
      const params = (n.params as string[]) ?? [];
      const paramsNode = params.map((p, i) => (
        <Fragment key={p}>
          {i > 0 && <Punct>{" | "}</Punct>}
          <Name>{p}</Name>
        </Fragment>
      ));
      const lines: React.ReactNode[] = [
        <Line key="def">
          {ind}
          <Keyword>funct</Keyword>
          {" "}
          <Name>{String(n.name)}</Name>
          <Punct>(</Punct>
          {paramsNode}
          <Punct>)</Punct>
          {" "}
          <Punct>{"{"}</Punct>
        </Line>,
        ...renderBlock(n.body as AstNode, indent + 1),
        <Line key="close">
          {ind}
          <Punct>{"}"}</Punct>
        </Line>,
      ];
      return lines;
    }

    case "ClassDef": {
      const lines: React.ReactNode[] = [
        <Line key="def">
          {ind}
          <Keyword>class</Keyword>
          {" "}
          <Name>{String(n.name)}</Name>
          {" "}
          <Punct>{"{"}</Punct>
        </Line>,
      ];
      const members = (n.members as AstNode[]) ?? [];
      for (const m of members) {
        lines.push(...renderNode(m, indent + 1));
      }
      lines.push(
        <Line key="close">
          {ind}
          <Punct>{"}"}</Punct>
        </Line>,
      );
      return lines;
    }

    case "Return": {
      if (n.value === null || n.value === undefined) {
        return [
          <Line key="r">
            {ind}
            <Keyword>return</Keyword>
          </Line>,
        ];
      }
      return [
        <Line key="r">
          {ind}
          <Keyword>return</Keyword>{" "}
          {renderInline(n.value as AstNode)}
        </Line>,
      ];
    }

    case "ThrowStmt":
      return [
        <Line key="t">
          {ind}
          <Keyword>throw</Keyword>{" "}
          {renderInline(n.value as AstNode)}
        </Line>,
      ];

    case "BreakStmt":
      return [
        <Line key="b">
          {ind}
          <Keyword>break</Keyword>
        </Line>,
      ];

    case "ContinueStmt":
      return [
        <Line key="c">
          {ind}
          <Keyword>continue</Keyword>
        </Line>,
      ];

    case "ImportStmt":
      return [
        <Line key="i">
          {ind}
          <Keyword>import</Keyword>{" "}
          <Str>{JSON.stringify(String(n.path))}</Str>
        </Line>,
      ];

    case "TryCatch": {
      const lines: React.ReactNode[] = [
        <Line key="t">
          {ind}
          <Keyword>try</Keyword> <Punct>{"{"}</Punct>
        </Line>,
        ...renderBlock(n.try_block as AstNode, indent + 1),
      ];
      if (n.catch_var !== undefined && n.catch_block) {
        lines.push(
          <Line key="catch">
            {ind}
            <Punct>{"}"}</Punct>{" "}
            <Keyword>catch</Keyword>
            <Punct>(</Punct>
            <Name>{String(n.catch_var)}</Name>
            <Punct>)</Punct>{" "}
            <Punct>{"{"}</Punct>
          </Line>,
        );
        lines.push(...renderBlock(n.catch_block as AstNode, indent + 1));
      }
      if (n.finally_block) {
        lines.push(
          <Line key="finally">
            {ind}
            <Punct>{"}"}</Punct>{" "}
            <Keyword>finally</Keyword>{" "}
            <Punct>{"{"}</Punct>
          </Line>,
        );
        lines.push(...renderBlock(n.finally_block as AstNode, indent + 1));
      }
      lines.push(
        <Line key="close">
          {ind}
          <Punct>{"}"}</Punct>
        </Line>,
      );
      return lines;
    }

    case "IndexAssign":
      return [
        <Line key="0">
          {ind}
          {renderInline(n.target as AstNode)}
          <Punct>[</Punct>
          {renderInline(n.index as AstNode)}
          <Punct>]</Punct>{" "}
          <Punct>=</Punct>{" "}
          {renderInline(n.value as AstNode)}
        </Line>,
      ];

    case "MemberAssign":
      return [
        <Line key="0">
          {ind}
          {renderInline(n.target as AstNode)}
          <Punct>.</Punct>
          <Name>{String(n.member)}</Name>{" "}
          <Punct>=</Punct>{" "}
          {renderInline(n.value as AstNode)}
        </Line>,
      ];

    // Block isn't a statement on its own but appears as `then_block`
    // etc.; handled via `renderBlock` directly.
    default:
      return [
        <Line key="fallback">
          {ind}
          <Text>{`<${n.__type__}>`}</Text>
        </Line>,
      ];
  }
}

function renderBlock(block: AstNode, indent: number): React.ReactNode[] {
  const stmts = (block?.statements as AstNode[]) ?? [];
  const lines: React.ReactNode[] = [];
  for (const stmt of stmts) {
    lines.push(...renderNode(stmt, indent));
  }
  return lines;
}

// ─── Inline-expression renderer ─────────────────────────────────

// Returns a React fragment for an expression — always a single line.
function renderInline(node: AstValue): React.ReactNode {
  if (node === null || node === undefined) return <Lit>null</Lit>;
  if (typeof node === "string") return <Str>{JSON.stringify(node)}</Str>;
  if (typeof node === "number") return <Num>{String(node)}</Num>;
  if (typeof node === "boolean") return <Lit>{node ? "true" : "false"}</Lit>;
  if (Array.isArray(node)) return <Text>{`[...]`}</Text>;
  const n = node as AstNode;
  switch (n.__type__) {
    case "NumberLit":
      return <Num>{String(n.value)}</Num>;
    case "StringLit":
      return <Str>{JSON.stringify(String(n.value))}</Str>;
    case "BoolLit":
      return <Lit>{n.value ? "true" : "false"}</Lit>;
    case "NullLit":
      return <Lit>null</Lit>;
    case "Identifier":
      return <Name>{String(n.name)}</Name>;
    case "BinaryOp": {
      return (
        <>
          {renderInline(n.left as AstNode)}{" "}
          <Op>{String(n.op)}</Op>{" "}
          {renderInline(n.right as AstNode)}
        </>
      );
    }
    case "UnaryOp": {
      const op = String(n.op);
      return (
        <>
          <Op>{op}</Op>
          {op === "not" ? " " : ""}
          {renderInline(n.operand as AstNode)}
        </>
      );
    }
    case "Call": {
      const args = (n.args as AstNode[]) ?? [];
      return (
        <>
          {renderInline(n.callee as AstNode)}
          <Punct>(</Punct>
          {args.map((a, i) => (
            <Fragment key={i}>
              {i > 0 && <Punct>{" | "}</Punct>}
              {renderInline(a)}
            </Fragment>
          ))}
          <Punct>)</Punct>
        </>
      );
    }
    case "Index": {
      return (
        <>
          {renderInline(n.target as AstNode)}
          <Punct>[</Punct>
          {renderInline(n.index as AstNode)}
          <Punct>]</Punct>
        </>
      );
    }
    case "Slice": {
      return (
        <>
          {renderInline(n.target as AstNode)}
          <Punct>[</Punct>
          {n.start ? renderInline(n.start as AstNode) : null}
          <Punct>:</Punct>
          {n.stop ? renderInline(n.stop as AstNode) : null}
          {n.step ? (
            <>
              <Punct>:</Punct>
              {renderInline(n.step as AstNode)}
            </>
          ) : null}
          <Punct>]</Punct>
        </>
      );
    }
    case "MemberAccess": {
      return (
        <>
          {renderInline(n.target as AstNode)}
          <Punct>.</Punct>
          <Name>{String(n.member)}</Name>
        </>
      );
    }
    case "ListLit": {
      const values = (n.values as AstNode[]) ?? [];
      return (
        <>
          <Punct>[</Punct>
          {values.map((v, i) => (
            <Fragment key={i}>
              {i > 0 && <Punct>{" | "}</Punct>}
              {renderInline(v)}
            </Fragment>
          ))}
          <Punct>]</Punct>
        </>
      );
    }
    case "DictLit": {
      const pairs = (n.pairs as Array<[AstNode, AstNode]>) ?? [];
      return (
        <>
          <Punct>{"{"}</Punct>
          {pairs.map(([k, v], i) => (
            <Fragment key={i}>
              {i > 0 && <Punct>{" | "}</Punct>}
              {renderInline(k)}
              <Punct>: </Punct>
              {renderInline(v)}
            </Fragment>
          ))}
          <Punct>{"}"}</Punct>
        </>
      );
    }
    default:
      return <Text>{`<${n.__type__}>`}</Text>;
  }
}

// ─── Coloring primitives ────────────────────────────────────────

// Tiny inline components — keep the markup compact since `renderNode`
// composes a lot of them per line.
function Keyword({ children }: { children: React.ReactNode }) {
  return <span className="text-purple-300">{children}</span>;
}
function Name({ children }: { children: React.ReactNode }) {
  return <span className="text-sky-300">{children}</span>;
}
function Num({ children }: { children: React.ReactNode }) {
  return <span className="text-cyan-300">{children}</span>;
}
function Str({ children }: { children: React.ReactNode }) {
  return <span className="text-amber-300">{children}</span>;
}
function Lit({ children }: { children: React.ReactNode }) {
  return <span className="text-emerald-300">{children}</span>;
}
function Op({ children }: { children: React.ReactNode }) {
  return <span className="text-rose-300">{children}</span>;
}
function Punct({ children }: { children: React.ReactNode }) {
  return <span className="text-zinc-400">{children}</span>;
}
function Text({ children }: { children: React.ReactNode }) {
  return <span className="text-foreground/80">{children}</span>;
}
function Line({ children }: { children: React.ReactNode }) {
  return <div>{children}</div>;
}

function pad(n: number): string {
  return "  ".repeat(n);
}
