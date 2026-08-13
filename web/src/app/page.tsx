import Link from "next/link";
import { ArrowRight, ExternalLink, Github, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { HeroAnimation } from "@/components/hero-animation";
import { PipelineDiagram } from "@/components/pipeline-diagram";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import {
  LexerAnimation,
  ParserAnimation,
  VMAnimation,
} from "@/components/stage-animations";
import { ROT_VERSION } from "@/lib/rot-version";

const GITHUB_URL = "https://github.com/omkarxpatel/ROT";
const PAPER_URL = `${GITHUB_URL}/blob/main/paper/main.pdf`;

interface InsideFile {
  name: string;
  loc: string;
  blurb: string;
  href: string;
}

// LOC figures are rounded from the actual files — they shift
// commit-by-commit but the orders of magnitude are stable enough
// for marketing copy.
const INSIDE_ROT: InsideFile[] = [
  {
    name: "lexer.py",
    loc: "~320 LOC",
    blurb: "Hand-rolled, char-by-char tokenizer. Emits Tokens with line + col.",
    href: `${GITHUB_URL}/blob/main/rot/lexer.py`,
  },
  {
    name: "syntax.py",
    loc: "~870 LOC",
    blurb: "Recursive-descent statements; Pratt expressions. Builds the AST.",
    href: `${GITHUB_URL}/blob/main/rot/syntax.py`,
  },
  {
    name: "interpreter.py",
    loc: "~1,300 LOC",
    blurb:
      "Tree-walking evaluator. Snapshot-per-statement for the playground's step mode.",
    href: `${GITHUB_URL}/blob/main/rot/interpreter.py`,
  },
  {
    name: "codegen.py",
    loc: "~690 LOC",
    blurb: "AST → bytecode chunks. The M2 compiler. Per-instruction line attribution.",
    href: `${GITHUB_URL}/blob/main/rot/codegen.py`,
  },
  {
    name: "vm.py",
    loc: "~780 LOC",
    blurb: "Stack-based bytecode VM. Frames, handlers, 38 opcodes.",
    href: `${GITHUB_URL}/blob/main/rot/vm.py`,
  },
  {
    name: "errors.py",
    loc: "~90 LOC",
    blurb: "RotError + rustc-style rendering — source line, caret, hints.",
    href: `${GITHUB_URL}/blob/main/rot/errors.py`,
  },
];

interface DemoCard {
  name: string;
  example: string;
  blurb: string;
}

const DEMOS: DemoCard[] = [
  {
    name: "FizzBuzz",
    example: "fizzbuzz",
    blurb: "Loops, if/elseif/else, and the classic interview prompt.",
  },
  {
    name: "Factorial",
    example: "factorial",
    blurb: "Recursion + return value. Watch the call frame stack grow.",
  },
  {
    name: "Counter",
    example: "counter",
    blurb: "Classes, init, methods, and `this`. Object-oriented in ROT.",
  },
  {
    name: "Sum List",
    example: "sum_list",
    blurb: "Lists + for-in + compound assignment.",
  },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-full flex-col">
      <SiteHeader />
      <main className="flex-1">
        <Hero />
        {/* Directly under the hero: the hardest numbers should land in
            the first screen, not 1,100px down the page. */}
        <Stats />
        <Pipeline />
        <WatchEachStage />
        <WhatsInside />
        <Demos />
      </main>
      <SiteFooter />
    </div>
  );
}

function Hero() {
  return (
    <section className="mx-auto max-w-6xl px-4 pt-10 sm:px-6 sm:pt-14">
      <div className="grid items-start gap-8 lg:grid-cols-5 lg:gap-12">
        <div className="lg:col-span-2">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/5 px-2.5 py-1 text-[10px] uppercase tracking-wider text-amber-300">
            <Sparkles className="h-3 w-3" />
            v{ROT_VERSION} · 819 tests passing
          </div>
          {/* text-balance evens out the rag; the mono face at 6xl in a
              2/5 column breaks badly otherwise. */}
          <h1 className="mt-4 text-balance font-mono text-[2.5rem] font-semibold leading-[1.05] tracking-tighter text-foreground sm:text-5xl lg:text-6xl">
            Watch a programming language work.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-foreground/90 sm:text-lg">
            A small, hand-rolled language — tokenize, parse, execute,
            compile to bytecode — with every step animated in front of
            you. ~25,000 lines, no <code className="font-mono">exec()</code>,
            no compile-to-Python.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button asChild size="lg" className="px-5 sm:px-8">
              <Link href="/playground">
                Try it yourself
                <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="px-5 sm:px-8"
            >
              <Link href="#pipeline">How does it work?</Link>
            </Button>
          </div>
          {/* Redundant with the header nav on phones, and it costs the
              hero ~44px of height that the demo card needs. */}
          <div className="mt-6 hidden items-center gap-4 text-xs text-muted-foreground sm:flex">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 hover:text-foreground"
            >
              <Github className="h-3.5 w-3.5" />
              GitHub
            </a>
            <span className="text-border">{"·"}</span>
            <Link href="/docs" className="hover:text-foreground">
              Docs
            </Link>
            <span className="text-border">{"·"}</span>
            <Link href="/docs/internals" className="hover:text-foreground">
              Internals
            </Link>
          </div>
        </div>
        <div className="lg:col-span-3 lg:pt-2">
          <HeroAnimation />
        </div>
      </div>
    </section>
  );
}

