# P678USBBAS2 — [P6/P7/P8] 当前源码正常 USB 镜像的完整客体回归

负责人：codex。状态：待领取。

冻结当前源码及正常无console overlay的runtime7 USB-only镜像，在一次性QEMU虚盘和匹配固件运行已有run_usb_only_hardware_qemu，核对完整桌面、键鼠、文件持久化、内部盘哨兵。另运行runner --selftest。保留实际阶段和失败。协调者运行客体，定向check只宿主；不写物理盘，不替代P6 KVM时限、P8真机或既有P8BOOTCONSOLE1返修。只写交付。

## 可修改文件

- `codex-works/deliveries/P678USBBAS2.md`

## 定向验收

- `module:tests.test_usb_startup_budget`

交付：`codex-works/deliveries/P678USBBAS2.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
