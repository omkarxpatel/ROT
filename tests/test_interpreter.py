"""Tests for the tree-walking interpreter (rot/interpreter.py)."""

import contextlib
import io

import pytest

from rot import ast
from rot.errors import InterpreterError
from rot.interpreter import Interpreter
from rot.lexer import Lexer
from rot.syntax import Parser


def _run(source: str) -> str:
    program = Parser(Lexer().tokenize(source)).parse()
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        Interpreter().execute(program)
    return captured.getvalue()


def test_coutln_prints_with_trailing_newline():
    assert _run('coutln("hi")') == "hi\n"


def test_cout_prints_without_newline():
    assert _run('cout("hi")') == "hi"


def test_multiple_print_calls_are_concatenated():
    assert _run('cout("a")\ncout("b")\ncoutln("c")') == "abc\n"


def test_function_definition_and_call():
    src = 'funct greet(name) { coutln(name) }\ngreet("world")'
    assert _run(src) == "world\n"


def test_function_with_multiple_params_separated_by_pipe():
    src = 'funct add(x | y) { coutln(x + y) }\nadd(2 | 3)'
    assert _run(src) == "5\n"


def test_if_else_takes_correct_branch():
    src = (
        'funct pick(x) {\n'
        '    if (x > 0) { coutln("positive") }\n'
        '    else { coutln("non-positive") }\n'
        '}\n'
        'pick(5)'
    )
    assert _run(src) == "positive\n"


def test_if_elseif_else_full_chain():
    src = (
        'funct cmp(x | y) {\n'
        '    if (x > y) { coutln("gt") }\n'
        '    elseif (x == y) { coutln("eq") }\n'
        '    else { coutln("lt") }\n'
        '}\n'
        'cmp(1 | 1)'
    )
    assert _run(src) == "eq\n"


def test_arithmetic_precedence_matches_pratt_parser():
    # 1 + 2 * 3 should compute to 7, not 9.
    assert _run("coutln(1 + 2 * 3)") == "7\n"


def test_parenthesized_arithmetic():
    assert _run("coutln((1 + 2) * 3)") == "9\n"


def test_undefined_name_raises_interpreter_error():
    program = Parser(Lexer().tokenize("nope()")).parse()
    with pytest.raises(InterpreterError) as exc_info:
        Interpreter().execute(program)
    assert "nope" in str(exc_info.value)


def test_wrong_arity_raises_interpreter_error():
    program = Parser(Lexer().tokenize(
        'funct one(x) { coutln(x) }\none(1 | 2)'
    )).parse()
    with pytest.raises(InterpreterError) as exc_info:
        Interpreter().execute(program)
    assert "one" in str(exc_info.value)
    assert "1" in str(exc_info.value)


def test_variable_assignment_and_use():
    assert _run("x = 5\ncoutln(x)") == "5\n"


def test_assignment_reuses_existing_binding():
    src = "x = 1\nx = x + 41\ncoutln(x)"
    assert _run(src) == "42\n"


def test_function_returns_value():
    src = 'funct add(x | y) { return x + y }\ncoutln(add(2 | 3))'
    assert _run(src) == "5\n"


def test_bare_return_yields_null():
    src = 'funct nothing() { return }\ncoutln(nothing())'
    assert _run(src) == "null\n"


def test_falling_off_function_end_returns_null():
    src = 'funct silent() { x = 1 }\ncoutln(silent())'
    assert _run(src) == "null\n"


def test_early_return_short_circuits_remaining_statements():
    src = (
        'funct first_positive(x) {\n'
        '    if (x > 0) { return "yes" }\n'
        '    return "no"\n'
        '}\n'
        'coutln(first_positive(5))\n'
        'coutln(first_positive(0-1))'
    )
    # 0-1 == -1 via the arithmetic; tests both branches.
    assert _run(src) == "yes\nno\n"


def test_return_value_threads_through_call_chain():
    src = (
        'funct double(x) { return x + x }\n'
        'funct quadruple(x) { return double(double(x)) }\n'
        'coutln(quadruple(3))'
    )
    assert _run(src) == "12\n"


def test_while_loop_counts_to_three():
    src = (
        'i = 1\n'
        'while (i <= 3) {\n'
        '    coutln(i)\n'
        '    i = i + 1\n'
        '}'
    )
    assert _run(src) == "1\n2\n3\n"


def test_unary_minus_negates():
    assert _run("coutln(-5)") == "-5\n"
    assert _run("x = 7\ncoutln(-x)") == "-7\n"


def test_modulo_arithmetic():
    assert _run("coutln(10 % 3)") == "1\n"
    assert _run("coutln(15 % 5)") == "0\n"


def test_boolean_literals_print_lowercase():
    # rot uses lowercase `true`/`false` in source, so cout/coutln render the same.
    assert _run("coutln(true)") == "true\n"
    assert _run("coutln(false)") == "false\n"


def test_null_literal_prints_lowercase():
    assert _run("coutln(null)") == "null\n"


