import { cn } from "@/lib/utils";

type Language = "rot" | "python" | "bash" | "text";

interface CodeBlockProps {
  code: string;
  language?: Language;
  /** Optional label rendered above the block (e.g. "ROT" or "Python"). */
  label?: string;
  className?: string;
  /** Show a leading filename/title bar. */
  filename?: string;
}

const ROT_KEYWORDS = new Set([
  "funct",
  "let",
  "if",
  "elseif",
  "else",
  "while",
  "for",
  "in",
  "break",
  "continue",
  "return",
  "class",
  "this",
  "try",
  "catch",
  "finally",
  "throw",
  "import",
  "and",
  "or",
  "not",
  "true",
  "false",
  "null",
  "super",
]);

const ROT_BUILTINS = new Set([
  "cout",
  "coutln",
  "input",
  "read_file",
  "write_file",
  "str",
  "num",
  "chr",
  "ord",
  "abs",
  "min",
  "max",
  "pow",
  "sqrt",
  "floor",
  "ceil",
  "round",
  "pi",
  "e",
  "len",
  "range",
  "append",
  "pop",
  "sum",
  "sorted",
  "reversed",
  "keys",
  "values",
  "items",
  "type",
  "is_num",
  "is_str",
  "is_list",
  "is_dict",
  "is_bool",
  "is_null",
  "is_func",
  "rand_int",
  "rand_float",
  "seed",
  "assert",
  "exit",
]);

const PYTHON_KEYWORDS = new Set([
  "def",
  "if",
  "elif",
  "else",
  "while",
  "for",
  "in",
  "break",
  "continue",
  "return",
  "class",
  "self",
  "try",
  "except",
  "finally",
  "raise",
  "import",
  "from",
  "as",
  "and",
  "or",
  "not",
  "True",
  "False",
  "None",
  "pass",
  "with",
  "yield",
  "lambda",
  "global",
  "nonlocal",
]);

const PYTHON_BUILTINS = new Set([
  "print",
  "len",
  "range",
  "str",
  "int",
  "float",
  "bool",
  "list",
  "dict",
  "tuple",
  "set",
  "abs",
  "min",
  "max",
  "sum",
  "sorted",
  "reversed",
  "type",
  "input",
  "open",
]);

type TokenKind =
  | "keyword"
  | "builtin"
  | "string"
  | "fstring"
  | "number"
  | "comment"
  | "operator"
  | "ident"
  | "plain";

interface Token {
  kind: TokenKind;
  text: string;
}

const TOKEN_CLASS: Record<TokenKind, string> = {
  keyword: "text-purple-400",
  builtin: "text-sky-300",
  string: "text-amber-300",
  fstring: "text-amber-300",
  number: "text-cyan-300",
  comment: "text-zinc-500 italic",
  operator: "text-rose-300",
  ident: "text-foreground",
  plain: "text-foreground",
};

// Operator / punctuation characters we colorize as a unit.
const OPERATOR_CHARS = new Set([
  "+",
  "-",
  "*",
  "/",
  "%",
  "=",
  "<",
  ">",
  "!",
  "&",
  "|",
  "^",
  "~",
  "?",
  ":",
  ".",
  ",",
  ";",
  "(",
  ")",
  "[",
  "]",
  "{",
  "}",
]);

function isIdentStart(ch: string): boolean {
  return /[A-Za-z_]/.test(ch);
}

function isIdentCont(ch: string): boolean {
  return /[A-Za-z0-9_]/.test(ch);
}

function isDigit(ch: string): boolean {
  return ch >= "0" && ch <= "9";
}

/** Tokenize ROT or Python source for highlighting. Comment style: //
 * for ROT, # for Python. Both support single + double quoted strings,
 * triple-quoted Python strings, and f-strings. */
