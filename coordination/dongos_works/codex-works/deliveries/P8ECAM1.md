# P8ECAM1 交付

真机最新照片为 S15 PCI DISCOVERY、0x050A0002、8 CPU。源码链路确认失败在只读 ECAM 发现阶段；现有照片不足以证明具体描述符，Runtime type11 是结合此前同机平台设备信息提出并独立验证的兼容假设。

仅在可信已校验 MCFG 的完整配置请求内允许 Runtime type11。BAR/DMA 的 Runtime 拒绝、Runtime Reserved/RAM/Code/Data 拒绝、原物理边界/FB 排除/映射前守卫均保留。新增首个 ECAM Denied 的128B私有固定 BSS 上下文，原因/原描述符/MCFG/FB 数值在精确 S15 Denied 时绘制14行；字段地址不解引用。

实际编译发现 Dong `pub var` 不导出 ELF global，故采用相同声明文件内的纯导出访问器返回固定 BSS 地址，避免改变编译器、构建器或扩大文件范围。实际 release getter 指令、16字段布局、entry 与真实 Dong provider 完整链接及 ABI 均由原生探针验证。

预验：`tests.test_ecam_mmio` 1 test、0 skip；debug/release × O0/O2 各214 cases，44 ELF/COFF 汇编、24实际原生执行、10种实际编译坏体均正常被拒。证据 `build/test/ecam-mmio/run-fbff9413b009/validation-summary.json`。`tests.test_boot_progress` 1 test、0 skip；O0/O2 各318 cases/5743 checks、14坏体×2及4 hook坏体均拒绝，保留原236 cases。证据 `build/test/boot-progress/run-967b4bc75867/result.json`。旧的直接数据符号尝试及超时/夹具失败日志保留，没有作为通过证据。

正常 USB-only runtime7/test=false 镜像构建通过，原完整桌面/键鼠/文件系统双启动已通过（`build/hardware/usb-ecam-20261026-r1/live-full/result.json`），真实状态23/failed0/error0/view0/cpus4、88B及128B冲突上下文均零，真实校验 MCFG 也已保存。现有四个跨模块旧夹具在 P8ECAMTEST1 中更新纯依赖/ABI及UTF-8复制；其失败记录保留，最终以协调器独立定向复验为准。

根协调器另外执行 Runtime ECAM 实际固件地图正例及旧规则 S15 上下文反例；私有候选不写 U 盘。验收和介质回执以协调器后续审查/集成记录为准。交付时尚未写入 H:；实机是否越过 S15、进入桌面和支持 USB 键鼠，仍须用户复测。


## AI交付 2026-10-26T12:18:28+00:00 · codex-mcp-918a30d10dd649bf

9个授权文件已完成并冻结；详见 codex-works/deliveries/P8ECAM1.md。仅可信MCFG内Runtime type11 ECAM兼容，原BAR/DMA Runtime拒绝保留；首个拒绝128B上下文与S15精确条件14行显示。Dong pubvar ELF-local故使用纯导出固定BSS getter，同范围文件，无编译器/builder改动。原生ECAM214 cases×4和10坏体、屏幕318 cases/5743checks×2和14坏体×2均通过，0skip。正常完整USB-only双启动通过。四旧夹具由独立P8ECAMTEST1适配，正式定向复验待其冻结后排队。真实RuntimeECAM正例/旧规则反例尚待root实际VM验证；H尚未更新，实机桌面未确认。