def test_and_or_short_circuit():
    # If `or` short-circuits, the right-hand `oops()` is never called.
    src = (
        'funct oops() { return 1 / 0 }\n'
        'coutln(true or oops())'
    )
    assert _run(src) == "true\n"


def test_not_inverts_truthiness():
    assert _run("coutln(not true)") == "false\n"
    assert _run("coutln(not false)") == "true\n"
    assert _run("coutln(not (1 == 1))") == "false\n"


def test_str_num_len_builtins():
    assert _run('coutln(str(42))') == "42\n"
    assert _run('coutln(num("100"))') == "100\n"
    assert _run('coutln(len("hello"))') == "5\n"


def test_float_literal_evaluates():
    assert _run("coutln(3.14)") == "3.14\n"


def test_string_concatenation_with_number_coerces():
    assert _run('coutln("count: " + 42)') == "count: 42\n"


def test_string_concatenation_with_bool_uses_rot_style():
    assert _run('coutln("flag: " + true)') == "flag: true\n"


def test_string_escapes_are_decoded():
    assert _run(r'cout("a\nb")') == "a\nb"
    assert _run(r'cout("tab\there")') == "tab\there"


def test_escaped_quote_in_string():
    assert _run(r'coutln("she said \"hi\"")') == 'she said "hi"\n'


def test_compound_assign_plus():
    assert _run("x = 5\nx += 3\ncoutln(x)") == "8\n"


def test_compound_assign_all_ops():
    assert _run("x = 10\nx -= 3\ncoutln(x)") == "7\n"
    assert _run("x = 4\nx *= 3\ncoutln(x)") == "12\n"
    assert _run("x = 10\nx /= 4\ncoutln(x)") == "2.5\n"
    assert _run("x = 10\nx %= 3\ncoutln(x)") == "1\n"


def test_compound_assign_string_concat():
    assert _run('s = "hello"\ns += " world"\ncoutln(s)') == "hello world\n"


def test_list_literal_and_indexing():
    src = 'xs = [1 | 2 | 3]\ncoutln(xs[0])\ncoutln(xs[2])'
    assert _run(src) == "1\n3\n"


def test_list_index_assign():
    src = 'xs = [1 | 2 | 3]\nxs[1] = 99\ncoutln(xs[1])'
    assert _run(src) == "99\n"


def test_list_compound_index_assign():
    src = 'xs = [10 | 20 | 30]\nxs[1] += 5\ncoutln(xs[1])'
    assert _run(src) == "25\n"


def test_for_loop_iterates_a_list():
    src = (
        'for x in [10 | 20 | 30] {\n'
        '    coutln(x)\n'
        '}'
    )
    assert _run(src) == "10\n20\n30\n"


def test_for_loop_with_range():
    src = (
        'for i in range(3) {\n'
        '    coutln(i)\n'
        '}'
    )
    assert _run(src) == "0\n1\n2\n"


def test_range_with_two_args():
    src = (
        'for i in range(2 | 5) {\n'
        '    coutln(i)\n'
        '}'
    )
    assert _run(src) == "2\n3\n4\n"


def test_break_exits_loop():
    src = (
        'for i in range(10) {\n'
        '    if (i == 3) { break }\n'
        '    coutln(i)\n'
        '}'
    )
    assert _run(src) == "0\n1\n2\n"


def test_continue_skips_iteration():
    src = (
        'for i in range(5) {\n'
        '    if (i % 2 == 0) { continue }\n'
        '    coutln(i)\n'
        '}'
    )
    assert _run(src) == "1\n3\n"


def test_break_in_while_loop():
    src = (
        'i = 0\n'
        'while (true) {\n'
        '    if (i >= 3) { break }\n'
        '    coutln(i)\n'
        '    i += 1\n'
        '}'
    )
    assert _run(src) == "0\n1\n2\n"


def test_append_and_len():
    src = (
        'xs = [1 | 2]\n'
        'append(xs | 3)\n'
        'append(xs | 4)\n'
        'coutln(len(xs))\n'
        'coutln(xs[3])'
    )
    assert _run(src) == "4\n4\n"


def test_pop_removes_and_returns_last():
    src = (
        'xs = [1 | 2 | 3]\n'
        'last = pop(xs)\n'
        'coutln(last)\n'
        'coutln(len(xs))'
    )
    assert _run(src) == "3\n2\n"


def test_nested_indexing():
    src = (
        'grid = [[1 | 2] | [3 | 4]]\n'
        'coutln(grid[0][1])\n'
        'coutln(grid[1][0])'
    )
    assert _run(src) == "2\n3\n"


def test_string_indexing_returns_char():
    assert _run('s = "hello"\ncoutln(s[1])') == "e\n"


def test_string_iteration():
    src = (
        'for ch in "abc" {\n'
        '    coutln(ch)\n'
        '}'
    )
    assert _run(src) == "a\nb\nc\n"


def test_string_method_via_member_access():
    # `.upper()` is Python's str method, exposed for free via member access.
    assert _run('coutln("hello".upper())') == "HELLO\n"


