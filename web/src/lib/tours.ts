// Guided tours for the playground. Each tour is a fixed program + a
// line-keyed caption table. When a tour is active, the playground
// runs in Animate mode at a tour-friendly speed and shows the current
// line's caption above the Step Detail card.
//
// Captions are keyed by `statement_line` (the line of the snapshot
// currently being executed). If the active line has no caption, the
// most recently shown caption persists — keeps the banner stable
// during follow-up steps that share a logical phase.

export interface Tour {
  key: string;
  label: string;
  blurb: string;
  source: string;
  // Map from source line number (1-indexed) to caption text. Caption
  // shows when the active snapshot's `statement_line` matches a key.
  linesToCaption: Record<number, string>;
  // Suggested auto-play speed in ms-per-step. Tours run slower than
  // the default 400ms so the captions have time to land.
  speedMs?: number;
}

const TOUR_COUNTING: Tour = {
  key: "tour-counting",
  label: "Counting to three",
  blurb: "Variables, while loops, and stdout — the smallest interesting program.",
  source: `i = 1
while (i <= 3) {
    coutln(i)
    i = i + 1
}
`,
  linesToCaption: {
    1: "First we bind `i = 1`. `i` lives in the global scope. As the loop runs it'll keep changing in place — not a new binding each time.",
    2: "The `while` keyword evaluates its condition. The interpreter walks the scope chain looking for `i`, finds it, and compares with 3. If true, the body runs.",
    3: "`coutln` is a builtin — it prints its argument and adds a newline. Watch the Output panel grow.",
    4: "Mutating the variable in place. This is the same binding being updated — not a new local. Look at the env diff turn amber.",
  },
  speedMs: 900,
};

const TOUR_FUNCTIONS: Tour = {
  key: "tour-functions",
  label: "Functions and call frames",
  blurb: "Recursive factorial. Watch new call frames push onto the scope chain.",
  source: `funct factorial(n) {
    if (n <= 1) {
        return 1
    }
    return n * factorial(n - 1)
}

coutln(factorial(4))
`,
  linesToCaption: {
    1: "Defining `factorial`. The body isn't run yet; it's stored as a callable value bound to the name. Functions are values in ROT, like in Python or JavaScript.",
    2: "The recursive base case. When `n` reaches 1 we stop calling ourselves and start unwinding.",
    3: "Returning 1 pops the current call frame. The caller picks up where it left off, multiplies its `n` by what we returned, and returns again.",
    5: "The recursive call. A new call frame pushes onto the scope chain — its own `n`, its own locals, a parent pointing at the global scope. Watch the env panel.",
    8: "Kicks the whole thing off. By the bottom of the call we'll have nested four frames deep. The final result — 24 — gets printed.",
  },
  speedMs: 1000,
};

const TOUR_CLASSES: Tour = {
  key: "tour-classes",
  label: "Classes and instances",
  blurb: "A small Counter class. Watch `this` bind, methods dispatch, and fields update.",
  source: `class Counter {
    init(start) {
        this.n = start
    }
    tick() {
        this.n = this.n + 1
    }
}

c = Counter(10)
c.tick()
c.tick()
coutln(c.n)
`,
  linesToCaption: {
    1: "Defining a class. `Counter` is now a class value with two methods: `init` (run when you construct an instance) and `tick`.",
    3: "Inside `init`, `this` refers to the brand-new instance being constructed. We set its `n` field — instances are mutable.",
    6: "`tick` updates the instance's `n`. `this` here means whichever instance called `c.tick()`.",
    10: "`Counter(10)` constructs an instance: a fresh object is allocated, then `init` runs with `this` bound to it. We get back the populated instance.",
    11: "`c.tick()` is the method dispatch — find `tick` on the instance's class, call it with `this = c`. Field-update happens in place.",
    13: "Reading the field at the end. Counter was 10, ticked twice, so the printed result is 12.",
  },
  speedMs: 1000,
};

export const TOURS: Tour[] = [TOUR_COUNTING, TOUR_FUNCTIONS, TOUR_CLASSES];

export function findTour(key: string | null | undefined): Tour | null {
  if (!key) return null;
  return TOURS.find((t) => t.key === key) ?? null;
}

// Given a tour and a snapshot's `statement_line`, return the caption
// that should show. Searches downward from the active line for the
// nearest registered line — this way captions persist across follow-up
// steps that don't have their own caption entry.
//
// We walk the lines in DESCENDING order so a caption registered on a
// higher line wins over a default. Returns null when no caption is
// registered for any line ≤ the active line (e.g. before the first
// statement runs).
export function captionFor(tour: Tour, activeLine: number): string | null {
  let best: { line: number; text: string } | null = null;
  for (const [k, v] of Object.entries(tour.linesToCaption)) {
    const line = Number(k);
    if (line <= activeLine && (best === null || line > best.line)) {
      best = { line, text: v };
    }
  }
  return best?.text ?? null;
}
