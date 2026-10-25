# P8USBFSTEST1 — 默认 FAT32 依赖夹具适配与独立静态复核

任务：`codex:P8USBFSTEST1`，读取任务书时为 rev 2。本文记录交付和独立审查，不代替协调器的正式验收、集成登记。

## 交付范围

仅修改三个旧测试的依赖清单和隔离源复制：

- `tests/test_fat32.py`：`SOURCES` 增加真实默认 `services/lib/hardware_profile.dg`，并复制到缺失第二 FAT 写入坏体的私有 `services/lib/`。
- `tests/test_fat32_paths.py`：同样纳入源指纹，并复制到缺失 LFN checksum 检查坏体的私有源根。
- `tests/test_fat32_allocation.py`：同样纳入源指纹，并复制到原始/坏体 allocation 私有源根。

独立检查当前 Git diff：三个文件均只新增上述模块依赖和复制逻辑；原坏体算法、预期错误、容量、布局、故障注入、持久化和性能门限没有放宽。本补充任务不修改生产 FAT32 源码、profile 模板或物理介质。

## 原默认行为复验

执行命令：

```text
python -m unittest tests.test_fat32 tests.test_fat32_paths tests.test_fat32_allocation -v
```

执行者为 root；本审查者实际读取完整结果日志和测试源，未重复运行这组已完成测试。

- 12 tests，159.439 秒，全部通过，0 skip。
- 日志：`code/build/hardware/usb-only-20261025-r2/fat-default-tests.log`。
- 三套测试仍在各自 teardown 比较 `source-before.json` / `source-after.json`；新增 profile 已纳入此闭包。
- 原实际源码坏体（漏第二 FAT 更新、漏 LFN checksum、entry scan / restarted cursor）保留，且正常返回断言拒绝，不能因新增 import 的编译失败冒充检测成功。

## 冻结 R2 的补充独立静态审查

审查范围为 `services/fs/fat32.dg`、USB 权限入口及构建 profile 契约。未修改生产源码，未运行 VM 或访问物理盘。未发现阻断 R2 的问题。

### FSInfo 兼容范围

`mount_inner` 仅在 `hardware_profile.USB_ONLY` 为真时允许 primary / backup FSInfo 的 `[488,496)` 两个 32 位提示值不同。两副本各自检查 free hint 为 unknown 或不大于 cluster count，next hint 为 unknown 或位于 `[2,clusters+2)`。USB primary 的 `[4,484)` 和 `[496,508)` 保留字节必须为零；其余 504 bytes 仍逐字节相等，因此 backup 的保留区和签名也不能绕过。

默认 profile 仍比较完整 512 bytes，默认容量和原 matching-reserved 行为保持。两份 BPB、完整 FAT 镜像、链循环/交叉/孤儿、目录树和 LFN 审计没有因 hint 兼容而跳过。提示值不参与分配授权，写入前仍通过原写入协议将两份提示置为 unknown。

关联独立 native 证据：`code/build/test/usb-fat32/run-a42cb0bbb84b`，93.750 秒、0 skip、`source_stable=true`；默认 debug/release 各 3,570 checks，USB 各 8,104 checks。含大卷 stale hints 成功、两副本六种越界拒绝、504 个非 hint 字节分别破坏拒绝、492 个两副本相同 reserved 破坏拒绝，以及真实错误 bitmap 下标坏体。ELF64/COFF 均组装。

root 实际只读真实卷日志已复核：`code/build/hardware/usb-only-20261025-r2/real-volume-mount-after.log`。实际 `fp_mount` 返回 0，ready=1、readonly=0、dirty=0、clusters=1899872，reads=45114、writes=0、flushes=0、bad_io=0，Scratch/Volume canary 正常。此证据确认真实卷的只读挂载和审计；不将其扩称为真机桌面、键鼠或真实介质写入已经通过。

### 位图边界

