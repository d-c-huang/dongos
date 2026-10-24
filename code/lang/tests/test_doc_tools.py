"""dongdoc, dong_doctest and dong_explain; also keeps lang/docs compiling and current."""
from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "lang" / "docs"


def load_tool(name: str):
    spec = importlib.util.spec_from_file_location(f"doc_tools_{name}", ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through it
    spec.loader.exec_module(module)
    return module


dongdoc = load_tool("dongdoc")
doctest_tool = load_tool("dong_doctest")
explain = load_tool("dong_explain")


def run(main, argv, stdin: str = ""):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), patch("sys.stdin", io.StringIO(stdin)):
        status = main(argv)
    return status, out.getvalue(), err.getvalue()


SAMPLE = """// geo.shapes — integer shapes for the doc generator test.
// Second sentence stays out of the summary.

module geo.shapes;

import geo.base;

// A rectangle. Fields are spelled out in full.
pub struct Rect {
    pub width: u64,
    height: u64,
}

// Not documented because it is private.
struct Hidden { value: u8 }

pub const ORIGIN: Rect = Rect { width: 0, height: 0 };

// Area of r. Uses wrapping, two's-
// complement multiplication.
pub fn area(r: *const Rect) u64 {
    unsafe { return wrapping_mul((*r).width, (*r).height); }
}

fn helper() u64 { return 1; }

// Grows in place.
pub fn (self: *Rect) grow(by: u64) void {
    unsafe { (*self).width += by; }
}

pub unsafe extern "sysv64" ("c_draw") fn draw(r: *const Rect) void;

pub error Degenerate = 0x7000_0001;
"""


class DongDocTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "src"
        (self.root / "geo").mkdir(parents=True)
        (self.root / "geo" / "shapes.dg").write_text(SAMPLE, encoding="utf-8", newline="\n")
        (self.root / "geo" / "base.dg").write_text("module geo.base;\n", encoding="utf-8")
        self.output = Path(self.temporary.name) / "out"

    def tearDown(self):
        self.temporary.cleanup()

    def page(self):
        pages = dongdoc.build([self.root], self.output, "Test")
        return pages[self.output / "geo.shapes.md"], pages[self.output / "index.md"]

    def test_public_items_comments_and_signatures(self):
        page, index = self.page()
        self.assertIn("integer shapes for the doc generator test.", index)
        self.assertNotIn("Second sentence", index)
        self.assertIn("pub struct Rect {\n    pub width: u64,\n    height: u64,\n}", page)
        self.assertIn("pub fn area(r: *const Rect) u64\n```", page)  # body stripped
        self.assertIn("Area of r. Uses wrapping, two's-complement multiplication.", page)  # no space at hyphen
        self.assertIn("### `Rect.grow`", page)
        self.assertIn("pub const ORIGIN: Rect = Rect { width: 0, height: 0 };", page)
        self.assertIn("pub error Degenerate = 0x7000_0001;", page)
        self.assertIn("依赖：`geo.base`", page)
        self.assertNotIn("Hidden", page)
        self.assertNotIn("helper", page)

    def test_unsafe_and_extern_marked(self):
        page, _ = self.page()
        self.assertIn("| [`draw`](#fn-draw) | 函数 ⚠unsafe |", page)
        self.assertNotIn("| [`area`](#fn-area) | 函数 ⚠unsafe |", page)
        self.assertIn("```dong ignore\npub unsafe extern", page)

    def test_check_mode_reports_stale_then_fresh(self):
        argv = ["--root", str(self.root), "--output", str(self.output)]
        self.assertEqual(run(dongdoc.main, argv + ["--check"])[0], 1)
        self.assertEqual(run(dongdoc.main, argv)[0], 0)
        self.assertEqual(run(dongdoc.main, argv + ["--check"])[0], 0)
        (self.root / "geo" / "shapes.dg").write_text(SAMPLE.replace("A rectangle.", "A box."), encoding="utf-8")
        status, out, _ = run(dongdoc.main, argv + ["--check"])
        self.assertEqual(status, 1)
        self.assertIn("geo.shapes.md", out)

    def test_syntax_error_is_reported(self):
        (self.root / "geo" / "base.dg").write_text("module geo.base;\nfn (\n", encoding="utf-8")
        status, _, err = run(dongdoc.main, ["--root", str(self.root), "--output", str(self.output)])
        self.assertEqual(status, 1)
        self.assertIn("error[E0101]", err)
        self.assertFalse(self.output.exists())

    def test_repository_std_reference_is_current(self):
        status, out, _ = run(dongdoc.main, ["--root", str(ROOT / "lang/std"), "--output", str(DOCS / "std"), "--check"])
        self.assertEqual(status, 0, out)