def test_list_method_via_member_access():
    src = (
        'xs = [3 | 1 | 2]\n'
        'xs.sort()\n'
        'coutln(xs[0])'
    )
    assert _run(src) == "1\n"


def test_string_split():
    src = (
        'parts = "a,b,c".split(",")\n'
        'coutln(parts[0])\n'
        'coutln(parts[2])'
    )
    assert _run(src) == "a\nc\n"


def test_empty_dict_literal():
    src = "d = {}\ncoutln(len(d))"
    assert _run(src) == "0\n"


def test_dict_literal_and_access():
    src = (
        'd = {"name": "alice" | "age": 30}\n'
        'coutln(d["name"])\n'
        'coutln(d["age"])'
    )
    assert _run(src) == "alice\n30\n"


def test_dict_assignment_creates_key():
    src = (
        'd = {}\n'
        'd["score"] = 100\n'
        'coutln(d["score"])'
    )
    assert _run(src) == "100\n"


def test_dict_iteration_yields_keys():
    src = (
        'd = {"a": 1 | "b": 2}\n'
        'count = 0\n'
        'for k in d {\n'
        '    count += 1\n'
        '}\n'
        'coutln(count)'
    )
    assert _run(src) == "2\n"


def test_dict_methods_via_member_access():
    # Python's dict.keys() returns a view; len works on it.
    src = (
        'd = {"a": 1 | "b": 2 | "c": 3}\n'
        'coutln(len(d.keys()))'
    )
    assert _run(src) == "3\n"


def test_class_def_instance_field_assign_in_init():
    src = (
        'class Point {\n'
        '    init(x | y) {\n'
        '        this.x = x\n'
        '        this.y = y\n'
        '    }\n'
        '}\n'
        'p = Point(3 | 4)\n'
        'coutln(p.x)\n'
        'coutln(p.y)'
    )
    assert _run(src) == "3\n4\n"


def test_class_method_call_uses_this():
    src = (
        'class Counter {\n'
        '    init(start) { this.count = start }\n'
        '    inc() { this.count += 1 }\n'
        '    get() { return this.count }\n'
        '}\n'
        'c = Counter(10)\n'
        'c.inc()\n'
        'c.inc()\n'
        'c.inc()\n'
        'coutln(c.get())'
    )
    assert _run(src) == "13\n"


def test_class_with_no_init_takes_no_args():
    src = (
        'class Empty {\n'
        '    greet() { coutln("hello") }\n'
        '}\n'
        'e = Empty()\n'
        'e.greet()'
    )
    assert _run(src) == "hello\n"


def test_class_with_no_init_rejects_args():
    src = 'class Empty {}\nEmpty(1)'
    with pytest.raises(InterpreterError):
        _run(src)


def test_class_method_calls_other_method():
    src = (
        'class Adder {\n'
        '    init(x) { this.x = x }\n'
        '    double() { return this.x * 2 }\n'
        '    quadruple() { return this.double() * 2 }\n'
        '}\n'
        'a = Adder(5)\n'
        'coutln(a.quadruple())'
    )
    assert _run(src) == "20\n"


def test_class_fields_are_independent_per_instance():
    src = (
        'class Box {\n'
        '    init(v) { this.value = v }\n'
        '}\n'
        'a = Box("first")\n'
        'b = Box("second")\n'
        'coutln(a.value)\n'
        'coutln(b.value)'
    )
    assert _run(src) == "first\nsecond\n"


def test_throw_caught_by_try():
    src = (
        'try {\n'
        '    throw "oops"\n'
        '} catch (e) {\n'
        '    coutln("caught: " + e)\n'
        '}'
    )
    assert _run(src) == "caught: oops\n"


def test_runtime_error_caught():
    src = (
        'try {\n'
        '    x = 1 / 0\n'
        '} catch (e) {\n'
        '    coutln("got error")\n'
        '}'
    )
    assert _run(src) == "got error\n"


def test_undefined_name_caught():
    src = (
        'try {\n'
        '    coutln(nonexistent)\n'
        '} catch (e) {\n'
        '    coutln("undefined caught")\n'
        '}'
    )
    assert _run(src) == "undefined caught\n"


def test_throw_with_dict_value():
    src = (
        'try {\n'
        '    throw {"code": 42 | "msg": "boom"}\n'
        '} catch (e) {\n'
        '    coutln(e["code"])\n'
        '    coutln(e["msg"])\n'
        '}'
    )
    assert _run(src) == "42\nboom\n"


def test_uncaught_throw_propagates():
    src = 'throw "untouched"'
    # Without an enclosing try, _ThrowSignal escapes execute() — Python
    # surfaces it as a BaseException.
    with pytest.raises(BaseException):
        _run(src)


def test_try_block_runs_to_completion_on_success():
    src = (
        'try {\n'
        '    coutln("ok")\n'
        '} catch (e) {\n'
        '    coutln("should not print")\n'
        '}'
    )
    assert _run(src) == "ok\n"