function Pipeline() {
  return (
    <section
      id="pipeline"
      className="mx-auto mt-24 max-w-6xl scroll-mt-20 px-4 sm:px-6"
    >
      <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            The pipeline
          </h2>
          <p className="mt-2 max-w-2xl text-base leading-relaxed text-foreground/90">
            Six stages, from raw characters to printed output. The
            playground animates every one of them.
          </p>
        </div>
        <Link
          href="/playground"
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Open the playground →
        </Link>
      </div>
      <div className="mt-8">
        <PipelineDiagram />
      </div>
    </section>
  );
}

function WatchEachStage() {
  return (
    <section className="mx-auto mt-24 max-w-6xl px-4 sm:px-6">
      <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            Watch each stage
          </h2>
          <p className="mt-2 max-w-2xl text-base leading-relaxed text-foreground/90">
            Self-contained loops, one per major pipeline stage. The
            full playground threads them together.
          </p>
        </div>
        <Link
          href="/docs/internals"
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Read the internals docs →
        </Link>
      </div>
      <div className="mt-8 grid gap-4 lg:grid-cols-3">
        <LexerAnimation />
        <ParserAnimation />
        <VMAnimation />
      </div>
    </section>
  );
}

function Stats() {
  const stats: Array<{ label: string; value: string }> = [
    { label: "Version", value: `v${ROT_VERSION}` },
    { label: "Lines of code", value: "~25,000" },
    { label: "Tests passing", value: "819" },
    { label: "Opcodes (M2 VM)", value: "38" },
  ];
  return (
    <section className="mx-auto mt-10 max-w-6xl px-4 sm:px-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {stats.map((s) => (
          <div
            key={s.label}
            className="rounded-lg border border-border/60 bg-card/40 p-4"
          >
            <div className="text-xs uppercase tracking-wider text-muted-foreground">
              {s.label}
            </div>
            <div className="mt-2 font-mono text-2xl font-semibold tracking-tight">
              {s.value}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function WhatsInside() {
  return (
    <section className="mx-auto mt-24 max-w-6xl px-4 sm:px-6">
      <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            What&apos;s inside
          </h2>
          <p className="mt-2 max-w-2xl text-base leading-relaxed text-foreground/90">
            The whole language lives in six files. Each one is small
            enough to read in a sitting.
          </p>
        </div>
        <a
          href={PAPER_URL}
          target="_blank"
          rel="noreferrer"
          className="inline-flex shrink-0 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          Read the design retrospective (PDF)
          <ExternalLink className="h-3 w-3 opacity-60" />
        </a>
      </div>
      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {INSIDE_ROT.map((f) => (
          <a
            key={f.name}
            href={f.href}
            target="_blank"
            rel="noreferrer"
            className="group rounded-lg border border-border/60 bg-card/40 p-4 transition-colors hover:border-border hover:bg-card/60"
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-mono text-sm text-foreground">
                {f.name}
              </span>
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {f.loc}
              </span>
            </div>
            <p className="mt-3 text-[12.5px] leading-relaxed text-muted-foreground">
              {f.blurb}
            </p>
            <div className="mt-3 flex items-center gap-1 text-[11px] text-muted-foreground/70 group-hover:text-foreground">
              View on GitHub
              <ExternalLink className="h-3 w-3 opacity-60" />
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}

function Demos() {
  return (
    <section className="mx-auto mb-24 mt-24 max-w-6xl px-4 sm:px-6">
      <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            Demos
          </h2>
          <p className="mt-2 max-w-2xl text-base leading-relaxed text-foreground/90">
            Open a sample in the playground and step through it
            statement by statement.
          </p>
        </div>
      </div>
      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {DEMOS.map((d) => (
          <Link
            key={d.example}
            href={`/playground?example=${d.example}`}
            className="group rounded-lg border border-border/60 bg-card/40 p-4 transition-all hover:border-amber-500/40 hover:bg-card/60"
          >
            <div className="flex items-baseline justify-between">
              <span className="font-mono text-sm font-semibold tracking-tight text-foreground">
                {d.name}
              </span>
              <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/60 transition-transform group-hover:translate-x-0.5 group-hover:text-amber-300" />
            </div>
            <p className="mt-3 text-[12.5px] leading-relaxed text-muted-foreground">
              {d.blurb}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}
