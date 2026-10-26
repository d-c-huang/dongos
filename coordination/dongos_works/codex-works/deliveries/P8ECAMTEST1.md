# P8ECAMTEST1 — 旧 native 夹具依赖适配

任务：`codex:P8ECAMTEST1`，实现依据领取时的 rev2 原任务书。本文冻结时预验进程尚未全部结束，**不宣称四模块总通过，也不代表独立验收或集成**。后续实际结果由根审查 note 补充；正式独立复验以协调器作业为准。

## 范围

仅修改以下四个 Python 测试文件，另提交本文。未修改生产代码、既有 C/DG 探针、AHCI fixture 文件、新 `test_ecam_mmio.py` / `ecam_mmio_probe.c`、协调器状态/索引。未运行 OS/VM、未写 USB、未执行 Git 变更。

| 文件（相对于 code/） | SHA-256 |
| --- | --- |
| tests/test_user_smp_readonly.py | 3f94c28c534d9af1ae82c41213b3fe6e6472d8d8096fb1fe94db60ff1cdba8cb |
| tests/test_xhci_kernel.py | 319a87c1cd9ba11fc4c363e60cc08592ca12b98add94a85d1cc192ec0e2ede7a |
| tests/test_ahci_broker.py | 61740f435652b0bcac7e97d7e03a8d2eeb338da0d3294e9ed6672a3128dbc410 |
| tests/test_nvme_broker.py | ee0ff50278fb6259b586538bcdd116e896318628bfdaeb6d6f21c3eae87af17e |

四文件冻结字节均为 ASCII，亦为合法 UTF-8。生产源码及原 fixture 内容未转码或重写。

## 保留的旧失败与原因

原日志完整保留：`code/build/hardware/usb-ecam-20261026-r1/native-regression.log`。原运行共 8 项、6 errors，包含额外 framebuffer 项；本任务对应其中四模块的 7 项。

1. readonly `test_actual_policy_bridge_and_real_bad_controls`：旧 `copy_graph` 从生产读取 UTF-8，却以 Windows 默认编码写 staged DG。实际失败副本位于 `build/test/p6-readonly-native/run-76fb1f978095/debug-normal/kernel/mm/errors.dg`；生产 em dash 的 UTF-8 字节 `E2 80 94` 被写成 `A1 AA`，编译器在 byte 13 报非法 UTF-8。该副本的 `mm/phys_buddy.dg` 亦受默认编码影响。生产原文件合法 UTF-8。
2. readonly `test_same_page_preflight_uses_actual_pte_flags`：提取的真实 `configuration_address` 新增调用 `record_configuration_denied`，旧夹具未提供该真实依赖。
3. xHCI 的实际正常/坏体两项：生产 `device_host` 新增 DMA 上下文，旧 memory fixture 缺失真实 `DmaLease` 类型及相关 ABI。
4. AHCI 与 NVMe：真实 `grant` 引用了 `hardware_profile.USB_ONLY`，旧硬编码 fixture envelope 缺少对应 import 和实际模块。

## 适配内容与契约

