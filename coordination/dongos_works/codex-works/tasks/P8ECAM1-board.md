# P8ECAM1 — 可信MCFG Runtime type11 ECAM兼容与S15拒绝上下文

负责人：codex。状态：待领取。

新真机S15 PCI DISCOVERY FIRST ERROR050A0002 CPU8，真实链preflight_discovery/discover/hardware/configuration_read/read32/configuration_address/window/mmio_range，仅读ECAM vendor/class/header，无BAR/角色绑定/DMA授予。Denied可能descriptor type/Runtime、retained framebuffer或MCFG边界，Runtime很可疑但尚无原descriptor不能冒称实机根因确诊。仅增加ecam&&kind11&&完整请求位于可信MCFG范围的Runtime兼容，Reserved0 Runtime仍拒，所有BAR ecam=false Runtime仍拒/非11-RAM/MCFG边界/FB排除/权限9及map前guard不变。当前无EFI runtime调用、allocator只非runtime7、新root无Runtime宽WB alias，原WINDOW supervisor WRITE|UC/NX不变，不改EFI服务/安全/DMA/deadline。纯DG BSS新增versioned128B PCI_CONFLICT(first-Denied sticky)16q：version valid reason error physical bytes ecam descriptor_index kind base pages attrs mcfg_first mcfg_end framebuffer_base framebuffer_bytes；reason1descriptor 2FB 3bounds，仅ecam路径记录，valid最后发布，无外调/分配/硬件效果。ASM entry通过真实编译器pub var全局符号读取此固定BSS，S15/error050a2/version1/valid1/ecam1且error相等才显示紧凑14行原因物理范围/UEFI/MCFG/FB，绝不解引用字段地址，低分辨率安全原Gate/ABI/首次error不变。新增真实raw64/mmio_range/configuration_address/window/read32 native harness，只隔离startup/paging/invlpg/最终volatile_load等硬件边界，覆盖12mask类型两用途/非0首bus/边界FB/0副作用/raw只读/context原值及坏体正常oracle拒绝；扩展原bootprogress实际renderer像素守卫。独立新ECAM/bootprogress/framebuffer/stable-readonly/xhci/AHCI/NVMe定向复验0skip/source稳定。root正常USB-only两boot原完整HID/FS/CPU gate及私有EFI真实MCFG Runtime type11描述符兼容实际发现后正常boot，旧拒绝私有kernel反控S15/versionedcontext/屏幕原始descriptor逐字一致，normal objects/磁盘不变/全部VM停。原SanDisk H已确认插回，验证后备份fsync全readback/readonlyFAT正常成品发布，private不发布，任务验收集成与Git沿既有授权。

## 可修改文件

- `kernel/user/devices.dg`
- `include/boot_progress.inc`
- `kernel/entry.asm`
- `tests/test_ecam_mmio.py`
- `tests/ecam_mmio_probe.c`
- `tests/test_boot_progress.py`
- `tests/boot_progress_probe.c`
- `docs/hardware-ecam-runtime.md`
- `codex-works/deliveries/P8ECAM1.md`

## 定向验收

- `module:tests.test_ecam_mmio`
- `module:tests.test_boot_progress`
- `module:tests.test_framebuffer_gate`
- `module:tests.test_user_smp_readonly`
- `module:tests.test_xhci_kernel`
- `module:tests.test_ahci_broker`
- `module:tests.test_nvme_broker`

交付：`codex-works/deliveries/P8ECAM1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