容量门在读取备份 BPB、FSInfo、FAT 或目录之前检查 `clusters+2 <= FAT_AUDIT_BYTES*8`。所有进入标记的非零 cluster 已由 `chain_length/next` 限制为 `[2,clusters+2)`，因此最大字节下标 `floor((clusters+1)/8)` 严格小于数组长度。最终 allocation pass 使用相同 cluster 边界和 `/8` 下标；清零循环严格小于同一编译期长度。

默认 `FAT_AUDIT_BYTES=32768`，USB 为 2097152；`Scratch.seen`、EMPTY 和 clear 循环来自同一常量。实际布局分别为 Scratch 39656 / 2104040 bytes，使用借用 Scratch，关联 native 检查最大局部栈帧小于 8192 bytes；cap 拒绝路径同时验证 Volume/Scratch 双侧 canary。几何乘法由 32 位 BPB、有效容量及受限 spc 约束，在 u64 中不会溢出。

### 权限默认拒绝

`drivers.device_policy.rank(BLOCK)` 在 USB profile 恒为 0，真实内核 ledger 的 `bind` 必须再次通过该 rank；不能仅靠调用方声明某设备是 block 获授权。`user.devices.admit(role=1)` 与 `grant(id=2)` 的第一条 guard 均在任何状态发布、ECAM/BAR 硬件写入、PTE 或 DMA 操作之前拒绝。

因此 slot 2 的 SELECTED、BAR 映射与 DMA lease 均保持空；后续 MMIO、DMA acquire、AHCI/NVMe enable 和 MSI gate 继续由这些空状态拒绝。syscall 使用真实 CURRENT slot，不能借调用参数冒用 slot 13/4；XHCI 和输入仍经各自身份、绑定、owner、incarnation 和资源门。`block_service.setup` 的 USB 分支执行 `try setup_usb(); return;`，USB 失败直接返回错误，没有转回 PCI block 的回退路径。

此结论范围是 DongOS 不授予内部 PCI 存储新的控制权限；PCI inventory/configuration 的只读枚举仍然存在。关联 native policy 证据见 `code/build/test/usb-only-profile/run-3a34ae465f76`，实际 ledger 及四类真实 guard/策略坏体覆盖；硬件入口 native probe 只执行实际第一 guard 片段，不冒称执行了宿主不可运行的完整特权 grant 例程。

### 构建快照契约

`tools.usb_only_profile` 固定默认 false/32768 与 USB true/2097152 的完整字节模板；源和 staged DG 全图、metadata、链接/路径及精确模板在生成和最终 verify 时校验。默认源模块不被改写，staged 图仅允许此模块变更。

独立只读复核 R2：108 个原始 DG 和 108 个 staged DG 匹配；内核编译 roots 与全部 17 个 CPL3 DG 入口均使用同一个 `R2/source/usb-only-services`。`build_service` 拒绝快照外的入口，解析器对多 root 的同名模块报错；成功返回前再次 verify，外层构建输入有变动则失败。R2 `build-inputs.json` 为 `source_unchanged=true`，对其 metadata 执行只读 verify 成功。

契约边界：同一快照指 services DG 图；ASM、链接脚本及 std 使用主树并由外层指纹约束。前后指纹服务于可信本地构建来源绑定，不能防止主动攻击者在编译读取期间临时篡改后恢复；本任务未引入此类威胁模型要求。

## 结论

P8USBFSTEST1 的三个旧测试仅作必要依赖夹具适配，原验证强度保留，已有 12 tests / 0 skip 的实际通过记录。冻结 R2 的 FSInfo 兼容、位图边界、USB 权限拒绝和 profile 来源契约独立静态审查无阻断项。协调器验收和集成状态由 root 按最新 rev 单独登记。


## AI交付 2026-10-25T10:50:24+00:00 · codex-mcp-14619bbd432c41a6

三旧FAT测试fixture新增真实lib.hardware_profile默认依赖并覆盖fingerprint/私有坏体树，原oracle和mutations不变。主目录代码已落盘；host tests.test_fat32/test_fat32_paths/test_fat32_allocation全部12tests/159.439s/0skip，交付记录保存log/hash与静态审查。请协调器独立三模块复验；未据此宣称桌面动态通过。