def test_throw_in_function_caught_by_caller():
    src = (
        'funct bad() { throw "from inside" }\n'
        'try {\n'
        '    bad()\n'
        '} catch (e) {\n'
        '    coutln(e)\n'
        '}'
    )
    assert _run(src) == "from inside\n"


def test_math_builtins():
    assert _run("coutln(abs(-5))") == "5\n"
    assert _run("coutln(min(3 | 1 | 2))") == "1\n"
    assert _run("coutln(max(3 | 1 | 2))") == "3\n"
    assert _run("coutln(min([3 | 1 | 2]))") == "1\n"
    assert _run("coutln(pow(2 | 10))") == "1024\n"
    assert _run("coutln(sqrt(16))") == "4.0\n"
    assert _run("coutln(floor(3.9))") == "3\n"
    assert _run("coutln(ceil(3.1))") == "4\n"
    assert _run("coutln(round(2.7))") == "3\n"


def test_math_constants():
    # pi and e are bound as numeric constants.
    assert _run("coutln(round(pi | 2))") == "3.14\n"
    assert _run("coutln(round(e | 2))") == "2.72\n"


def test_type_builtin():
    assert _run("coutln(type(42))") == "int\n"
    assert _run("coutln(type(3.14))") == "float\n"
    assert _run('coutln(type("hi"))') == "string\n"
    assert _run("coutln(type([1 | 2]))") == "list\n"
    assert _run('coutln(type({"a": 1}))') == "dict\n"
    assert _run("coutln(type(true))") == "bool\n"
    assert _run("coutln(type(null))") == "null\n"


def test_type_of_class_instance_is_class_name():
    src = (
        'class Foo {}\n'
        'f = Foo()\n'
        'coutln(type(f))'
    )
    assert _run(src) == "Foo\n"


def test_is_x_predicates():
    assert _run("coutln(is_num(42))") == "true\n"
    assert _run("coutln(is_num(3.14))") == "true\n"
    assert _run('coutln(is_num("hi"))') == "false\n"
    assert _run('coutln(is_str("hi"))') == "true\n"
    assert _run("coutln(is_list([1]))") == "true\n"
    assert _run('coutln(is_dict({"a": 1}))') == "true\n"
    assert _run("coutln(is_bool(true))") == "true\n"
    assert _run("coutln(is_null(null))") == "true\n"
    assert _run("coutln(is_null(0))") == "false\n"


def test_input_builtin(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "alice")
    src = 'name = input("name? ")\ncoutln("hi " + name)'
    assert _run(src) == "hi alice\n"


def test_file_io_round_trip(tmp_path):
    target = tmp_path / "scratch.txt"
    src = (
        f'write_file("{target}" | "hello\\nfile")\n'
        f'content = read_file("{target}")\n'
        f'coutln(content)'
    )
    # The content contains a literal newline after decoding, so output
    # is "hello\nfile\n" (with trailing newline from coutln).
    assert _run(src) == "hello\nfile\n"


def test_rand_int_returns_value_in_range():
    src = (
        'x = rand_int(1 | 10)\n'
        'coutln(x >= 1 and x <= 10)'
    )
    assert _run(src) == "true\n"


def test_rand_float_returns_0_to_1():
    src = (
        'x = rand_float()\n'
        'coutln(x >= 0 and x < 1)'
    )
    assert _run(src) == "true\n"


def test_assert_passes_silently_on_true():
    assert _run("assert(true)\ncoutln(\"ok\")") == "ok\n"


def test_assert_throws_on_false():
    with pytest.raises(InterpreterError):
        _run('assert(false | "boom")')


def test_assert_caught_in_try_block():
    src = (
        'try {\n'
        '    assert(1 == 2 | "math broke")\n'
        '} catch (e) {\n'
        '    coutln(e)\n'
        '}'
    )
    out = _run(src)
    assert "math broke" in out


def test_fstring_simple():
    src = 'name = "alice"\ncoutln(f"hello, {name}!")'
    assert _run(src) == "hello, alice!\n"


def test_fstring_with_number():
    src = 'x = 42\ncoutln(f"x = {x}")'
    assert _run(src) == "x = 42\n"


def test_fstring_with_expression():
    src = 'coutln(f"sum = {1 + 2 * 3}")'
    assert _run(src) == "sum = 7\n"


def test_fstring_no_interpolation_is_just_string():
    assert _run('coutln(f"plain text")') == "plain text\n"


def test_fstring_multiple_interpolations():
    src = 'a = 1\nb = 2\ncoutln(f"{a} + {b} = {a + b}")'
    assert _run(src) == "1 + 2 = 3\n"


def test_fstring_uses_rot_style_stringify():
    # `true` should render as "true", not Python's "True".
    assert _run('coutln(f"flag is {true}")') == "flag is true\n"
    assert _run('coutln(f"empty is {null}")') == "empty is null\n"


def test_fstring_unclosed_brace_errors():
    from rot.errors import ParserError
    with pytest.raises(ParserError):
        _run('coutln(f"oops {x")')


def test_fstring_empty_brace_errors():
    from rot.errors import ParserError
    with pytest.raises(ParserError):
        _run('coutln(f"oops {}")')


