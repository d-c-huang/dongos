# P8BSPDIAG1 交付

最新8CPU Intel真机在S19/0停留超过两分钟。S19是正常最后绘屏，后续阶段只记RAM并退休view，不能据此认定BKL死锁。新增显式BSP用户态隔离构建工具和专门验证器；不修改任何正常kernel/service/EFI生产源码或默认策略。

工具从仍通过校验的正常USB-only构建复用完整对象，严格比对33内核对象/7加载器对象及已知NASM/ELF/EFI命令结构，实际由可信模板生成5条命令，无shell执行日志。仅重编services_run.o既有P6_USER_SMP=0选择器，再真实链接kernel/IMG及两个manifest消费者EFI；私有EFI源唯一banner变为BSP DIAG R1 USER SMP OFF。17服务和SERVICES字节不变，无内存图/人为错误注入。输出独立bsp-diagnostic.json，不复制build-inputs.json或冒充正常多核成品。目录/来源/对象/工具/原输入/唯一路径和payload均有验证。

候选工具SHA560d1626cb6b64c792d186d8c4a11b54b6d573a133debec9e6c4e909c96363b1，真实完整normal→diagnostic5命令构建/verify通过（build/hardware/usb-s19-20261026-r1/bsp-builder-preflight-r3）。原r1错误checker把efi_main.obj当成包含未使用digest宏，已按实际数据/完整listing宏消费修正，原失败保留。

便携原生测试SHAaec77008d1556c5ad8e82111d07a8b55a110dc80deea8966fa7c23e45f0a378f，实际预验1test143.233s/0skip通过；23个拒绝/不执行控制，真实NASM/ELF/EFI链接和生产汇编体。其明确synthetic provider与最小PIE服务仅测试构建流水线，不冒充完整OS。证据build/test/bsp-diagnostic/run-3e04e093024d/validation-summary.json，原r1 NASM可选reloc warning失败保留。

根协调器已执行真实正常8CPU完整桌面/键鼠/USB文件/代码/全部8CPU GS/Header/PCID gate，eight-live-r2通过；r1只因末尾trace仍固定4CPU online_mask而失败，已保留，修observer仅改实际8CPU计数和mask，不修改guest。正常成品8CPU QEMU没有复现这张真机停留。

提交时真实BSP诊断8CPU完整VM与正式独立定向复验仍待根执行，不宣称已通过或已写H。root完成后在审查/集成note补实际结果；通过才备份原SanDisk H文件、flush/fsync/完整读回/只读FAT。新版本物理Intel测试仍待用户反馈；隔离成功仅缩小范围，不等同于正常用户多核故障已修复。


## AI交付 2026-10-26T13:31:15+00:00 · codex-mcp-918a30d10dd649bf

4授权文件已完成并冻结，详见codex-works/deliveries/P8BSPDIAG1.md。仅显式BSP隔离构建/独立manifest/真实pipeline测试，不改正常生产源码或默认多核策略。完整normal→diag五命令构建预检通过，原生便携1test143.233s/0skip、23拒绝控制及真实NASM/ELF/EFI已通过，明确synthetic provider仅pipeline测试。root实际正常8CPU完整desktop/HID/FS/8CPU oracle eight-live-r2 PASS；BSP诊断实际VM/正式独立复验尚待执行，H尚未更新，8CPU Intel此新诊断版未测。旧失败保留。