function tokenize(source: string, language: Language): Token[] {
  if (language !== "rot" && language !== "python") {
    return [{ kind: "plain", text: source }];
  }
  const tokens: Token[] = [];
  const len = source.length;
  let i = 0;
  let buffer = "";
  const flush = () => {
    if (buffer.length === 0) return;
    tokens.push({ kind: "plain", text: buffer });
    buffer = "";
  };

  const keywords = language === "rot" ? ROT_KEYWORDS : PYTHON_KEYWORDS;
  const builtins = language === "rot" ? ROT_BUILTINS : PYTHON_BUILTINS;
  const lineCommentPrefix = language === "rot" ? "//" : "#";

  while (i < len) {
    const ch = source[i];
    const next = source[i + 1];

    // Comments.
    if (language === "rot" && ch === "/" && next === "/") {
      flush();
      let j = i;
      while (j < len && source[j] !== "\n") j += 1;
      tokens.push({ kind: "comment", text: source.slice(i, j) });
      i = j;
      continue;
    }
    if (language === "python" && ch === "#") {
      flush();
      let j = i;
      while (j < len && source[j] !== "\n") j += 1;
      tokens.push({ kind: "comment", text: source.slice(i, j) });
      i = j;
      continue;
    }

    // f-string prefix (rot + python share this surface).
    if ((ch === "f" || ch === "F") && (next === '"' || next === "'")) {
      // Only treat as f-string if the f isn't part of a larger ident.
      const prev = i > 0 ? source[i - 1] : "";
      if (!isIdentCont(prev)) {
        flush();
        const quote = next;
        let j = i + 2;
        while (j < len) {
          const c = source[j];
          if (c === "\\" && j + 1 < len) {
            j += 2;
            continue;
          }
          if (c === quote) {
            j += 1;
            break;
          }
          if (c === "\n" && language === "rot") {
            // ROT doesn't support multi-line strings; stop at newline.
            break;
          }
          j += 1;
        }
        tokens.push({ kind: "fstring", text: source.slice(i, j) });
        i = j;
        continue;
      }
    }

    // Strings.
    if (ch === '"' || ch === "'") {
      flush();
      const quote = ch;
      // Python triple-quoted strings.
      if (
        language === "python" &&
        source[i + 1] === quote &&
        source[i + 2] === quote
      ) {
        let j = i + 3;
        while (j + 2 < len) {
          if (
            source[j] === quote &&
            source[j + 1] === quote &&
            source[j + 2] === quote
          ) {
            j += 3;
            break;
          }
          j += 1;
        }
        tokens.push({ kind: "string", text: source.slice(i, j) });
        i = j;
        continue;
      }
      let j = i + 1;
      while (j < len) {
        const c = source[j];
        if (c === "\\" && j + 1 < len) {
          j += 2;
          continue;
        }
        if (c === quote) {
          j += 1;
          break;
        }
        if (c === "\n" && language === "rot") break;
        j += 1;
      }
      tokens.push({ kind: "string", text: source.slice(i, j) });
      i = j;
      continue;
    }

    // Numbers.
    if (isDigit(ch) || (ch === "." && next && isDigit(next))) {
      flush();
      let j = i;
      let sawDot = false;
      while (j < len) {
        const c = source[j];
        if (isDigit(c)) {
          j += 1;
        } else if (c === "." && !sawDot && isDigit(source[j + 1] ?? "")) {
          sawDot = true;
          j += 1;
        } else {
          break;
        }
      }
      tokens.push({ kind: "number", text: source.slice(i, j) });
      i = j;
      continue;
    }

    // Identifiers / keywords / builtins.
    if (isIdentStart(ch)) {
      flush();
      let j = i + 1;
      while (j < len && isIdentCont(source[j])) j += 1;
      const word = source.slice(i, j);
      let kind: TokenKind = "ident";
      if (keywords.has(word)) kind = "keyword";
      else if (builtins.has(word)) kind = "builtin";
      tokens.push({ kind, text: word });
      i = j;
      continue;
    }

    // Operators / punctuation.
    if (OPERATOR_CHARS.has(ch)) {
      flush();
      tokens.push({ kind: "operator", text: ch });
      i += 1;
      continue;
    }

    // Whitespace / fallback.
    buffer += ch;
    i += 1;
    // Mark lineCommentPrefix as touched to satisfy the bundler if it were
    // unused — both branches already consume it above, this is defensive.
    void lineCommentPrefix;
  }
  flush();
  return tokens;
}

export function CodeBlock({
  code,
  language = "rot",
  label,
  filename,
  className,
}: CodeBlockProps) {
  const trimmed = code.replace(/^\n/, "").replace(/\s+$/, "");
  const tokens = tokenize(trimmed, language);

  return (
    <div
      className={cn(
        "overflow-hidden rounded-lg border border-border/60 bg-zinc-950/80 text-[13px] shadow-sm",
        className,
      )}
    >
      {(label || filename) && (
        <div className="flex items-center justify-between border-b border-border/40 bg-zinc-900/60 px-3 py-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
          <span>{filename ?? label}</span>
          {label && filename ? <span>{label}</span> : null}
        </div>
      )}
      <pre className="overflow-x-auto p-4 font-mono leading-relaxed">
        <code>
          {tokens.map((tok, idx) => (
            <span key={idx} className={TOKEN_CLASS[tok.kind]}>
              {tok.text}
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}