class DocTestToolTests(unittest.TestCase):
    def check(self, text: str):
        path = Path("sample.md")
        return doctest_tool.run_document(path, doctest_tool.extract(path, text))

    def test_success_failure_and_error_expectations(self):
        outcomes = self.check(
            "```dong\nmodule a;\nfn f() u64 { return 1; }\n```\n"
            "```dong error=E0201 line=2\nmodule b;\nfn f() u64 { return x; }\n```\n"
            "```dong error=E0301\nmodule c;\nfn f() u64 { return x; }\n```\n"
            "```dong error=E0201 line=1\nmodule d;\nfn f() u64 { return x; }\n```\n"
            "```dong error=E0201\nmodule e;\nfn f() u64 { return 1; }\n```\n"
            "```dong\nmodule f;\nfn f() u64 { return y; }\n```\n"
            "```dong ignore\nnot even dong\n```\n"
            "```text\nmodule ignored;\n```\n")
        self.assertEqual([o.passed for o in outcomes], [True, True, False, False, False, False, True])
        self.assertTrue(outcomes[-1].skipped)
        self.assertIn("expected E0301, got E0201", outcomes[2].detail)
        self.assertIn("expected E0201 at line 1", outcomes[3].detail)
        self.assertIn("but the example compiled", outcomes[4].detail)
        self.assertEqual(outcomes[0].example.line, 2)

    def test_later_blocks_import_earlier_successes_and_std(self):
        outcomes = self.check(
            "```dong\nmodule lib.util;\npub fn one() u64 { return 1; }\n```\n"
            "```dong error=E0101\nmodule lib.util;\npub fn one() u64 { return 2 }\n```\n"
            "```dong\nmodule lib.app;\nimport lib.util;\nimport core.slice as slice;\n"
            "fn f() u64 { if slice.equal(\"a\", \"a\") { return util.one(); } return 0; }\n```\n")
        self.assertTrue(all(o.passed for o in outcomes), [o.detail for o in outcomes])

    def test_release_mode_attribute(self):
        source = "module r;\nconst X: u8 = 255;\nfn f(a: u8) u8 { return a + X; }\n"
        outcomes = self.check(f"```dong release\n{source}```\n")
        self.assertTrue(outcomes[0].passed)
        self.assertTrue(outcomes[0].example.release)

    def test_invalid_attributes_and_fences(self):
        with self.assertRaisesRegex(doctest_tool.UsageError, "unknown example attribute"):
            doctest_tool.extract(Path("x.md"), "```dong fast\n```\n")
        with self.assertRaisesRegex(doctest_tool.UsageError, "line= requires error="):
            doctest_tool.extract(Path("x.md"), "```dong line=3\n```\n")
        with self.assertRaisesRegex(doctest_tool.UsageError, "unterminated"):
            doctest_tool.extract(Path("x.md"), "```dong\nmodule a;\n")

    def test_missing_module_declaration(self):
        outcomes = self.check("```dong\nfn f() u64 { return 1; }\n```\n")
        self.assertFalse(outcomes[0].passed)
        self.assertIn("module", outcomes[0].detail)

    def test_repository_documents_compile(self):
        status, out, err = run(doctest_tool.main, [str(DOCS)])
        self.assertEqual(status, 0, out + err)
        self.assertRegex(out, r"[1-9]\d* passed, 0 failed")


class ExplainTests(unittest.TestCase):
    def test_catalog_covers_every_compiler_code(self):
        used = set()
        for path in (ROOT / "lang" / "dongc").glob("*.py"):
            used |= set(re.findall(r'"(E\d{4})"', path.read_text(encoding="utf-8")))
        entries = explain.load()
        self.assertTrue(used)
        self.assertEqual(sorted(used - set(entries)), [])
        for code, (title, body) in entries.items():
            self.assertTrue(title and body, code)

    def test_single_code_and_markers(self):
        status, out, _ = run(explain.main, ["e0401"])
        self.assertEqual(status, 0)
        self.assertIn("E0401: 可能未初始化", out)
        self.assertIn("```dong  ✗ 触发 E0401", out)
        self.assertIn("```dong  ✓ 正确写法", out)
        self.assertNotIn("error=", out)

    def test_stdin_diagnostics_from_both_compilers(self):
        diagnostics = ("a.dg:2:21: error[E0201]: undefined name 'x'\n"
                       "b.dg:1:1: E0301: operand types differ\n"
                       "c.dg:3:3: error[E0201]: again\n")
        status, out, _ = run(explain.main, ["-"], stdin=diagnostics)
        self.assertEqual(status, 0)
        self.assertTrue(out.startswith(diagnostics))
        self.assertEqual(out.count("E0201: 名称错误"), 1)
        self.assertIn("E0301: 类型错误", out)

    def test_unknown_code_and_list(self):
        status, _, err = run(explain.main, ["E9999"])
        self.assertEqual(status, 1)
        self.assertIn("unknown code E9999", err)
        status, out, _ = run(explain.main, ["--list"])
        self.assertEqual(status, 0)
        self.assertEqual(len(out.splitlines()), len(explain.load()))


if __name__ == "__main__":
    unittest.main()
