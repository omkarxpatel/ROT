import Link from "next/link";
import { ArrowRight, ExternalLink, Github } from "lucide-react";

import { Button } from "@/components/ui/button";
import { CodeBlock } from "@/components/code-block";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { ROT_VERSION } from "@/lib/rot-version";

const GITHUB_URL = "https://github.com/omkarxpatel/ROT";

const HERO_SNIPPET = `funct fizzbuzz(n) {
    for i in range(1 | n + 1) {
        if (i % 15 == 0) {
            coutln("FizzBuzz")
        } elseif (i % 3 == 0) {
            coutln("Fizz")
        } elseif (i % 5 == 0) {
            coutln("Buzz")
        } else {
            coutln(i)
        }
    }
}
fizzbuzz(15)`;

const ROT_GREETING = `funct greet(name) {
    coutln(f"hello, {name}")
}
greet("world")`;

const PYTHON_GREETING = `def greet(name):
    print(f"hello, {name}")
greet("world")`;

const HIGHLIGHTS: Array<{ title: string; body: string }> = [
  {
    title: "rustc-style errors",
    body: "Every runtime error renders with the source line, a caret under the offending token, and Python-ism hints — `print` suggests `cout`, `def` suggests `funct`.",
  },
  {
    title: "let for explicit shadowing",
    body: "Bare `=` walks the scope chain (closures can mutate enclosing state). `let name = expr` opts out and declares a fresh local, mirroring the v2.16.6 design.",
  },
  {
    title: "try / catch / finally",
    body: "Full error-handling surface. `finally` runs through return, break, continue, and re-thrown exceptions — same semantics you'd expect from Python or Java.",
  },
  {
    title: "Slicing",
    body: "`s[a:b:c]` works on strings and lists. Negative bounds wrap from the end, step controls direction, omitted bounds clamp. `xs[::-1]` reverses.",
  },
  {
    title: "f-string format specs",
    body: "`f\"{pi:.2f}\"`, `f\"{n:>5}\"`, `f\"{255:x}\"` — the full Python format-spec mini-language, with ROT-style fallbacks for booleans, `null`, lists, and instances.",
  },
  {
    title: "Immutable builtins",
    body: "`pi = 3.0` is rejected at runtime; the builtin layer is frozen. Use `let pi = 3.0` to shadow locally — explicit, opt-in, no accidental clobber.",
  },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-full flex-col">
      <SiteHeader />
      <main className="flex-1">
        <Hero />
        <Stats />
        <WhatIsRot />
        <QuickTaste />
        <Highlights />
      </main>
      <SiteFooter />
    </div>
  );
}

function Hero() {
  return (
    <section className="mx-auto max-w-6xl px-4 pt-16 sm:px-6 sm:pt-24">
      <div className="grid items-start gap-12 lg:grid-cols-2 lg:gap-16">
        <div>
          <h1 className="font-mono text-6xl font-semibold tracking-tighter sm:text-7xl">
            ROT
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-foreground/90 sm:text-xl">
            A hand-rolled programming language. C++/Python-flavored, written in
            Python, ~3,800 lines.
          </p>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground">
            Built as a learning project. Tree-walking interpreter; bytecode VM
            coming next.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button asChild size="lg">
              <Link href="/playground">
                Try the playground
                <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/docs">Read the docs</Link>
            </Button>
          </div>
          <div className="mt-6 flex items-center gap-4 text-xs text-muted-foreground">
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
            <a
              href="/paper/main.pdf"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 hover:text-foreground"
            >
              Paper (PDF)
              <ExternalLink className="h-3 w-3 opacity-60" />
            </a>
          </div>
        </div>
        <div className="lg:pt-2">
          <CodeBlock
            code={HERO_SNIPPET}
            language="rot"
            filename="fizzbuzz.rot"
          />
        </div>
      </div>
    </section>
  );
}

function Stats() {
  const stats: Array<{ label: string; value: string }> = [
    { label: "Version", value: `v${ROT_VERSION}` },
    { label: "Lines of code", value: "~3,800" },
    { label: "Tests passing", value: "628" },
    { label: "Commits this year", value: "81" },
  ];
  return (
    <section className="mx-auto mt-20 max-w-6xl px-4 sm:px-6">
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

function WhatIsRot() {
  return (
    <section className="mx-auto mt-24 max-w-3xl px-4 sm:px-6">
      <h2 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
        What is ROT?
      </h2>
      <div className="mt-4 space-y-5 text-base leading-relaxed text-foreground/90">
        <p>
          ROT is a custom programming language built from scratch in Python. It
          has its own surface syntax (`funct` for `def`, `cout`/`coutln` for
          `print`, `|` as the argument separator, `this` not `self`, C-style
          braces, `//` comments) and its own runtime — no Python `exec()` is
          involved.
        </p>
        <p>
          The pipeline is hand-rolled end to end. A character-by-character lexer
          produces tokens; a recursive-descent parser (Pratt for expressions)
          produces an AST; a tree-walking interpreter evaluates it directly.
          Every AST node carries source coordinates so runtime errors render in
          a rustc style — source line, caret, and a hint when the failure looks
          like a Python-ism.
        </p>
        <p>
          The feature surface is intentionally focused: `let` for explicit
          shadowing, `try`/`catch`/`finally` for error handling, slicing,
          f-string format specs, immutable builtins, info-leak hardening against
          Python attribute access, and 628 tests across Python 3.9-3.12 in CI.
          This is a learning project and portfolio piece — the next direction
          is a bytecode VM.
        </p>
      </div>
    </section>
  );
}

function QuickTaste() {
  return (
    <section className="mx-auto mt-24 max-w-6xl px-4 sm:px-6">
      <h2 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
        Quick taste
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        A side-by-side with Python to ground the surface.
      </p>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <CodeBlock code={ROT_GREETING} language="rot" label="ROT" />
        <CodeBlock code={PYTHON_GREETING} language="python" label="Python" />
      </div>
      <p className="mt-4 text-xs text-muted-foreground">
        Different surface: <code className="font-mono">funct</code> not{" "}
        <code className="font-mono">def</code>,{" "}
        <code className="font-mono">cout</code>/
        <code className="font-mono">coutln</code> not{" "}
        <code className="font-mono">print</code>,{" "}
        <code className="font-mono">|</code> not{" "}
        <code className="font-mono">,</code> for arg separators,{" "}
        <code className="font-mono">this</code> not{" "}
        <code className="font-mono">self</code>,{" "}
        <code className="font-mono">//</code> comments, C-style braces.
      </p>
    </section>
  );
}

function Highlights() {
  return (
    <section className="mx-auto mt-24 max-w-6xl px-4 sm:px-6">
      <h2 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
        Highlights
      </h2>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {HIGHLIGHTS.map((h) => (
          <div
            key={h.title}
            className="rounded-lg border border-border/60 bg-card/40 p-5"
          >
            <h3 className="font-mono text-sm font-semibold tracking-tight">
              {h.title}
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              {h.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
