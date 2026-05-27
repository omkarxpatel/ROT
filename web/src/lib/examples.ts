// Examples bundle. The actual `.rot` source contents are fetched from
// /rot_examples/examples.json at runtime — this file just lists the
// metadata so the dropdown can render before the fetch resolves.

export interface ExampleMeta {
  key: string;
  label: string;
  blurb: string;
}

// The 7 examples in examples/ (mirrored by scripts/copy-rot.mjs).
export const EXAMPLES: ExampleMeta[] = [
  { key: "hello", label: "Hello", blurb: "the smallest rot program" },
  { key: "multiple_prints", label: "Multiple Prints", blurb: "cout vs coutln" },
  { key: "factorial", label: "Factorial", blurb: "recursion + return" },
  { key: "fizzbuzz", label: "FizzBuzz", blurb: "loops + if/elseif/else" },
  { key: "functions", label: "Functions", blurb: "funct, params with |" },
  { key: "sum_list", label: "Sum List", blurb: "lists + for-in + compound assign" },
  { key: "counter", label: "Counter", blurb: "classes, this, init, methods" },
];

let cache: Record<string, string> | null = null;

export async function loadExamples(): Promise<Record<string, string>> {
  if (cache) return cache;
  const r = await fetch("/rot_examples/examples.json", { cache: "force-cache" });
  if (!r.ok) {
    throw new Error(`failed to load examples: ${r.status}`);
  }
  cache = (await r.json()) as Record<string, string>;
  return cache;
}

export const DEFAULT_EXAMPLE_KEY = "fizzbuzz";

// Inlined fizzbuzz source so the editor renders something before
// /rot_examples/examples.json is fetched. Kept in sync with
// examples/fizzbuzz.rot.
export const DEFAULT_EXAMPLE_SOURCE = `funct fizzbuzz(n) {
    i = 1
    while (i <= n) {
        if (i % 15 == 0) {
            coutln("fizzbuzz")
        }
        elseif (i % 3 == 0) {
            coutln("fizz")
        }
        elseif (i % 5 == 0) {
            coutln("buzz")
        }
        else {
            coutln(i)
        }
        i = i + 1
    }
}

fizzbuzz(15)
`;