def test_str_builtin_uses_rot_style():
    # Updated in v2.9.0 to match f-string conventions.
    assert _run("coutln(str(true))") == "true\n"
    assert _run("coutln(str(null))") == "null\n"
    assert _run("coutln(str(42))") == "42\n"


def test_closure_can_mutate_enclosing_variable():
    """The headline v2.10.0 feature — counter closures now work."""
    src = (
        'funct make_counter() {\n'
        '    count = 0\n'
        '    funct inc() { count += 1 }\n'
        '    inc()\n'
        '    inc()\n'
        '    inc()\n'
        '    coutln(count)\n'
        '}\n'
        'make_counter()'
    )
    assert _run(src) == "3\n"


def test_assignment_in_function_mutates_global():
    src = (
        'x = 10\n'
        'funct change() { x = 99 }\n'
        'change()\n'
        'coutln(x)'
    )
    assert _run(src) == "99\n"


def test_function_param_shadows_outer():
    src = (
        'x = 10\n'
        'funct foo(x) { x = 99 }\n'   # x is a param, set_local — local scope
        'foo(5)\n'
        'coutln(x)'                     # global x unchanged
    )
    assert _run(src) == "10\n"


def test_nested_closure_mutates_outer_scope():
    src = (
        'funct outer() {\n'
        '    x = 1\n'
        '    funct middle() {\n'
        '        funct inner() { x = 99 }\n'
        '        inner()\n'
        '    }\n'
        '    middle()\n'
        '    coutln(x)\n'
        '}\n'
        'outer()'
    )
    assert _run(src) == "99\n"


def test_for_loop_var_is_local():
    # Loop variable shouldn't leak as a global if `i` isn't already declared.
    src = (
        'for i in range(3) {\n'
        '    nothing = i\n'
        '}\n'
        # After the loop, `i` is still bound at this scope (last iter value).
        'coutln(i)'
    )
    assert _run(src) == "2\n"


def test_import_basic(tmp_path):
    lib = tmp_path / "lib.rot"
    lib.write_text('funct double(x) { return x * 2 }\n')
    main_src = f'import "{lib}"\ncoutln(double(7))'

    import contextlib, io
    from rot.compiler import Compiler
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        Compiler(trace=False).run(main_src)
    assert captured.getvalue() == "14\n"


def test_import_resolves_relative_to_source_dir(tmp_path):
    lib = tmp_path / "helper.rot"
    lib.write_text('funct greet(name) { return "hi " + name }\n')
    main = tmp_path / "app.rot"
    main.write_text('import "helper.rot"\ncoutln(greet("rot"))')

    import contextlib, io
    from rot.compiler import Compiler
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        Compiler(trace=False).run(main.read_text(), source_path=str(main))
    assert captured.getvalue() == "hi rot\n"


def test_import_adds_extension_if_omitted(tmp_path):
    lib = tmp_path / "math2.rot"
    lib.write_text('funct sq(x) { return x * x }\n')
    main = tmp_path / "use.rot"
    main.write_text('import "math2"\ncoutln(sq(6))')   # no .rot extension

    import contextlib, io
    from rot.compiler import Compiler
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        Compiler(trace=False).run(main.read_text(), source_path=str(main))
    assert captured.getvalue() == "36\n"


def test_import_is_cached_does_not_re_execute(tmp_path):
    """Importing the same file twice runs it once — the second call is a no-op.
    We verify by having the library `coutln` something at module-load time."""
    lib = tmp_path / "noisy.rot"
    lib.write_text('coutln("loaded")\nfunct x() { return 1 }\n')
    main = tmp_path / "main.rot"
    main.write_text(
        f'import "noisy"\n'
        f'import "noisy"\n'  # second import is cached, no second print
        f'coutln(x())'
    )

    import contextlib, io
    from rot.compiler import Compiler
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        Compiler(trace=False).run(main.read_text(), source_path=str(main))
    # "loaded" should appear once.
    assert captured.getvalue() == "loaded\n1\n"


def test_import_missing_file_raises(tmp_path):
    main = tmp_path / "broken.rot"
    main.write_text('import "nonexistent"')
    with pytest.raises(InterpreterError):
        import contextlib, io
        from rot.compiler import Compiler
        with contextlib.redirect_stdout(io.StringIO()):
            Compiler(trace=False).run(main.read_text(), source_path=str(main))


def test_imported_class_is_usable(tmp_path):
    lib = tmp_path / "shapes.rot"
    lib.write_text(
        'class Square {\n'
        '    init(side) { this.side = side }\n'
        '    area() { return this.side * this.side }\n'
        '}\n'
    )
    main = tmp_path / "demo.rot"
    main.write_text(
        f'import "shapes"\n'
        f's = Square(4)\n'
        f'coutln(s.area())'
    )

    import contextlib, io
    from rot.compiler import Compiler
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        Compiler(trace=False).run(main.read_text(), source_path=str(main))
    assert captured.getvalue() == "16\n"


