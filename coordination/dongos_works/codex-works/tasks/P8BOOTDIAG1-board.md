# P8BOOTDIAG1 — 真机黑屏的UEFI屏幕阶段与错误诊断

负责人：codex。状态：待领取。

用户Intel真机从H盘runtime0启动后黑屏有信号。仅补引导器可见诊断，不推断实际根因或放宽4GiB/映像校验/内存规则。EFI入口在串口前显示版本/S00；读盘、校验、GOP、ACPI等阶段与早期原错误码上屏。首次最终GetMemoryMap/ExitBootServices序列前永久关闭固件打印，包括失败重试和fatal，后续不得调用固件控制台。Microsoft x64 ABI、有限长度ASCII→UTF16、空控制台与错误返回需实际原生执行验证。当前无存储runtime0重建与正常、损坏/缺失映像客体验证；准备新介质但需用户插回H盘后才更新。真实硬件门保持待验。只改声明六文件，build输出另存，原第一次镜像/失败保留。

## 可修改文件

- `boot/efi_main.asm`
- `boot/loader_console.asm`
- `tests/test_loader_console.py`
- `tests/loader_console_probe.c`
- `docs/loader-console.md`
- `codex-works/deliveries/P8BOOTDIAG1.md`

## 定向验收

- `module:tests.test_loader_console`
- `module:tests.test_image`

交付：`codex-works/deliveries/P8BOOTDIAG1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
