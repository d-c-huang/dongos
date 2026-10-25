# P8SYMBOL1：CPU 观察器的 NASM 私有局部符号

CPU 观察器原先把跨对象同名的合法 NASM 宏私有局部符号也当成需要全局唯一的观测字段。`tests/run_cpu_qemu.py` 仅在完成 ELF 表/字符串边界及 UTF8 检查后，忽略 `..@` 前缀且 `info==0`（STB_LOCAL、STT_NOTYPE）的实现标签。普通 local、global、weak、typed-private 的歧义、所需 CPU 符号、表边界与原同值重复策略保持。

`tests.test_cpu_elf_symbols` 用真实 NASM 两对象与 ld.lld 链接 ELF 产生同名不同地址私有符号，核对所需7项真实值；18场景包括普通local冲突、global/weak/private不同binding/type、required冲突/缺失、截断与name越界等负例。旧函数体对同一合法真实ELF实际复现原拒绝。源码前后指纹相同，0skip，证据 `build/test/p8-symbol/run-6a4aa0c1230b/summary.json`。原 `tests.test_cpu_qemu_result` 也通过，证据 `build/hardware/usb-stage-20261025-r2/cpu-reader-regression.log`。

此补充只处理 CPU 观察器，不修改已哈希的 `tools/elf_symbols.py`，不宣称已经解决完整桌面观察链。后续实测证明正常 desktop 链走 generic ELF reader，P8STAGE1 因而另将错误记录逻辑移到单一命名函数消除重复标签，重新构建与复验。CPU 观察器对合法私有标签的兼容修复本身保留，并独立验收；没有生产行为或磁盘变化，没有 VM/Git。


## AI交付 2026-10-25T13:51:22+00:00 · codex-mcp-14619bbd432c41a6

CPU ELF parser仅略..@prefix且info==0的NASM私有local/NOTYPE标签，required/普通local/global/weak/typed私有歧义及bounds/UTF8检查保持。实际NASM2TU+ld ELF18场景和旧函数实际拒绝对照native通过，0skip/source稳定；原CPU结果协议回归通过。只2实现测试+交付文件，未改kernel/tools或VM/Git。该CPU修复不冒称解决normal generic reader，P8STAGE1已另收敛单TU错误helper并重新完整build。请求独立1模块验收。
