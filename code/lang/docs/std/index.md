# Dong 标准库参考

<!-- 由 tools/dongdoc.py 生成，请勿手工编辑。 -->

标准库没有自动导入，也没有默认堆；使用前显式 `import` 并给编译器加 `--root lang/std`。

| 模块 | 公开声明 | 说明 |
| --- | ---: | --- |
| [`arch.x86_64`](arch.x86_64.md) | 12 | reviewed external-assembly wrappers for x86-64 hardware. |
| [`core.arena`](core.arena.md) | 4 | caller-supplied linear arena. |
| [`core.bitset`](core.bitset.md) | 4 | allocation-free bitset with LSB-first bit order. |
| [`core.errors`](core.errors.md) | 1 | standard-library error codes shared by all std modules. |
| [`core.fmt`](core.fmt.md) | 5 | buffer/callback formatting without allocation or a global output. |
| [`core.int`](core.int.md) | 6 | usize checked arithmetic and power-of-two alignment helpers. |
| [`core.mem`](core.mem.md) | 4 | raw byte-memory primitives with explicit pointer and length. |
| [`core.slice`](core.slice.md) | 4 | byte-slice helpers. |
| [`core.utf8`](core.utf8.md) | 4 | strict UTF-8 scalar decode/encode and whole-slice validation. |
| [`sync.spin`](sync.spin.md) | 4 | a spin lock over a single u32 cell, built on sequential-consistency atomics and the pause hint. |