- readonly 使用本文件局部等价依赖遍历器，保留原递归 import/override 语义，显式以 UTF-8 读写 staged DG；本套生成的 DG/C/ASM 源码也显式 UTF-8。未修改共享 copier 或其它测试文件。PTE 夹具直接带入生产的完整 `ConfigurationConflict` 声明、初始化、纯 getter、真实 denial helper，再执行原 `configuration_address` 与 `configuration_read_stable`；未 stub 或移除边界检查。
- xHCI 从生产 `user.memory` 提取真实 `DmaLease`、`EMPTY_DMA`、DMA 状态常量、`dma_snapshot` 完整体，以及所需真实 `Process`、初始化存储、`processes`、`generation` getter。该 grant fixture 不发布 process/DMA retirement lease；其零初始化状态与真实拒绝检查保留。现有 native allocator/物理 I/O 边界及授权、DMA、BAR、身份、隔离、隔离后重用等受测函数均不变。新增实际 memory 源码纳入该套前后哈希检查。通用 `dependencies` helper 未改变，专用 ECAM 测试仍使用其原行为。
- AHCI/NVMe 仅向 envelope 增加真实 `lib.hardware_profile` import，将 `services/lib/hardware_profile.dg` 原始字节复制到每个独立 fixture 根的 `lib/hardware_profile.dg`，并逐次断言字节相同；实际默认模块也纳入前后源码哈希。没有伪造 USB_ONLY 常量或篡改 USB_ONLY 策略。真实 grant/capwalk 字节提取与坏体改动规则均保留。
- 原有断言和反例保持：readonly 9 个实际策略/bridge 坏体与 2 个 PTE 坏体；xHCI 4 个实际授权/隔离坏体及正常 16 场景；AHCI 初始 command-clear readback 坏体；NVMe 4 个 capwalk/readback/control-width 坏体。原 rc1、oracle 文本、无 panic、失败前零破坏性事件、BAR/DMA 拒绝、PTE 标志/PA/cold-window 等断言均未删除或放宽。
- 四套继续只作原声明的 native 策略/事务检查；真实 ECAM guard、映射次序和 denial context 的专门原生测试由冻结的 `tests.test_ecam_mmio` 承担。

## 截至本文冻结的实际预验

第一轮命令：

```text
python -m unittest tests.test_user_smp_readonly tests.test_xhci_kernel tests.test_ahci_broker tests.test_nvme_broker -v
```

日志：`code/build/hardware/usb-ecam-20261026-r1/fixture-adapt-first.log`。该进程已预加载第一次 xHCI Python 版本；其新增 import 未分行，原 copier 只认行首 import，因此其中两项 xHCI 保留了 missing `user.abi` 的中间失败。冻结源码已将新增真实 imports 各自分行，未改 copier 或放宽契约；该旧进程日志不作为冻结 xHCI 的成功证据。

已完成并实际通过：

- readonly actual policy/bridge：20 个 native 执行，正常 rc0、9 个坏体在 debug/release 均 rc1；`build/test/p6-readonly-native/run-d1891d0bc930/validation-summary.json` 为 passed=true、sources_unchanged=true。
- readonly actual PTE preflight：6 个 native 执行，正常及 2 个坏体各 debug/release；`build/test/p6-ecam-preflight-native/run-a12b8b6a319b/validation-summary.json` 为 passed=true。
- 第一轮 xHCI 的独立 unmodified kernel/launcher 编译项已通过。
- 冻结 xHCI 源码的直接实际 fixture DG debug 编译成功，路径 `build/test/p8-xhci-fixture-compile/run-c5604cac5527`。

冻结源码的 xHCI 单模块定向重跑正在进行：

```text
python -m unittest tests.test_xhci_kernel -v
```

日志：`code/build/hardware/usb-ecam-20261026-r1/fixture-adapt-xhci-final.log`。本文冻结时实际正常授权/隔离项、实际坏体项已显示 ok，unmodified 编译项尚在执行。AHCI/NVMe 第一轮总进程仍在执行；本文不预先记为通过。根协调器可并行启动正式独立复验，后续最终预验数字由审查 note 记录。


## AI交付 2026-10-26T12:27:31+00:00 · codex-mcp-918a30d10dd649bf

四授权旧夹具已按真实依赖/ABI和UTF-8复制修复并冻结，详见codex-works/deliveries/P8ECAMTEST1.md。原正常及坏体主体/断言保留，AHCI/NVMe补原hardware_profile字节，xHCI保留真实DmaLease及fail-closed getter，readonly保留真实拒绝context。当前预验尚未全部结束，未宣称总通过；旧6ERROR及首轮预加载旧xHCI依赖错误记录保留。申请独立四模块定向复验。
