import Link from "next/link";
import { ArrowLeft, ArrowRight, ExternalLink } from "lucide-react";

import { CodeBlock } from "@/components/code-block";
import { HeroAnimation } from "@/components/hero-animation";
import { PipelineDiagram } from "@/components/pipeline-diagram";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import {
  LexerAnimation,
  ParserAnimation,
  VMAnimation,
} from "@/components/stage-animations";

interface Section {
  id: string;
  title: string;
}

const TOC: Section[] = [
  { id: "watch", title: "Watch the pipeline" },
  { id: "source", title: "Source — characters" },
  { id: "lexer", title: "Lexer — tokens" },
  { id: "parser", title: "Parser — AST" },
  { id: "interpreter", title: "Interpreter — snapshots" },
  { id: "bytecode", title: "Bytecode — opcodes" },
  { id: "output", title: "Output — stdout" },
  { id: "where-next", title: "Where to look next" },
];

const FIZZBUZZ_SOURCE = `i = 1
while (i <= 3) {
    if (i == 3) {
        coutln("Fizz")
    } else {
        coutln(i)
    }
    i = i + 1
}`;

const TOKEN_SAMPLE = `IDENT(i) OP(=) NUMBER(1)
WHILE LPAREN IDENT(i) LE NUMBER(3) RPAREN LBRACE
IF LPAREN IDENT(i) EQ NUMBER(3) RPAREN LBRACE
IDENT(coutln) LPAREN STRING("Fizz") RPAREN
RBRACE ELSE LBRACE
IDENT(coutln) LPAREN IDENT(i) RPAREN
RBRACE
IDENT(i) OP(=) IDENT(i) OP(+) NUMBER(1)
RBRACE`;

const AST_SAMPLE = `Program
└── statements
    ├── Assign(target=Var("i"), value=Lit(1))
    └── WhileStmt(
        cond = BinaryOp("<=", Var("i"), Lit(3)),
        body = Block([
            IfStmt(
                cond   = BinaryOp("==", Var("i"), Lit(3)),
                then   = Block([Call(Var("coutln"), [Lit("Fizz")])]),
                else_  = Block([Call(Var("coutln"), [Var("i")])])
            ),
            Assign(
                target = Var("i"),
                value  = BinaryOp("+", Var("i"), Lit(1))
            )
        ])
    )`;

const BYTECODE_SAMPLE = `# the i = 1 line compiles to:
0   LOAD_CONST    1
2   STORE_NAME    i

# while (i <= 3) { ... } compiles to:
4   LOAD_NAME     i
6   LOAD_CONST    3
8   LE
9   JUMP_IF_FALSE  <end-of-loop>
...`;

