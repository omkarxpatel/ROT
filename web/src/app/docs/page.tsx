import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  Compass,
  GitBranch,
  Sparkles,
} from "lucide-react";

import { Callout } from "@/components/callout";
import { CodeBlock } from "@/components/code-block";
import { MiniPlayground } from "@/components/mini-playground";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";

interface TocItem {
  id: string;
  title: string;
}

interface TocGroup {
  label: string;
  items: TocItem[];
}

const TOC_GROUPS: TocGroup[] = [
  {
    label: "Basics",
    items: [
      { id: "getting-started", title: "Getting started" },
      { id: "hello-world", title: "Hello world" },
      { id: "variables", title: "Variables" },
      { id: "literals", title: "Literals" },
      { id: "operators", title: "Operators" },
    ],
  },
  {
    label: "Flow & shape",
    items: [
      { id: "control-flow", title: "Control flow" },
      { id: "functions", title: "Functions" },
      { id: "classes", title: "Classes" },
    ],
  },
  {
    label: "Beyond basics",
    items: [
      { id: "error-handling", title: "Error handling" },
      { id: "imports", title: "Imports" },
      { id: "fstrings", title: "F-strings" },
      { id: "slicing", title: "Slicing" },
    ],
  },
  {
    label: "Reference",
    items: [
      { id: "builtins", title: "Builtins reference" },
      { id: "repl", title: "The REPL" },
      { id: "errors", title: "Error messages" },
      { id: "reserved-words", title: "Reserved words" },
      { id: "examples", title: "Examples" },
    ],
  },
];

