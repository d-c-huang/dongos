"""Native actual device policy: permissions, atomicity, diagnostic ABI and bad bodies."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest
import uuid

from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags, tool

ROOT = Path(__file__).resolve().parents[1]
ROOTS = ("tests", "kernel", "lang/examples", "lang/std")
FIELDS = ("version", "valid", "error_code", "slot", "address", "page",
          "descriptor_index", "kind", "base", "pages", "attributes")


def source_graph():
    pending, seen = [ROOT / "tests/device_policy_probe.dg"], set()
    while pending:
        path = pending.pop().resolve()
        if path in seen:
            continue
        seen.add(path)
        for name in re.findall(r"^\s*import\s+([\w.]+)\s", path.read_text(encoding="utf-8"), re.M):
            candidates = [ROOT / base / (name.replace(".", "/") + ".dg") for base in ROOTS]
            matches = [candidate for candidate in candidates if candidate.is_file()]
            if len(matches) != 1:
                raise AssertionError(f"ambiguous/missing module {name}: {matches}")
            pending.extend(matches)
    return seen


def hashes(paths):
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


class DevicePolicyTests(unittest.TestCase):
    def test_native_independent_conflicts_and_failure_atomicity(self):
        nasm, cc = tool("nasm", "NASM"), tool("gcc", "CC")
        self.assertTrue(nasm and cc, "native device validation requires NASM and SysV-capable GCC")
        directory = ROOT / "build/test/device-policy" / ("run-" + uuid.uuid4().hex[:12])
        directory.mkdir(parents=True)
        graph = source_graph()
        inputs = graph | set((ROOT / "lang/dongc").rglob("*.py")) | {
            ROOT / "lang/tests/test_dongc.py", ROOT / "tests/device_policy_probe.c", Path(__file__).resolve()}
        before = hashes(inputs)
        (directory / "source-before.json").write_text(json.dumps(before, indent=2) + "\n", encoding="utf-8")
        snapshot = directory / "source"
        for path in graph | {ROOT / "tests/device_policy_probe.c"}:
            target = snapshot / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        tool_evidence = {}
        for name, executable in (("nasm", nasm), ("gcc", cc)):
            binary = Path(executable).resolve()
            version = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=20)
            self.assertEqual(0, version.returncode, version.stdout + version.stderr)
            tool_evidence[name] = {"path": str(binary), "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                                   "version": version.stdout + version.stderr}
        (directory / "tools.json").write_text(json.dumps(tool_evidence, indent=2) + "\n", encoding="utf-8")
        commands, results = [], []

        def run(label, command, expected=0):
            result = subprocess.run([str(x) for x in command], cwd=ROOT, capture_output=True, text=True, timeout=40)
            evidence = {"command": [str(x) for x in command], "returncode": result.returncode,
                        "stdout": result.stdout, "stderr": result.stderr}
            commands.append(label)
            (directory / (label + ".json")).write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
            self.assertEqual(expected, result.returncode, f"{label}: {result.stdout}{result.stderr}")
            return result

        def compile_at(source, mode, label):
            compiled = compile_file(source / "tests/device_policy_probe.dg",
                                    roots=[source / base for base in ROOTS], mode=mode)
            self.assertEqual({p.relative_to(ROOT).as_posix() for p in graph},
                             {Path(p).relative_to(source).as_posix() for p in compiled.source_files})
            layouts = {t["full_name"]: t for t in compiled.layout_manifest["types"]}
            self.assertEqual(88, layouts["boot.device_policy.Views"]["size"])
            self.assertEqual(184, layouts["boot.device_policy.Plan"]["size"])
            conflict = layouts["boot.device_policy.Conflict"]
            self.assertEqual((88, 8), (conflict["size"], conflict["alignment"]))
            self.assertEqual([(name, "u64", i * 8, 8) for i, name in enumerate(FIELDS)],
                             [(f["name"], f["type"], f["offset"], f["size"]) for f in conflict["fields"]])
            asm = directory / (label + ".asm")
            asm.write_text(compiled.assembly, encoding="utf-8")
            (directory / (label + "-layout.json")).write_text(json.dumps(compiled.layout_manifest, indent=2) + "\n", encoding="utf-8")
            objects = {}
            for fmt in ("elf64", "win64"):
                obj = directory / (label + (".obj" if fmt == "win64" else ".o"))
                run(label + "-" + fmt, [nasm, "-f", fmt, *nasm_flags(nasm), "-o", obj, asm])
                objects[fmt] = obj
            return objects["win64" if os.name == "nt" else "elf64"]

        def link_run(source, obj, label, optimization, expected=0):
            exe = directory / (label + (".exe" if os.name == "nt" else ""))
            run(label + "-link", [cc, "-std=c11", optimization, "-Wall", "-Wextra", "-Werror",
                "-D__USE_MINGW_ANSI_STDIO=1", *(["-mno-sse"] if os.name == "nt" else ["-no-pie"]),
                source / "tests/device_policy_probe.c", obj, "-o", exe])
            return run(label + "-execute", [exe], expected)

        try:
            for mode in ("debug", "release"):
                obj = compile_at(snapshot, mode, mode)
                for opt in ("-O0", "-O2"):
                    label = mode + opt
                    result = link_run(snapshot, obj, label, opt)
                    self.assertRegex(result.stdout, r"device policy native checks=10[0-9]{2} complete Plan and input guards verified")
                    self.assertRegex(result.stdout, r"device diagnostic native checks=[5-9][0-9] complete 88-byte context, zero-stale, aliases and input guards verified")
                    results.append({"label": label, "stdout": result.stdout})
            policy = snapshot / "kernel/boot/device_policy.dg"
            original = policy.read_text(encoding="utf-8")
            runtime_guard = "if kind != 11 || ((u64_at(raw.ptr,offset + 32) & 0x8000_0000_0000_0000) != 0 && slot != 0) {"
            mutants = (
                ("missing-valid-publication", "compiler_fence();(*conflict).valid=1;", "compiler_fence();"),
                ("truncate-attributes", "attributes:u64_at(raw.ptr,offset+32)",
                 "attributes:(u64_at(raw.ptr,offset+32) as u32) as u64"),
                ("old-reject-runtime-lapic", runtime_guard,
                 "if kind != 11 || (u64_at(raw.ptr,offset + 32) & 0x8000_0000_0000_0000) != 0 {"),
                ("allow-runtime-all-slots", runtime_guard, "if kind != 11 {"),
                ("allow-reserved", runtime_guard,
                 "if (kind != 11 && kind != 0) || ((u64_at(raw.ptr,offset + 32) & 0x8000_0000_0000_0000) != 0 && slot != 0) {"),
                ("allow-ram", runtime_guard,
                 "if (kind != 11 && kind != 7) || ((u64_at(raw.ptr,offset + 32) & 0x8000_0000_0000_0000) != 0 && slot != 0) {"),
            )
            for name, needle, replacement in mutants:
                self.assertEqual(1, original.count(needle), name + " must alter a unique actual body")
                policy.write_text(original.replace(needle, replacement), encoding="utf-8")
                obj = compile_at(snapshot, "release", name)
                result = link_run(snapshot, obj, name, "-O2", expected=1)
                self.assertIn("device policy failure line", result.stderr)
                self.assertNotIn("unexpected panic", result.stderr)
                results.append({"label": name, "rejected_by_actual_execution": True, "stderr": result.stderr})
                policy.write_text(original, encoding="utf-8")
        finally:
            after = hashes(inputs)
            (directory / "source-after.json").write_text(json.dumps(after, indent=2) + "\n", encoding="utf-8")
            self.assertEqual(before, after, "source changed during independent native validation")
            (directory / "summary.json").write_text(json.dumps({"source_stable": before == after,
                "skips": 0, "commands": commands, "results": results}, indent=2) + "\n", encoding="utf-8")
        print(f"device policy evidence: {directory}")