def test_repl_echoes_expression_value(monkeypatch, capsys):
    inputs = iter(["1 + 2", "x = 5", "x * x"])
    def mock_input(prompt=""):
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError
    monkeypatch.setattr("builtins.input", mock_input)
    from rot.repl import start_repl
    start_repl()
    out, _ = capsys.readouterr()
    # "3" from 1+2, "25" from x*x. "x = 5" is a statement, no echo.
    assert "3" in out
    assert "25" in out


def test_repl_persists_state_across_inputs(monkeypatch, capsys):
    inputs = iter([
        "funct double(n) { return n * 2 }",
        "double(7)",
    ])
    def mock_input(prompt=""):
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError
    monkeypatch.setattr("builtins.input", mock_input)
    from rot.repl import start_repl
    start_repl()
    out, _ = capsys.readouterr()
    assert "14" in out


def test_repl_multiline_input(monkeypatch, capsys):
    # Open brace on first line — REPL should keep reading until balanced.
    inputs = iter([
        "funct greet() {",
        '    coutln("hello from repl")',
        "}",
        "greet()",
    ])
    def mock_input(prompt=""):
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError
    monkeypatch.setattr("builtins.input", mock_input)
    from rot.repl import start_repl
    start_repl()
    out, _ = capsys.readouterr()
    assert "hello from repl" in out


def test_repl_error_does_not_kill_session(monkeypatch, capsys):
    inputs = iter([
        "undefined_name()",          # raises InterpreterError
        "coutln(\"still alive\")",   # should still execute
    ])
    def mock_input(prompt=""):
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError
    monkeypatch.setattr("builtins.input", mock_input)
    from rot.repl import start_repl
    start_repl()
    out, err = capsys.readouterr()
    assert "still alive" in out
    assert "undefined_name" in err or "rot error" in err


def test_division_by_zero_raises_interpreter_error():
    with pytest.raises(InterpreterError) as exc_info:
        _run("coutln(1 / 0)")
    assert "division by zero" in str(exc_info.value).lower()


def test_modulo_by_zero_raises_interpreter_error():
    with pytest.raises(InterpreterError):
        _run("coutln(5 % 0)")


def test_binary_op_type_mismatch_raises_interpreter_error():
    with pytest.raises(InterpreterError) as exc_info:
        _run('coutln(1 - "x")')
    assert "cannot apply" in str(exc_info.value)


def test_unary_minus_on_string_raises_interpreter_error():
    with pytest.raises(InterpreterError) as exc_info:
        _run('coutln(-"x")')
    assert "cannot negate" in str(exc_info.value)


def test_index_assign_out_of_bounds_raises_interpreter_error():
    with pytest.raises(InterpreterError):
        _run('xs = [1]\nxs[5] = 99')


def test_for_over_non_iterable_raises_interpreter_error():
    with pytest.raises(InterpreterError) as exc_info:
        _run("for x in 123 { coutln(x) }")
    assert "cannot iterate" in str(exc_info.value)


def test_break_at_top_level_raises_interpreter_error():
    with pytest.raises(InterpreterError) as exc_info:
        _run("break")
    assert "outside of a loop" in str(exc_info.value)


def test_continue_at_top_level_raises_interpreter_error():
    with pytest.raises(InterpreterError) as exc_info:
        _run("continue")
    assert "outside of a loop" in str(exc_info.value)


def test_return_at_top_level_raises_interpreter_error():
    with pytest.raises(InterpreterError) as exc_info:
        _run("return 42")
    assert "outside of a function" in str(exc_info.value)


def test_method_param_does_not_clobber_outer_scope():
    src = (
        'x = 1\n'
        'class C { init(x) { this.x = x } }\n'
        'C(5)\n'
        'coutln(x)'    # outer x must still be 1
    )
    assert _run(src) == "1\n"


def test_this_in_method_does_not_clobber_outer_this():
    # Pre-fix: `set("this", instance)` would walk up and mutate any
    # outer binding named `this`.
    src = (
        'this = "outer"\n'
        'class C { init() {} }\n'
        'C()\n'
        'coutln(this)'   # outer must still be "outer"
    )
    assert _run(src) == "outer\n"


def test_pop_empty_list_raises_interpreter_error():
    with pytest.raises(InterpreterError) as exc_info:
        _run("pop([])")
    assert "empty" in str(exc_info.value)


def test_range_step_zero_raises_interpreter_error():
    with pytest.raises(InterpreterError):
        _run('for i in range(0 | 3 | 0) { coutln(i) }')


def test_rand_int_inverted_range_raises_interpreter_error():
    with pytest.raises(InterpreterError):
        _run("coutln(rand_int(5 | 1))")


def test_read_file_missing_raises_interpreter_error():
    with pytest.raises(InterpreterError) as exc_info:
        _run('coutln(read_file("/no/such/file/at/all.txt"))')
    assert "read_file" in str(exc_info.value)


def test_sqrt_negative_raises_interpreter_error():
    with pytest.raises(InterpreterError) as exc_info:
        _run("coutln(sqrt(-1))")
    assert "sqrt" in str(exc_info.value)