export default function DocsPage() {
  return (
    <div className="flex min-h-full flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6 lg:py-16">
        <header className="mb-10">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-card/40 px-2.5 py-1 text-[10px] uppercase tracking-wider text-muted-foreground">
            Language reference
          </div>
          <h1 className="mt-4 font-mono text-4xl font-semibold tracking-tight">
            Docs
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            Every section is a runnable example with the minimum prose
            needed to read it. Click <span className="font-mono text-foreground">Run</span> on any
            block to execute it inline — no install. Reach for the{" "}
            <Link
              href="/docs/internals"
              className="text-foreground underline-offset-4 hover:underline"
            >
              Internals
            </Link>{" "}
            doc to see how the language is implemented.
          </p>
        </header>
        <QuickLinks />
        <div className="mt-12 grid gap-12 lg:grid-cols-[220px_1fr] lg:gap-16">
          <aside className="hidden lg:block">
            <nav className="lg:sticky lg:top-24">
              <div className="text-xs uppercase tracking-wider text-muted-foreground">
                On this page
              </div>
              <div className="mt-4 space-y-5 text-sm">
                {TOC_GROUPS.map((group) => (
                  <div key={group.label}>
                    <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                      {group.label}
                    </div>
                    <ul className="space-y-1">
                      {group.items.map((item) => (
                        <li key={item.id}>
                          <a
                            href={`#${item.id}`}
                            className="block text-muted-foreground transition-colors hover:text-foreground"
                          >
                            {item.title}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </nav>
          </aside>
          <article className="prose prose-invert max-w-none scroll-smooth">
            <GettingStarted />
            <HelloWorld />
            <Variables />
            <Literals />
            <Operators />
            <ControlFlow />
            <Functions />
            <Classes />
            <ErrorHandling />
            <Imports />
            <FStrings />
            <Slicing />
            <Builtins />
            <Repl />
            <Errors />
            <ReservedWords />
            <Examples />
          </article>
        </div>
      </div>
      <SiteFooter />
    </div>
  );
}

function SectionHeading({
  id,
  children,
}: {
  id: string;
  children: React.ReactNode;
}) {
  return (
    <h2
      id={id}
      className="mt-16 scroll-mt-24 font-mono text-2xl font-semibold tracking-tight first:mt-0"
    >
      <a href={`#${id}`} className="no-underline">
        {children}
      </a>
    </h2>
  );
}

function Prose({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-4 space-y-4 text-sm leading-relaxed text-foreground/90">
      {children}
    </div>
  );
}

function CodeFrame({
  code,
  language = "rot",
  label,
}: {
  code: string;
  language?: "rot" | "python" | "bash" | "text";
  label?: string;
}) {
  return (
    <div className="mt-4">
      <CodeBlock code={code} language={language} label={label} />
    </div>
  );
}

function InlineCode({ children }: { children: React.ReactNode }) {
  return (
    <code className="rounded bg-zinc-900/70 px-1.5 py-0.5 font-mono text-[12px] text-foreground">
      {children}
    </code>
  );
}

/* -------------------------- Top quick-links -------------------------- */

function QuickLinks() {
  const tiles: Array<{
    href: string;
    icon: React.ComponentType<{ className?: string }>;
    label: string;
    blurb: string;
    accent: string;
  }> = [
    {
      href: "/playground",
      icon: Sparkles,
      label: "Open the playground",
      blurb: "Run any example in your browser. Step through statement-by-statement.",
      accent: "border-amber-500/30 hover:border-amber-500/50",
    },
    {
      href: "/docs/internals",
      icon: Compass,
      label: "How ROT works",
      blurb: "Lexer, parser, interpreter, bytecode VM — all walked through visually.",
      accent: "border-violet-500/30 hover:border-violet-500/50",
    },
    {
      href: "#examples",
      icon: Boxes,
      label: "Seven runnable demos",
      blurb: "Hello, fizzbuzz, factorial, counter, sum_list, multiple_prints, functions.",
      accent: "border-sky-500/30 hover:border-sky-500/50",
    },
    {
      href: "https://github.com/omkarxpatel/ROT",
      icon: GitBranch,
      label: "Source on GitHub",
      blurb: "~5,700 lines of Python. Read the lexer in one sitting.",
      accent: "border-emerald-500/30 hover:border-emerald-500/50",
    },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {tiles.map((t) => {
        const Icon = t.icon;
        const external = t.href.startsWith("http");
        const className = `group flex flex-col gap-2 rounded-lg border bg-card/40 p-4 transition-colors ${t.accent}`;
        const body = (
          <>
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4 text-foreground/80" />
              <span className="font-mono text-[12px] font-semibold tracking-tight text-foreground">
                {t.label}
              </span>
              <ArrowRight className="ml-auto h-3.5 w-3.5 text-muted-foreground/60 transition-transform group-hover:translate-x-0.5" />
            </div>
            <p className="text-[12px] leading-relaxed text-muted-foreground">
              {t.blurb}
            </p>
          </>
        );
        return external ? (
          <a
            key={t.href}
            href={t.href}
            target="_blank"
            rel="noreferrer"
            className={className}
          >
            {body}
          </a>
        ) : (
          <Link key={t.href} href={t.href} className={className}>
            {body}
          </Link>
        );
      })}
    </div>
  );
}

/* -------------------------- Section components ------------------------- */

function GettingStarted() {
  return (
    <section>
      <SectionHeading id="getting-started">Getting started</SectionHeading>
      <Prose>
        <p>ROT runs on Python 3.9 or newer. Two ways to grab it:</p>
      </Prose>
      <CodeFrame
        language="bash"
        code={`# clone the repo (no PyPI package yet)
git clone https://github.com/omkarxpatel/ROT.git
cd ROT

# run a program
python -m rot examples/fizzbuzz.rot

# start the REPL
python -m rot

# trace the pipeline (tokens + AST + timings)
python -m rot --trace examples/hello.rot`}
      />
      <Prose>
        <p>
          The fastest sandbox is the browser{" "}
          <Link href="/playground" className="underline-offset-4 hover:underline">
            playground
          </Link>{" "}
          — no install, Pyodide runs the real Python package in WASM.
        </p>
      </Prose>
    </section>
  );
}

function HelloWorld() {
  return (
    <section>
      <SectionHeading id="hello-world">Hello world</SectionHeading>
      <Prose>
        <p>
          <InlineCode>coutln</InlineCode> prints with a trailing newline;{" "}
          <InlineCode>cout</InlineCode> doesn&apos;t. Click{" "}
          <span className="font-mono text-foreground">Run</span> on the block
          below to see it.
        </p>
      </Prose>
      <MiniPlayground
        label="hello.rot"
        source={`coutln("hello, world")`}
        caption="The smallest ROT program."
      />
    </section>
  );
}

function Variables() {
  return (
    <section>
      <SectionHeading id="variables">Variables</SectionHeading>
      <Prose>
        <p>
          Bare <InlineCode>=</InlineCode> walks the scope chain to find an
          existing binding — that&apos;s how closures mutate enclosing state.{" "}
          <InlineCode>let name = expr</InlineCode> always declares a fresh
          local in the current scope.
        </p>
      </Prose>
      <MiniPlayground
        label="vars.rot"
        caption="Bare assignment vs. let: see what the inner function returns."
        source={`funct outer() {
    z = 1
    funct inner() {
        z = z + 1     // chain-walks; mutates outer's z
        let z = 99    // creates a NEW local z that shadows
        return z      // returns the local (99), not the outer
    }
    coutln(inner())
    coutln(z)         // outer's z was bumped to 2 by inner
}

outer()`}
      />
      <Callout variant="context" title="Why two forms?">
        <p>
          Many languages tie scope to declaration syntax (
          <InlineCode>let</InlineCode> / <InlineCode>var</InlineCode> /
          <InlineCode>const</InlineCode>). ROT splits it differently: a
          bare assignment <em>finds</em> an existing binding;{" "}
          <InlineCode>let</InlineCode> <em>creates</em> one. Closures
          mutate enclosing state by default — no Python-style
          <InlineCode>nonlocal</InlineCode> declaration needed.
        </p>
      </Callout>
      <Callout variant="warning" title="Builtins are frozen">
        <p>
          <InlineCode>pi = 3.0</InlineCode> raises at runtime; the builtin
          layer rejects re-binding. Shadow locally with{" "}
          <InlineCode>let pi = 3.0</InlineCode> if you really need it.
        </p>
      </Callout>
    </section>
  );
}

function Literals() {
  return (
    <section>
      <SectionHeading id="literals">Literals</SectionHeading>
      <Prose>
        <p>
          Numbers, strings, booleans, lists, and dicts. Note the{" "}
          <InlineCode>|</InlineCode> separator inside collections — ROT
          inherits Python&apos;s comma usage everywhere else.
        </p>
      </Prose>
      <MiniPlayground
        label="literals.rot"
        source={`n = 42
f = 3.14
s = "hello"
t = 'world'
ok = true
nothing = null

xs = [1 | 2 | 3]
d = {"name": "ada" | "age": 36}

coutln(n)
coutln(f)
coutln(f"{s}, {t}")
coutln(xs)
coutln(d)
coutln(ok)
coutln(nothing)`}
      />
      <Callout variant="note" title="Why `|` and not `,`?">
        <p>
          Commas are used in argument lists and statements; the language
          uses <InlineCode>|</InlineCode> as the list / dict / param
          separator to keep parsing dead-simple and unambiguous. There&apos;s
          no precedence-juggling between commas in different contexts.
        </p>
      </Callout>
    </section>
  );
}

function Operators() {
  return (
    <section>
      <SectionHeading id="operators">Operators</SectionHeading>
      <Prose>
        <p>Familiar surface, no integer division (yet).</p>
      </Prose>
      <CodeFrame
        code={`// arithmetic
a + b   a - b   a * b   a / b   a % b

// comparison
a == b   a != b   a < b   a <= b   a > b   a >= b

// logical
a and b   a or b   not a

// compound assignment
x += 1   x -= 1   x *= 2   x /= 2   x %= 3

// unary
-x   not flag`}
      />
    </section>
  );
}

function ControlFlow() {
  return (
    <section>
      <SectionHeading id="control-flow">Control flow</SectionHeading>
      <Prose>
        <p>
          <InlineCode>elseif</InlineCode> and the two-word{" "}
          <InlineCode>else if</InlineCode> both work.{" "}
          <InlineCode>break</InlineCode> and <InlineCode>continue</InlineCode>{" "}
          are lexically scoped to loops in the same function body — they
          can&apos;t escape across a call.
        </p>
      </Prose>
      <MiniPlayground
        label="control_flow.rot"
        caption="Branches, while + continue/break, for-in."
        source={`x = 0
if (x > 0) {
    coutln("positive")
} elseif (x < 0) {
    coutln("negative")
} else {
    coutln("zero")
}

i = 0
while (i < 6) {
    if (i == 3) { i += 1 continue }
    if (i == 5) { break }
    coutln(i)
    i += 1
}

for word in ["a" | "b" | "c"] {
    coutln(word)
}`}
      />
      <Callout variant="tip" title="Step through it visually">
        <p>
          Open this in the playground and switch to{" "}
          <span className="font-mono text-foreground">Animate</span> mode
          to step through every iteration, seeing the env update each
          time around the loop.
        </p>
      </Callout>
    </section>
  );
}

function Functions() {
  return (
    <section>
      <SectionHeading id="functions">Functions</SectionHeading>
      <Prose>
        <p>
          <InlineCode>funct</InlineCode> declares a function. Parameters are
          separated by <InlineCode>|</InlineCode>. Closures capture by
          reference — they can mutate enclosing scope unless you use{" "}
          <InlineCode>let</InlineCode> to shadow.
        </p>
      </Prose>
      <MiniPlayground
        label="functions.rot"
        caption="A function and a closure that remembers its own counter."
        source={`funct add(a | b) {
    return a + b
}

coutln(add(2 | 3))

funct make_counter() {
    count = 0
    funct tick() {
        count += 1
        return count
    }
    return tick
}

c = make_counter()
coutln(c())
coutln(c())
coutln(c())`}
      />
      <Callout variant="context" title="How does the closure remember `count`?">
        <p>
          When <InlineCode>make_counter</InlineCode> runs, it builds a
          function value that captures a reference to{" "}
          <InlineCode>count</InlineCode> in its enclosing scope. Every
          time you call <InlineCode>c()</InlineCode>, it walks the scope
          chain, finds the same{" "}
          <InlineCode>count</InlineCode>, and updates it. See it happen
          live in the{" "}
          <Link
            href="/playground?example=factorial"
            className="text-foreground underline-offset-4 hover:underline"
          >
            playground
          </Link>{" "}
          (Animate mode shows the scope chain growing).
        </p>
      </Callout>
    </section>
  );
}

function Classes() {
  return (
    <section>
      <SectionHeading id="classes">Classes</SectionHeading>
      <Prose>
        <p>
          <InlineCode>class</InlineCode> declares a class.{" "}
          <InlineCode>init</InlineCode> is the constructor. The method
          receiver is <InlineCode>this</InlineCode>, not{" "}
          <InlineCode>self</InlineCode>. Inheritance is not yet supported —{" "}
          <InlineCode>super</InlineCode> is reserved and produces a clear
          error.
        </p>
      </Prose>
      <MiniPlayground
        label="classes.rot"
        caption="A small mutable Counter. Watch the field update on each tick."
        source={`class Counter {
    init(start) {
        this.count = start
    }
    tick() {
        this.count += 1
        return this.count
    }
    to_string() {
        return f"Counter({this.count})"
    }
}

c = Counter(0)
c.tick()
c.tick()
coutln(c)`}
      />
      <Callout variant="note" title="`this`, not `self`">
        <p>
          ROT uses C++/Java-style <InlineCode>this</InlineCode> as the
          implicit receiver. It&apos;s bound automatically inside method
          bodies — no <InlineCode>self</InlineCode> parameter to declare.
        </p>
      </Callout>
      <Callout variant="warning" title="No inheritance yet">
        <p>
          Classes are single-level. <InlineCode>super</InlineCode> is
          reserved (so when inheritance lands, syntax won&apos;t shift),
          but using it today errors with a clear message. Compose
          instead: hold one instance inside another.
        </p>
      </Callout>
    </section>
  );
}

function ErrorHandling() {
  return (
    <section>
      <SectionHeading id="error-handling">Error handling</SectionHeading>
      <Prose>
        <p>
          <InlineCode>try</InlineCode> / <InlineCode>catch</InlineCode> /{" "}
          <InlineCode>finally</InlineCode> with the expected semantics —{" "}
          <InlineCode>finally</InlineCode> runs even when{" "}
          <InlineCode>return</InlineCode>, <InlineCode>break</InlineCode>,{" "}
          <InlineCode>continue</InlineCode>, or a re-throw fires inside the
          try. <InlineCode>throw</InlineCode> can carry any value.
        </p>
      </Prose>
      <MiniPlayground
        label="errors.rot"
        caption="`finally` always runs — even when the try body returns."
        source={`funct parse(s) {
    try {
        return num(s)
    } catch (e) {
        coutln(f"bad input: {e}")
        return null
    } finally {
        coutln("done")
    }
}

parse("not a number")

// throw any value — dicts, instances, primitives
try {
    throw {"code": 42 | "msg": "boom"}
} catch (err) {
    coutln(err["msg"])
}`}
      />
      <Callout variant="tip" title="Throws carry values, not types">
        <p>
          Unlike Java&apos;s typed exception hierarchy, a{" "}
          <InlineCode>throw</InlineCode> in ROT carries any value
          (number, string, dict, instance) and{" "}
          <InlineCode>catch (e)</InlineCode> binds it. Pattern-match on
          its shape with regular if-statements.
        </p>
      </Callout>
    </section>
  );
}

function Imports() {
  return (
    <section>
      <SectionHeading id="imports">Imports</SectionHeading>
      <Prose>
        <p>
          <InlineCode>import &quot;path&quot;</InlineCode> evaluates another{" "}
          <InlineCode>.rot</InlineCode> file in a fresh module scope and binds
          the resulting namespace to the file&apos;s basename. Paths are
          relative to the importing file. Modules are cached, so circular
          imports terminate.
        </p>
      </Prose>
      <CodeFrame
        code={`// math_utils.rot
funct square(x) { return x * x }
PI = 3.14159

// main.rot
import "math_utils"
coutln(math_utils.square(5))
coutln(math_utils.PI)`}
      />
      <Callout variant="warning" title="CLI-only">
        <p>
          Imports need a real filesystem with a second{" "}
          <InlineCode>.rot</InlineCode> file, so they only work from the
          CLI. The browser playground doesn&apos;t expose
          virtual-filesystem writes yet.
        </p>
      </Callout>
    </section>
  );
}

function FStrings() {
  return (
    <section>
      <SectionHeading id="fstrings">F-strings</SectionHeading>
      <Prose>
        <p>
          Prefix a string with <InlineCode>f</InlineCode> to interpolate
          expressions inside <InlineCode>{"{...}"}</InlineCode>. The full
          Python format-spec mini-language is supported because the
          desugaring routes through Python&apos;s built-in{" "}
          <InlineCode>format()</InlineCode>.
        </p>
      </Prose>
      <MiniPlayground
        label="fstrings.rot"
        source={`name = "ada"
coutln(f"hello, {name}")

pi = 3.14159
coutln(f"pi rounded: {pi:.2f}")

n = 7
coutln(f"[{n:>5}]")
coutln(f"hex {255:x}")
coutln(f"bin {10:08b}")

xs = [1 | 2 | 3 | 4 | 5]
coutln(f"first three: {xs[:3]}")`}
      />
    </section>
  );
}

function Slicing() {
  return (
    <section>
      <SectionHeading id="slicing">Slicing</SectionHeading>
      <Prose>
        <p>
          Strings and lists support <InlineCode>s[a:b]</InlineCode> and{" "}
          <InlineCode>s[a:b:c]</InlineCode>. Negative bounds wrap from the
          end, out-of-range bounds clamp, the step controls direction
          (<InlineCode>[::-1]</InlineCode> reverses). Dicts can&apos;t be
          sliced and report a clean error.
        </p>
      </Prose>
      <MiniPlayground
        label="slicing.rot"
        source={`s = "hello, world"
coutln(s[7:])
coutln(s[:5])
coutln(s[::-1])

xs = [10 | 20 | 30 | 40 | 50]
coutln(xs[1:4])
coutln(xs[::2])
coutln(xs[-2:])`}
      />
    </section>
  );
}

function Builtins() {
  return (
    <section>
      <SectionHeading id="builtins">Builtins reference</SectionHeading>
      <Prose>
        <p>
          About 35 builtins ship with the interpreter, organized by purpose.
          The full set is defined in{" "}
          <InlineCode>rot/builtins.py</InlineCode>.
        </p>
      </Prose>
      {BUILTIN_GROUPS.map((group) => (
        <div key={group.title} className="mt-6">
          <h3 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
            {group.title}
          </h3>
          <div className="mt-2 overflow-x-auto rounded-lg border border-border/60">
            <table className="w-full text-sm">
              <thead className="bg-card/50 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-medium">Name</th>
                  <th className="px-3 py-2 font-medium">Arity</th>
                  <th className="px-3 py-2 font-medium">Description</th>
                  <th className="px-3 py-2 font-medium">Example</th>
                </tr>
              </thead>
              <tbody>
                {group.rows.map((row) => (
                  <tr
                    key={row.name}
                    className="border-t border-border/60 align-top"
                  >
                    <td className="px-3 py-2 font-mono text-[13px] text-sky-300">
                      {row.name}
                    </td>
                    <td className="px-3 py-2 font-mono text-[12px] text-muted-foreground">
                      {row.arity}
                    </td>
                    <td className="px-3 py-2 text-[13px]">
                      {row.description}
                    </td>
                    <td className="px-3 py-2 font-mono text-[12px] text-muted-foreground">
                      {row.example}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </section>
  );
}

function Repl() {
  return (
    <section>
      <SectionHeading id="repl">The REPL</SectionHeading>
      <Prose>
        <p>
          <InlineCode>python -m rot</InlineCode> with no file starts the
          REPL. Multi-line input is supported (open braces and strings keep
          accepting more lines). History persists in{" "}
          <InlineCode>~/.rot_history</InlineCode>. Type{" "}
          <InlineCode>exit</InlineCode>, <InlineCode>quit</InlineCode>, or{" "}
          <InlineCode>:q</InlineCode> to leave.
        </p>
      </Prose>
      <CodeFrame
        language="bash"
        code={`$ python -m rot
ROT 2.25.x  |  Ctrl-D / exit / :q to quit
> x = 5
> x * x
25
> funct fact(n) {
...     if (n <= 1) { return 1 }
...     return n * fact(n - 1)
... }
> fact(6)
720
> :q`}
      />
    </section>
  );
}

function Errors() {
  return (
    <section>
      <SectionHeading id="errors">Error messages</SectionHeading>
      <Prose>
        <p>
          Runtime errors carry source coordinates and render in a rustc style
          — the offending source line, a caret, and a hint when the failure
          looks like a Python-ism. Click <span className="font-mono text-foreground">Run</span> below to trigger
          one.
        </p>
      </Prose>
      <MiniPlayground
        label="errors.rot"
        caption="Try common Python-isms — the error block calls them out by name."
        source={`// 'print' is Python's stdout function — ROT uses cout / coutln.
print("hello")`}
      />
      <Callout variant="context" title="What you'll see">
        <p>
          The formatted block prints with the offending source line, a
          caret under the failing identifier, and a note suggesting
          <InlineCode>cout</InlineCode>. The same shape applies to
          arity mismatches, attribute lookups, and type errors.
        </p>
      </Callout>
    </section>
  );
}

function ReservedWords() {
  return (
    <section>
      <SectionHeading id="reserved-words">Reserved words</SectionHeading>
      <Prose>
        <p>
          The full keyword table lives in{" "}
          <InlineCode>rot/keywords.py</InlineCode>.
        </p>
      </Prose>
      <div className="mt-4 overflow-x-auto rounded-lg border border-border/60">
        <table className="w-full text-sm">
          <thead className="bg-card/50 text-left text-xs uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">Keyword</th>
              <th className="px-3 py-2 font-medium">Role</th>
            </tr>
          </thead>
          <tbody>
            {RESERVED_WORDS.map((row) => (
              <tr key={row.word} className="border-t border-border/60">
                <td className="px-3 py-2 font-mono text-[13px] text-purple-300">
                  {row.word}
                </td>
                <td className="px-3 py-2 text-[13px]">{row.role}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Examples() {
  const examples: Array<{ key: string; name: string; blurb: string }> = [
    { key: "hello", name: "Hello", blurb: "The smallest ROT program." },
    {
      key: "multiple_prints",
      name: "Multiple prints",
      blurb: "cout vs coutln, newline behavior.",
    },
    {
      key: "factorial",
      name: "Factorial",
      blurb: "Recursion and return values.",
    },
    {
      key: "fizzbuzz",
      name: "FizzBuzz",
      blurb: "Loops, branches, the classic interview prompt.",
    },
    {
      key: "functions",
      name: "Functions",
      blurb: "funct syntax, params separated by |.",
    },
    {
      key: "sum_list",
      name: "Sum list",
      blurb: "Lists, for-in, and compound assignment.",
    },
    {
      key: "counter",
      name: "Counter",
      blurb: "Classes, init, methods, this.",
    },
  ];
  return (
    <section>
      <SectionHeading id="examples">Examples</SectionHeading>
      <Prose>
        <p>
          Seven runnable programs live in{" "}
          <a
            href="https://github.com/omkarxpatel/ROT/tree/main/examples"
            target="_blank"
            rel="noreferrer"
            className="underline-offset-4 hover:underline"
          >
            <InlineCode>examples/</InlineCode>
          </a>{" "}
          alongside golden <InlineCode>.expected</InlineCode> outputs. Each
          card below deep-links to the playground with the example
          pre-loaded.
        </p>
      </Prose>
      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {examples.map((ex) => (
          <Link
            key={ex.key}
            href={`/playground?example=${ex.key}`}
            className="group rounded-lg border border-border/60 bg-card/40 p-3 transition-colors hover:border-amber-500/40 hover:bg-card/60"
          >
            <div className="flex items-baseline justify-between">
              <span className="font-mono text-[13px] font-semibold text-foreground">
                {ex.name}
              </span>
              <ArrowRight className="h-3 w-3 text-muted-foreground/50 transition-transform group-hover:translate-x-0.5 group-hover:text-amber-300" />
            </div>
            <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">
              {ex.blurb}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}

/* ------------------------------- Data ---------------------------------- */

interface BuiltinRow {
  name: string;
  arity: string;
  description: string;
  example: string;
}

interface BuiltinGroup {
  title: string;
  rows: BuiltinRow[];
}

const BUILTIN_GROUPS: BuiltinGroup[] = [
  {
    title: "I/O",
    rows: [
      {
        name: "cout",
        arity: "1+",
        description: "Print without trailing newline.",
        example: 'cout("hi ")',
      },
      {
        name: "coutln",
        arity: "1+",
        description: "Print with trailing newline.",
        example: 'coutln("hello")',
      },
      {
        name: "input",
        arity: "0-1",
        description: "Read a line from stdin (optional prompt).",
        example: 'input("name? ")',
      },
      {
        name: "read_file",
        arity: "1",
        description: "Read a text file as a string (UTF-8).",
        example: 'read_file("notes.txt")',
      },
      {
        name: "write_file",
        arity: "2",
        description: "Write a string to a file (UTF-8).",
        example: 'write_file("out.txt" | "ok")',
      },
    ],
  },
  {
    title: "Conversion",
    rows: [
      {
        name: "str",
        arity: "1",
        description: "Convert any value to its rot-style string form.",
        example: "str(42)",
      },
      {
        name: "num",
        arity: "1",
        description: "Parse a string into a number; raises on bad input.",
        example: 'num("3.14")',
      },
      {
        name: "chr",
        arity: "1",
        description: "Codepoint integer to a single-char string.",
        example: "chr(65)",
      },
      {
        name: "ord",
        arity: "1",
        description: "Single-char string to its codepoint integer.",
        example: 'ord("A")',
      },
    ],
  },
  {
    title: "Math",
    rows: [
      { name: "abs", arity: "1", description: "Absolute value.", example: "abs(-3)" },
      { name: "min", arity: "1+", description: "Minimum of arguments / iterable.", example: "min(1 | 2 | 3)" },
      { name: "max", arity: "1+", description: "Maximum of arguments / iterable.", example: "max(xs)" },
      { name: "pow", arity: "2", description: "Power.", example: "pow(2 | 10)" },
      { name: "sqrt", arity: "1", description: "Square root.", example: "sqrt(16)" },
      { name: "floor", arity: "1", description: "Round down to integer.", example: "floor(3.7)" },
      { name: "ceil", arity: "1", description: "Round up to integer.", example: "ceil(3.2)" },
      { name: "round", arity: "1-2", description: "Round to nearest (optional ndigits).", example: "round(3.14159 | 2)" },
      { name: "pi", arity: "constant", description: "The constant pi.", example: "pi" },
      { name: "e", arity: "constant", description: "The constant e.", example: "e" },
    ],
  },
  {
    title: "Collections",
    rows: [
      { name: "len", arity: "1", description: "Length of a string, list, or dict.", example: "len(xs)" },
      { name: "range", arity: "1-3", description: "Integer range as a list.", example: "range(1 | 10)" },
      { name: "append", arity: "2", description: "Append to a list in place; returns the list.", example: "append(xs | 4)" },
      { name: "pop", arity: "1-2", description: "Pop and return last (or given index).", example: "pop(xs)" },
      { name: "sum", arity: "1", description: "Sum a list of numbers.", example: "sum([1 | 2 | 3])" },
      { name: "sorted", arity: "1", description: "Return a new sorted copy.", example: "sorted(xs)" },
      { name: "reversed", arity: "1", description: "Return a reversed copy.", example: "reversed(xs)" },
      { name: "keys", arity: "1", description: "Dict keys as a list.", example: "keys(d)" },
      { name: "values", arity: "1", description: "Dict values as a list.", example: "values(d)" },
      { name: "items", arity: "1", description: "Dict items as a list of pairs.", example: "items(d)" },
    ],
  },
  {
    title: "Type introspection",
    rows: [
      { name: "type", arity: "1", description: "Type name as a string.", example: 'type(42)   // "num"' },
      { name: "is_num", arity: "1", description: "True if value is a number.", example: "is_num(3.14)" },
      { name: "is_str", arity: "1", description: "True if value is a string.", example: 'is_str("hi")' },
      { name: "is_list", arity: "1", description: "True if value is a list.", example: "is_list([1])" },
      { name: "is_dict", arity: "1", description: "True if value is a dict.", example: "is_dict({})" },
      { name: "is_bool", arity: "1", description: "True if value is a boolean.", example: "is_bool(true)" },
      { name: "is_null", arity: "1", description: "True if value is null.", example: "is_null(null)" },
      { name: "is_func", arity: "1", description: "True if value is a function.", example: "is_func(coutln)" },
    ],
  },
  {
    title: "Random",
    rows: [
      { name: "rand_int", arity: "2", description: "Random integer in [lo, hi].", example: "rand_int(1 | 6)" },
      { name: "rand_float", arity: "0-2", description: "Random float (default [0, 1)).", example: "rand_float()" },
      { name: "seed", arity: "1", description: "Seed the RNG for reproducibility.", example: "seed(42)" },
    ],
  },
  {
    title: "Control",
    rows: [
      { name: "assert", arity: "1-2", description: "Raise if false; optional message.", example: 'assert(x > 0 | "must be positive")' },
      { name: "exit", arity: "0-1", description: "Exit the program (optional code).", example: "exit(1)" },
    ],
  },
];

const RESERVED_WORDS: Array<{ word: string; role: string }> = [
  { word: "funct", role: "Declare a function." },
  { word: "let", role: "Declare a fresh local binding (opt out of chain-walking)." },
  { word: "return", role: "Return a value from a function." },
  { word: "if", role: "Conditional." },
  { word: "elseif", role: "Else-if (one-word form)." },
  { word: "else", role: "Fallthrough branch (also pairs with `if` as two-word form)." },
  { word: "while", role: "While loop." },
  { word: "for", role: "For-in loop." },
  { word: "in", role: "Pairs with `for`." },
  { word: "break", role: "Break out of the nearest loop in the current function." },
  { word: "continue", role: "Skip to the next iteration." },
  { word: "class", role: "Declare a class." },
  { word: "this", role: "Implicit receiver inside method bodies." },
  { word: "try", role: "Begin a try block." },
  { word: "catch", role: "Catch a thrown value." },
  { word: "finally", role: "Always-runs block." },
  { word: "throw", role: "Throw any value." },
  { word: "import", role: "Import another .rot file." },
  { word: "and", role: "Logical AND." },
  { word: "or", role: "Logical OR." },
  { word: "not", role: "Logical NOT." },
  { word: "true", role: "Boolean true." },
  { word: "false", role: "Boolean false." },
  { word: "null", role: "Null value." },
  { word: "cout", role: "Print without newline." },
  { word: "coutln", role: "Print with newline." },
  { word: "super", role: "Reserved for inheritance (not yet implemented)." },
];