export default function InternalsPage() {
  return (
    <div className="flex min-h-full flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6 lg:py-16">
        <header className="mb-10">
          <Link
            href="/docs"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" />
            All docs
          </Link>
          <h1 className="mt-4 font-mono text-4xl font-semibold tracking-tight">
            Internals
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            How ROT actually works. A nine-line program — counting from
            1 to 3 with a Fizz on the third — walked through every stage
            of the pipeline, end to end.
          </p>
        </header>
        <div className="grid gap-12 lg:grid-cols-[200px_1fr] lg:gap-16">
          <aside className="hidden lg:block">
            <nav className="lg:sticky lg:top-24">
              <div className="text-xs uppercase tracking-wider text-muted-foreground">
                On this page
              </div>
              <ul className="mt-3 space-y-1.5 text-sm">
                {TOC.map((s) => (
                  <li key={s.id}>
                    <a
                      href={`#${s.id}`}
                      className="block text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {s.title}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          </aside>
          <main className="min-w-0">
            <Watch />
            <Source />
            <Lexer />
            <Parser />
            <Interpreter />
            <Bytecode />
            <Output />
            <WhereNext />
          </main>
        </div>
      </div>
      <SiteFooter />
    </div>
  );
}

function SectionHeading({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2
      id={id}
      className="scroll-mt-24 font-mono text-2xl font-semibold tracking-tight text-foreground"
    >
      {children}
    </h2>
  );
}

function Watch() {
  return (
    <section id="watch" className="scroll-mt-24">
      <SectionHeading id="watch">Watch the pipeline</SectionHeading>
      <p className="mt-3 max-w-3xl text-base leading-relaxed text-foreground/90">
        Every stage that this page describes — read, parse, run — is
        what you see below. The animation loops through fourteen
        statement-executions of a tiny FizzBuzz, captured from the same
        snapshot model the playground exposes.
      </p>
      <div className="mt-6">
        <HeroAnimation />
      </div>
      <div className="mt-8">
        <PipelineDiagram />
      </div>
    </section>
  );
}

function Source() {
  return (
    <section id="source" className="mt-16 scroll-mt-24">
      <SectionHeading id="source">Source — characters</SectionHeading>
      <p className="mt-3 max-w-3xl text-base leading-relaxed text-foreground/90">
        The whole program is just text. Whitespace matters only inside
        strings; ROT uses C-style braces, not Python-style indentation.
      </p>
      <div className="mt-6">
        <CodeBlock code={FIZZBUZZ_SOURCE} language="rot" filename="demo.rot" />
      </div>
      <p className="mt-4 max-w-3xl text-[13.5px] leading-relaxed text-muted-foreground">
        Nothing is happening yet. The file is bytes on disk. Two things
        will turn it into something runnable: a{" "}
        <span className="font-mono text-foreground">lexer</span> that
        groups characters into tokens, and a{" "}
        <span className="font-mono text-foreground">parser</span> that
        groups tokens into a tree.
      </p>
    </section>
  );
}

function Lexer() {
  return (
    <section id="lexer" className="mt-16 scroll-mt-24">
      <SectionHeading id="lexer">Lexer — tokens</SectionHeading>
      <p className="mt-3 max-w-3xl text-base leading-relaxed text-foreground/90">
        The lexer reads characters one at a time. When it sees a digit
        it consumes more digits until something stops being a digit, and
        emits a <span className="font-mono">NUMBER</span> token. When it
        sees a letter it consumes an identifier, then checks the keyword
        table to decide if it&apos;s
        <span className="font-mono"> WHILE</span> or just{" "}
        <span className="font-mono">IDENT</span>. Every token carries
        its source line and column.
      </p>
      <div className="mt-6">
        <LexerAnimation />
      </div>
      <div className="mt-6">
        <CodeBlock
          code={TOKEN_SAMPLE}
          language="text"
          filename="tokens (abbreviated)"
        />
      </div>
      <p className="mt-4 max-w-3xl text-[13.5px] leading-relaxed text-muted-foreground">
        Source:{" "}
        <a
          href="https://github.com/omkarxpatel/ROT/blob/main/rot/lexer.py"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-mono text-foreground/80 hover:text-foreground"
        >
          rot/lexer.py
          <ExternalLink className="h-3 w-3 opacity-60" />
        </a>{" "}
        — around 360 lines, no regex, no parser-generator. Just a
        big <code className="font-mono text-foreground">while</code>{" "}
        loop and a character-dispatch table.
      </p>
    </section>
  );
}

function Parser() {
  return (
    <section id="parser" className="mt-16 scroll-mt-24">
      <SectionHeading id="parser">Parser — AST</SectionHeading>
      <p className="mt-3 max-w-3xl text-base leading-relaxed text-foreground/90">
        The parser turns the flat token stream into a tree of typed
        nodes — an <em>abstract syntax tree</em>. Statements use
        recursive descent (one function per grammar rule). Expressions
        use Pratt parsing, which handles operator precedence cleanly
        without a separate precedence table.
      </p>
      <div className="mt-6">
        <ParserAnimation />
      </div>
      <div className="mt-6">
        <CodeBlock
          code={AST_SAMPLE}
          language="text"
          filename="AST for the demo"
        />
      </div>
      <p className="mt-4 max-w-3xl text-[13.5px] leading-relaxed text-muted-foreground">
        Source:{" "}
        <a
          href="https://github.com/omkarxpatel/ROT/blob/main/rot/syntax.py"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-mono text-foreground/80 hover:text-foreground"
        >
          rot/syntax.py
          <ExternalLink className="h-3 w-3 opacity-60" />
        </a>
        . Every node is a{" "}
        <code className="font-mono text-foreground">@dataclass</code>{" "}
        with line and column fields, so runtime errors can point back
        to the exact source position.
      </p>
    </section>
  );
}

function Interpreter() {
  return (
    <section id="interpreter" className="mt-16 scroll-mt-24">
      <SectionHeading id="interpreter">
        Interpreter — snapshots
      </SectionHeading>
      <p className="mt-3 max-w-3xl text-base leading-relaxed text-foreground/90">
        The tree-walking interpreter visits each AST node in order, and
        executes it. Statements like{" "}
        <code className="font-mono">Assign</code> mutate the environment;{" "}
        <code className="font-mono">Call</code> pushes a new frame onto
        the scope chain; <code className="font-mono">If</code> evaluates
        its condition and dispatches.
      </p>
      <p className="mt-4 max-w-3xl text-base leading-relaxed text-foreground/90">
        For the playground, the interpreter also yields a{" "}
        <em>snapshot</em> after every statement — a frozen view of the
        scope chain, accumulated stdout, and the source position. That
        snapshot list is what the &ldquo;Step&rdquo; button walks
        through.
      </p>
      <p className="mt-4 max-w-3xl text-[13.5px] leading-relaxed text-muted-foreground">
        Source:{" "}
        <a
          href="https://github.com/omkarxpatel/ROT/blob/main/rot/interpreter.py"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-mono text-foreground/80 hover:text-foreground"
        >
          rot/interpreter.py
          <ExternalLink className="h-3 w-3 opacity-60" />
        </a>{" "}
        — about 1,100 lines. The fast path (
        <code className="font-mono text-foreground">execute()</code>) is
        the default; the snapshot path (
        <code className="font-mono text-foreground">iter_execute()</code>)
        is opt-in and powers the playground.
      </p>
    </section>
  );
}

function Bytecode() {
  return (
    <section id="bytecode" className="mt-16 scroll-mt-24">
      <SectionHeading id="bytecode">Bytecode — opcodes</SectionHeading>
      <p className="mt-3 max-w-3xl text-base leading-relaxed text-foreground/90">
        ROT also ships an opt-in bytecode compiler and stack VM. The
        compiler lowers the same AST into a flat array of 38 opcodes;
        the VM executes them with a value stack and a frame stack — the
        same model CPython, Lua, and the JVM use, just smaller.
      </p>
      <div className="mt-6">
        <VMAnimation />
      </div>
      <div className="mt-6">
        <CodeBlock
          code={BYTECODE_SAMPLE}
          language="text"
          filename="compiled chunk (excerpt)"
        />
      </div>
      <p className="mt-4 max-w-3xl text-[13.5px] leading-relaxed text-muted-foreground">
        Source:{" "}
        <a
          href="https://github.com/omkarxpatel/ROT/blob/main/rot/codegen.py"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-mono text-foreground/80 hover:text-foreground"
        >
          rot/codegen.py
          <ExternalLink className="h-3 w-3 opacity-60" />
        </a>{" "}
        and{" "}
        <a
          href="https://github.com/omkarxpatel/ROT/blob/main/rot/vm.py"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-mono text-foreground/80 hover:text-foreground"
        >
          rot/vm.py
          <ExternalLink className="h-3 w-3 opacity-60" />
        </a>
        . Try it from the CLI with{" "}
        <code className="font-mono text-foreground">
          python -m rot --vm examples/fizzbuzz.rot
        </code>
        .
      </p>
    </section>
  );
}

function Output() {
  return (
    <section id="output" className="mt-16 scroll-mt-24">
      <SectionHeading id="output">Output — stdout</SectionHeading>
      <p className="mt-3 max-w-3xl text-base leading-relaxed text-foreground/90">
        <code className="font-mono">cout</code> and{" "}
        <code className="font-mono">coutln</code> write to a captured
        buffer that the playground streams back to the browser, one
        chunk at a time. There&apos;s no magic: the implementation is{" "}
        <code className="font-mono">print(...)</code> into a{" "}
        <code className="font-mono">StringIO</code>.
      </p>
    </section>
  );
}

function WhereNext() {
  return (
    <section id="where-next" className="mt-16 scroll-mt-24">
      <SectionHeading id="where-next">Where to look next</SectionHeading>
      <ul className="mt-4 space-y-3 text-base leading-relaxed text-foreground/90">
        <li>
          <Link
            href="/playground"
            className="inline-flex items-center gap-1 text-foreground underline-offset-4 hover:underline"
          >
            Open the playground
            <ArrowRight className="h-4 w-4" />
          </Link>{" "}
          — type code, hit Animate, step through it statement by
          statement.
        </li>
        <li>
          <Link
            href="/docs"
            className="inline-flex items-center gap-1 text-foreground underline-offset-4 hover:underline"
          >
            The language reference
            <ArrowRight className="h-4 w-4" />
          </Link>{" "}
          — every keyword, operator, builtin, and surface feature.
        </li>
        <li>
          <a
            href="https://github.com/omkarxpatel/ROT"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-foreground underline-offset-4 hover:underline"
          >
            The source on GitHub
            <ExternalLink className="h-4 w-4" />
          </a>{" "}
          — ~25,000 lines across language and site. The lexer fits in one
          sitting.
        </li>
      </ul>
    </section>
  );
}
