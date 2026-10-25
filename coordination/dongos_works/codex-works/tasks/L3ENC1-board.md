# L3ENC1 — L3A纯ELF补齐XMM原子及受限无操作数指令

负责人：codex。状态：待领取。

继续L3，补齐现有nasm_program实际生成的movdqu、lock cmpxchg/xadd、pause/int3/lfence/sfence/mfence到内建assembler与x86 encoder。保持严格操作数/输出原子性，debug/release真实编译执行、NASM独立字节对照和错误操作数负控。仅关闭本编码差集，不外推全L3或新G6。

## 可修改文件

- `lang/bootstrap/x86_encode.dg`
- `lang/bootstrap/native_assembler.dg`
- `lang/tests/test_l3_extended_encoding.py`
- `codex-works/deliveries/L3ENC1.md`

## 定向验收

- `module:lang.tests.test_l3_extended_encoding`

交付：`codex-works/deliveries/L3ENC1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
