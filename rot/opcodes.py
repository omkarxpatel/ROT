"""Bytecode opcode set for the ROT VM (Milestone 2).

Each opcode is a small integer (`IntEnum`) so chunks compare cleanly
and can later be packed into bytes if desired. Instructions are
stored as tuples `(Op, *args)` in `Chunk.code` — an explicit form
that keeps the code easy to read in tests and trace output.

The set will grow as Milestone 2 progresses; right now it covers
literals, variables, and basic arithmetic. See `HANDOFF.md` for the
~30-opcode target.
"""

from __future__ import annotations

from enum import IntEnum


class Op(IntEnum):
    # ─── Stack manipulation ────────────────────────────────────────
    LOAD_CONST = 1   # arg: const-pool index. Pushes constants[idx].
    LOAD_NULL = 2    # Pushes None.
    LOAD_TRUE = 3    # Pushes True.
    LOAD_FALSE = 4   # Pushes False.
    POP = 5          # Pops and discards the top value.
    DUP = 6          # Duplicates the top value (push a copy). Used by
                     # short-circuit `and`/`or` to keep one copy on
                     # the stack while the conditional jump pops the
                     # other.

    # ─── Variables ─────────────────────────────────────────────────
    LOAD_NAME = 10   # arg: name-pool index. Pushes env[name].
    STORE_NAME = 11  # arg: name-pool index. Pops value, sets env[name].

    # ─── Arithmetic ────────────────────────────────────────────────
    ADD = 20         # Pops b, a; pushes a + b (with ROT's string-coercion
                     # semantics — handled in the VM, not here).
    SUB = 21
    MUL = 22
    DIV = 23
    MOD = 24
    NEG = 25         # Unary minus: pops a; pushes -a.

    # ─── Comparison ────────────────────────────────────────────────
    EQ = 30          # Pops b, a; pushes a == b.
    NE = 31
    LT = 32
    LE = 33
    GT = 34
    GE = 35

    # ─── Boolean ───────────────────────────────────────────────────
    NOT = 40         # Pops a; pushes Python's `not a` (truthiness rules
                     # match ROT's tree-walker since both rely on
                     # Python's bool coercion).

    # ─── Collections ───────────────────────────────────────────────
    BUILD_LIST = 60  # arg: count. Pops `count` values, builds a list
                     # (in push order), pushes it.
    BUILD_DICT = 61  # arg: count (number of key/value pairs). Pops 2N
                     # values as alternating key, value pairs (in push
                     # order), builds a dict, pushes it.
    GET_INDEX = 62   # Pops index, pops target, pushes target[index].
                     # Lists: negative indices wrap; out-of-bounds is
                     # an InterpreterError. Dicts: missing key is an
                     # InterpreterError.
    SET_INDEX = 63   # Pops value, pops index, pops target; performs
                     # target[index] = value. Same bounds rules as
                     # GET_INDEX.

    # ─── Control flow ──────────────────────────────────────────────
    # All jumps target an absolute IP (the index into `Chunk.code`).
    # The compiler emits jumps with a placeholder target (`0`) and
    # patches it once the destination IP is known. See
    # `Chunk.patch_jump`.
    JUMP = 50            # arg: target IP. Unconditional jump.
    JUMP_IF_FALSE = 51   # arg: target IP. Pops the top value; if falsy
                         # (Python truthiness), jumps to `target`.
    JUMP_IF_TRUE = 52    # arg: target IP. Pops the top value; if truthy,
                         # jumps to `target`.

    # ─── Iteration ─────────────────────────────────────────────────
    GET_ITER = 70        # Pops a value, calls `iter()` on it, pushes the
                         # iterator. Used by `for x in <expr> { ... }`.
                         # TypeError on a non-iterable becomes an
                         # InterpreterError.
    ITER_NEXT = 71       # arg: target IP. PEEKs the iterator on top of
                         # the stack. If exhausted, JUMPs to `target`
                         # (the iter stays on the stack — the loop's
                         # end cleanup site pops it). Else pushes the
                         # next value, keeping the iter underneath.

    # ─── Function calls ────────────────────────────────────────────
    CALL = 80            # arg: argc. Stack layout at the moment of
                         # dispatch: [..., function, arg1, ..., argN].
                         # Pops argc args + the function value, creates
                         # a new frame whose env binds the function's
                         # parameters to those args, transfers control.
    RETURN_VALUE = 81    # Pops the top of the current frame's stack as
                         # the return value, pops the frame, pushes the
                         # value onto the caller's stack. If there's no
                         # caller (the main frame just returned), halts.

    # ─── Halt ──────────────────────────────────────────────────────
    RETURN = 90      # Halt execution. Top of stack (if any) is the
                     # program's "result" — for a whole program that's
                     # always None.
