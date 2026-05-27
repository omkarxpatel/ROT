import Link from "next/link";

import { CodeBlock } from "@/components/code-block";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";

interface TocItem {
  id: string;
  title: string;
}

const TOC: TocItem[] = [
  { id: "getting-started", title: "Getting started" },
  { id: "hello-world", title: "Hello world" },
  { id: "variables", title: "Variables" },
  { id: "literals", title: "Literals" },
  { id: "operators", title: "Operators" },
  { id: "control-flow", title: "Control flow" },
  { id: "functions", title: "Functions" },
  { id: "classes", title: "Classes" },
  { id: "error-handling", title: "Error handling" },
  { id: "imports", title: "Imports" },
  { id: "fstrings", title: "F-strings" },
  { id: "slicing", title: "Slicing" },
  { id: "builtins", title: "Builtins reference" },
  { id: "repl", title: "The REPL" },
  { id: "errors", title: "Error messages" },
  { id: "reserved-words", title: "Reserved words" },
  { id: "examples", title: "Examples" },
];

export default function DocsPage() {
  return (
    <div className="flex min-h-full flex-col">
      <SiteHeader />
      <div className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6 lg:py-16">
        <header className="mb-12">
          <h1 className="font-mono text-4xl font-semibold tracking-tight">
            Docs
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            A language reference for ROT. Every section is a small example
            with the minimum prose needed to read it. For deeper architecture
            notes, see the{" "}
            <a
              href="https://github.com/omkarxpatel/ROT/blob/main/ARCHITECTURE.md"
              target="_blank"
              rel="noreferrer"
              className="text-foreground underline-offset-4 hover:underline"
            >
              ARCHITECTURE.md
            </a>{" "}
            or the{" "}
            <a
              href="/paper/main.pdf"
              target="_blank"
              rel="noreferrer"
              className="text-foreground underline-offset-4 hover:underline"
            >
              design retrospective paper
            </a>
            .
          </p>
        </header>
        <div className="grid gap-12 lg:grid-cols-[200px_1fr] lg:gap-16">
          <aside className="hidden lg:block">
            <nav className="lg:sticky lg:top-24">
              <div className="text-xs uppercase tracking-wider text-muted-foreground">
                On this page
              </div>
              <ul className="mt-3 space-y-1.5 text-sm">
                {TOC.map((item) => (
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
          <InlineCode>cout</InlineCode> doesn&apos;t.
        </p>
      </Prose>
      <CodeFrame code={`coutln("hello, world")`} />
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
      <CodeFrame
        code={`x = 5         // assigns to whatever 'x' resolves to (or a new global)
let y = 10    // always a fresh local 'y'

funct outer() {
    z = 1
    funct inner() {
        z = z + 1     // chain-walks; mutates outer's z
        let z = 99    // creates a NEW local z that shadows
        return z
    }
    return inner()
}`}
      />
      <Prose>
        <p>
          Builtins like <InlineCode>pi</InlineCode> are immutable —{" "}
          <InlineCode>pi = 3.0</InlineCode> raises. Use{" "}
          <InlineCode>let pi = 3.0</InlineCode> to shadow within a local
          scope.
        </p>
      </Prose>
    </section>
  );
}

function Literals() {
  return (
    <section>
      <SectionHeading id="literals">Literals</SectionHeading>
      <CodeFrame
        code={`// numbers
n = 42
f = 3.14

// strings
s = "hello"
t = 'world'
u = "with\\nescapes\\tand quotes \\"like this\\""

// booleans + null
ok = true
done = false
nothing = null

// lists use '|' as the separator
xs = [1 | 2 | 3]

// dicts use '|' between entries, ':' between key and value
d = {"name": "ada" | "age": 36}`}
      />
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
      <CodeFrame
        code={`if (x > 0) {
    coutln("positive")
} elseif (x < 0) {
    coutln("negative")
} else {
    coutln("zero")
}

while (i < 10) {
    if (i == 3) { i += 1 continue }
    if (i == 7) { break }
    coutln(i)
    i += 1
}

for word in ["a" | "b" | "c"] {
    coutln(word)
}`}
      />
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
      <CodeFrame
        code={`funct add(a | b) {
    return a + b
}

coutln(add(2 | 3))    // 5

funct make_counter() {
    count = 0
    funct tick() {
        count += 1
        return count
    }
    return tick
}

c = make_counter()
coutln(c())   // 1
coutln(c())   // 2`}
      />
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
          <InlineCode>init</InlineCode> is the constructor. Method receiver is{" "}
          <InlineCode>this</InlineCode>, not <InlineCode>self</InlineCode>.
          Inheritance is not yet supported — <InlineCode>super</InlineCode> is
          reserved and produces a clear error.
        </p>
      </Prose>
      <CodeFrame
        code={`class Counter {
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
coutln(c)   // Counter(2)`}
      />
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
      <CodeFrame
        code={`funct parse(s) {
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

// throw any value
try {
    throw {"code": 42 | "msg": "boom"}
} catch (err) {
    coutln(err.msg)
}`}
      />
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
      <CodeFrame
        code={`name = "ada"
coutln(f"hello, {name}")

pi = 3.14159
coutln(f"pi rounded: {pi:.2f}")     // pi rounded: 3.14

n = 7
coutln(f"[{n:>5}]")                 // [    7]
coutln(f"hex {255:x}")              // hex ff
coutln(f"bin {10:08b}")             // bin 00001010

// expressions and slicing also work inside the braces
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
      <CodeFrame
        code={`s = "hello, world"
coutln(s[7:])          // world
coutln(s[:5])          // hello
coutln(s[::-1])        // dlrow ,olleh

xs = [10 | 20 | 30 | 40 | 50]
coutln(xs[1:4])        // [20 | 30 | 40]
coutln(xs[::2])        // [10 | 30 | 50]
coutln(xs[-2:])        // [40 | 50]`}
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
          looks like a Python-ism.
        </p>
      </Prose>
      <CodeFrame
        language="text"
        code={`error: unknown identifier 'print'
  --> example.rot:3:5
   |
 3 |     print("hello")
   |     ^^^^^ did you mean 'cout'?
   |
note: 'print' is Python's stdout function — ROT uses cout / coutln.`}
      />
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
          alongside golden <InlineCode>.expected</InlineCode> outputs:{" "}
          <InlineCode>hello</InlineCode>, <InlineCode>fizzbuzz</InlineCode>,{" "}
          <InlineCode>factorial</InlineCode>,{" "}
          <InlineCode>functions</InlineCode>, <InlineCode>counter</InlineCode>,{" "}
          <InlineCode>sum_list</InlineCode>,{" "}
          <InlineCode>multiple_prints</InlineCode>. Click{" "}
          <Link href="/playground" className="underline-offset-4 hover:underline">
            Try the playground
          </Link>{" "}
          and pick one from the dropdown to run them in the browser.
        </p>
      </Prose>
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
