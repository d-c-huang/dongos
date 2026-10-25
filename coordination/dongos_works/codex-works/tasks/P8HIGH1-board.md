# P8HIGH1 — 高地址UEFI加载与低地址页表交接兼容修复

负责人：codex。状态：待领取。

用户Intel真机R2报告S00/START/E01_LOADED_IMAGE_RANGE。原已交付PE默认首选0x140000000(5GiB)，当前self检查拒绝>4GiB；E01也共用于HandleProtocol失败，新增实际base/size/status可见取证。不做删除安全检查式修复：允许已验证自身包含entry的高地址映像，在最终map/EBS前分配独立低地址EfiLoaderCode页，复制无外部引用的交接代码及私有GDT，先跳入低页才切CR3；切换后不能访问原PE、高EFI栈或原GDT。保留BootInfo/服务/trace ABI、低4GiB映射、2MiB内核、GOP严格要求、EBS无固件回调封存。独立原生验证range/copy/bounds/坏体，实际低/高载入客体须用完整地址证明，正常和hash/missing拒绝均回归。不宣称实际目标硬件通过，更新H介质待插回。声明六文件及build普通产物，不提交推送。

## 可修改文件

- `boot/efi_main.asm`
- `boot/loader_handoff.asm`
- `tests/test_loader_handoff.py`
- `tests/loader_handoff_probe.c`
- `docs/loader-high-address.md`
- `codex-works/deliveries/P8HIGH1.md`

## 定向验收

- `module:tests.test_loader_handoff`
- `module:tests.test_loader_console`
- `module:tests.test_image`

交付：`codex-works/deliveries/P8HIGH1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