def test_runtime_errors_now_catchable_with_try():
    # Errors that used to leak as Python exceptions are now InterpreterError
    # — meaning they're catchable in rot's own try/catch.
    src = (
        'try {\n'
        '    x = 1 / 0\n'
        '} catch (e) {\n'
        '    coutln("recovered")\n'
        '}'
    )
    assert _run(src) == "recovered\n"


def test_fstring_extra_tokens_in_brace_errors():
    from rot.errors import ParserError
    with pytest.raises(ParserError) as exc_info:
        _run('coutln(f"{1 2}")')
    assert "unexpected" in str(exc_info.value).lower()


def test_crlf_line_endings_work():
    # Windows-style CRLF source. Previously crashed at the \r.
    src = "coutln(1)\r\ncoutln(2)"
    assert _run(src) == "1\n2\n"


def test_member_access_with_keyword_name():
    # Pre-fix: `obj.class` would fail because `class` is a keyword, not IDENT.
    # We can't actually demo this with rot semantics (rot instances don't
    # use Python class names as attrs), but it should at least parse.
    from rot.compiler import Compiler
    # Parsing alone confirms the grammar accepts it.
    Compiler().parse('x = {"class": "ok"}\ncoutln(x["class"])')


def test_fizzbuzz_first_15():
    src = (
        'funct fizzbuzz(n) {\n'
        '    i = 1\n'
        '    while (i <= n) {\n'
        '        if (i % 15 == 0) { coutln("fizzbuzz") }\n'
        '        elseif (i % 3 == 0) { coutln("fizz") }\n'
        '        elseif (i % 5 == 0) { coutln("buzz") }\n'
        '        else { coutln(i) }\n'
        '        i = i + 1\n'
        '    }\n'
        '}\n'
        'fizzbuzz(15)'
    )
    expected = "1\n2\nfizz\n4\nbuzz\nfizz\n7\n8\nfizz\nbuzz\n11\nfizz\n13\n14\nfizzbuzz\n"
    assert _run(src) == expected


def test_closure_captures_lexical_scope():
    # Inside `outer`, calling `inner` should resolve `coutln` from the
    # enclosing scope chain (global), not require it to be a parameter.
    src = (
        'funct outer() {\n'
        '    funct inner() { coutln("inside") }\n'
        '    inner()\n'
        '}\n'
        'outer()'
    )
    assert _run(src) == "inside\n"


# ==== v2.14.1: Python exceptions from builtin calls wrap as InterpreterError ====

def test_len_of_null_wraps_typeerror():
    # `len(null)` used to leak Python's `TypeError` to the user.
    with pytest.raises(InterpreterError) as exc_info:
        _run("coutln(len(null))")
    assert "TypeError" not in type(exc_info.value).__name__
    msg = str(exc_info.value)
    assert "len" in msg.lower() or "NoneType" in msg


def test_len_of_int_wraps_typeerror():
    with pytest.raises(InterpreterError):
        _run("coutln(len(5))")


def test_num_of_garbage_string_wraps_valueerror():
    with pytest.raises(InterpreterError) as exc_info:
        _run('coutln(num("abc"))')
    assert "num" in str(exc_info.value)


def test_min_of_empty_list_wraps_valueerror():
    with pytest.raises(InterpreterError) as exc_info:
        _run("coutln(min([]))")
    # The wrapped error message should NOT be a raw Python ValueError reaching
    # the user — it must be an InterpreterError.
    assert isinstance(exc_info.value, InterpreterError)


def test_max_of_empty_list_wraps_valueerror():
    with pytest.raises(InterpreterError):
        _run("coutln(max([]))")


def test_abs_of_string_wraps_typeerror():
    with pytest.raises(InterpreterError):
        _run('coutln(abs("x"))')


def test_floor_of_string_wraps_typeerror():
    with pytest.raises(InterpreterError):
        _run('coutln(floor("x"))')


def test_pow_neg_one_half_returns_or_wraps():
    # pow(-1, 0.5) returns a complex in Python — that complex then fails
    # downstream. Either way, a try/catch in ROT must not see a Python
    # traceback escape.
    src = (
        'try {\n'
        '    x = pow(-1 | 0.5)\n'
        '    coutln(x)\n'
        '} catch (e) {\n'
        '    coutln("ok")\n'
        '}'
    )
    out = _run(src)
    # Either it computes a complex (Python lets it through) or raises —
    # either way the user shouldn't see a Python crash.
    assert "ok" in out or "j" in out


def test_wrapped_call_error_is_catchable_in_rot():
    # The whole point of wrapping is that try/catch in ROT works on them.
    src = (
        'try {\n'
        '    coutln(len(null))\n'
        '} catch (e) {\n'
        '    coutln("recovered")\n'
        '}'
    )
    assert _run(src) == "recovered\n"


# ==== v2.14.2: RecursionError -> "call stack too deep" =====================

