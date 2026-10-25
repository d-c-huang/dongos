# P8HIGH1：高地址EFI交接修复

用户真机R2报S00／START／E01。原PE首选5GiB，与原自身必须低于4GiB的检查冲突；E01也含协议失败，当前修复新增完整协议status／base／size可见证据，不把猜测写成用户实测地址。

两生产文件已完成：严格非空／无溢出／entry包含检查允许合法高EFI；最终map/EBS前分配LoaderCode低页并复制284B完全自包含交接块。原高PE在旧CR3下跳低，再由私有GDT／低栈切CR3／CS。原服务trace参数、BootInfo、低映射、2MiB内核及GOP限制保持，E14错误在低blob有界串口保留。原CPU／内存内核逐字不变。

独立作者 `tests.test_loader_handoff` 2项8.885s零skip，ELF64／COFF实际汇编，正常O0/O2各36,969检查；8个真实RIP目标闭包、复制边界／唯一patch、MS ABI保持、4个实际坏体正常返回1拒绝，最终源稳定。首轮在E14追加期间出现source_stable失败，原件保留。另原console及image兼容预检15项零skip通过。

实际五场景见 `code/build/hardware/high-loader-20261025-r2/guest-results.json`：

- 新版低地址正常：完整原PASS。
- 新版真实5GiB正常：完整原PASS。
- 新版真实5GiB篡改／缺失：严格原E08／E04，未进入内核。
- 原R2真实5GiB：复现原E01，halt RIP=0x140001d73。

均未修改客体内存／寄存器，所有原文件前后SHA一致、进程退出。新正常两次实际pmemsave读回BootInfo／memory map／低handoff页／当前CR3页表：类型1唯一覆盖handoff，不与Conventional重叠，GDTR自算值正确，原PE虚拟地址已不在新私有根。所有命令、串口、截图及原始物理读文件保留。

最终EFI SHA256 `29bdd9c4ac712c35c5d99fbf11d924705d1fa69515fefee86396896a66938c2f`；DONGOS.IMG沿用 `3c904bb48dfac9c1c8dab1861e392a68e1323eaed9eefff036bd81bb396a4455`。准备为USB DIAG R3。提交时尚待协调器独立复验，尚未登记验收。H盘当前未插回，因此未写入新介质。未重新跑完整runtime7矩阵，不宣称真机／暖PCID／物理WC验收，未提交或推送Git。


## AI交付 2026-10-25T09:34:23+00:00 · codex-mcp-14619bbd432c41a6

高地址EFI低页交接六声明文件完成；独立作者原生2项零skip、兼容15项零skip。真实旧版5GiB E01复现，新版低/高PASS、5GiB E08/E04拒绝及原始物理内存审计通过；最终EFI29bdd9c4…，实际硬件仍待用户再试。正式复验待排，H当前不在开发机，未写新介质。