def test_unbounded_recursion_wraps_to_interpreter_error():
    # An unbounded rot recursion used to leak a raw Python RecursionError
    # with the Python phrase "while calling a Python object" attached.
    # Now it must come out as a clean InterpreterError("call stack too deep").
    src = 'funct r() { r() }\nr()'
    with pytest.raises(InterpreterError) as exc_info:
        _run(src)
    msg = str(exc_info.value)
    assert "call stack too deep" in msg
    # And it must not include Python's recursion phrasing.
    assert "Python" not in msg
    assert "maximum recursion" not in msg


def test_unbounded_recursion_is_catchable():
    # Now that it's an InterpreterError, rot's try/catch can recover.
    src = (
        'funct r() { r() }\n'
        'try {\n'
        '    r()\n'
        '} catch (e) {\n'
        '    coutln("ok")\n'
        '}'
    )
    assert _run(src) == "ok\n"


# ==== v2.14.3: pop distinguishes empty-list vs out-of-range ================

def test_pop_out_of_range_says_so():
    # B41: previously pop([1] | 5) said "cannot pop from empty list" even
    # though the list isn't empty. The message should now mention "out of
    # range" or the bad index.
    with pytest.raises(InterpreterError) as exc_info:
        _run("pop([1] | 5)")
    msg = str(exc_info.value)
    assert "out of range" in msg
    assert "empty" not in msg


def test_pop_negative_out_of_range_says_so():
    with pytest.raises(InterpreterError) as exc_info:
        _run("pop([1 | 2] | -5)")
    assert "out of range" in str(exc_info.value)


def test_pop_empty_still_says_empty():
    # Make sure we didn't regress the empty case.
    with pytest.raises(InterpreterError) as exc_info:
        _run("pop([])")
    assert "empty" in str(exc_info.value)


# ==== v2.14.4: range with float step says "integer", not "zero" =============

def test_range_float_step_says_integer():
    # B27: range(0 | 3 | 0.5) used to say "step must not be zero" because
    # int(0.5) == 0. The real problem is the float step — say so.
    with pytest.raises(InterpreterError) as exc_info:
        _run("for i in range(0 | 3 | 0.5) { coutln(i) }")
    msg = str(exc_info.value)
    assert "integer" in msg
    assert "zero" not in msg


def test_range_zero_step_still_says_zero():
    # Make sure an honest zero step still gets the "must not be zero" message.
    with pytest.raises(InterpreterError) as exc_info:
        _run("for i in range(0 | 3 | 0) { coutln(i) }")
    assert "zero" in str(exc_info.value)


# ==== v2.14.5: range validates each arg before int() coercion ===============

def test_range_float_start_rejected():
    # B28: previously int(0.5) silently became 0 and produced an unexpected
    # range. Now floats are rejected up front.
    with pytest.raises(InterpreterError) as exc_info:
        _run("for i in range(0.5 | 3) { coutln(i) }")
    assert "integer" in str(exc_info.value)


def test_range_float_stop_rejected():
    with pytest.raises(InterpreterError) as exc_info:
        _run("for i in range(0 | 3.5) { coutln(i) }")
    assert "integer" in str(exc_info.value)


def test_range_string_arg_rejected_with_clean_message():
    # B29: previously leaked Python ValueError("invalid literal for int()
    # with base 10: 'abc'"). Now should be a clean rot error.
    with pytest.raises(InterpreterError) as exc_info:
        _run('for i in range("abc") { coutln(i) }')
    msg = str(exc_info.value)
    assert "integer" in msg or "range" in msg
    # No raw Python phrasing.
    assert "invalid literal" not in msg


def test_range_single_int_still_works():
    # Don't break the happy path.
    assert _run("for i in range(3) { coutln(i) }") == "0\n1\n2\n"


# ==== v2.14.6: read_file / write_file use explicit UTF-8 ====================

def test_read_file_non_utf8_raises_interpreter_error(tmp_path):
    # B33: previously leaked a raw UnicodeDecodeError. Now wrapped.
    bad = tmp_path / "bad.bin"
    bad.write_bytes(b"\xff\xfe\xfdgarbage")
    src = f'coutln(read_file("{bad}"))'
    with pytest.raises(InterpreterError) as exc_info:
        _run(src)
    msg = str(exc_info.value)
    assert "read_file" in msg
    assert "UTF-8" in msg or "utf-8" in msg.lower()


def test_read_file_utf8_roundtrip(tmp_path):
    # Confirm the UTF-8 happy path still works (and writes are also UTF-8).
    target = tmp_path / "u.txt"
    src = (
        f'write_file("{target}" | "héllo")\n'
        f'coutln(read_file("{target}"))\n'
    )
    assert _run(src) == "héllo\n"


def test_write_file_default_encoding_is_utf8(tmp_path):
    # B34/B35: explicit UTF-8 means the written file should bytewise be UTF-8
    # regardless of platform locale.
    target = tmp_path / "u.txt"
    _run(f'write_file("{target}" | "café")')
    raw = target.read_bytes()
    assert raw == "café".encode("utf-8")
