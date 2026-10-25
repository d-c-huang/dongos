# P8USBADAPT1 交付记录

日期：2026-10-25。实现：codex。范围为任务书声明的四个文件；等待协调器独立验收和集成登记。本记录不声明真机或 QEMU 验收通过。

## 构建与夹具适配

- `tools/build_usb.py` 的 `verify_build()` 对声明了 `usb_only_profile` 的成品调用 `tools.usb_only_profile.verify()`，只读核对默认 services 源图、完整 staged services 源图、USB profile 精确内容和元数据。原有源码 SHA、成品 SHA、正常 runtime7 条件仍执行。成品字节相同不能掩盖缺失或改写的 snapshot。
- CLI 新增显式 `--usb-only`。新构建传递该参数；复用 `--esp` 时必须提供有效 USB-only profile。普通成品不能只靠 CLI 参数重新标记成 USB-only，拒绝发生在镜像创建前。未声明该选项的普通构建继续使用原路径。
- `tests/test_device_manager.py` 的真实坏体隔离复制清单加入 `services/lib/hardware_profile.dg`，并将其纳入运行前后 SHA。保留真实默认模块，不用假模块绕过新增 import；原设备身份、IRQ、回收、launcher 和 mutation 检查继续执行。
- 新增 `tests/test_usb_profile_packaging.py`：有效普通/USB 成品收据区分、相同 artifacts 下的 staged profile 改写/模块改写/模块缺失拒绝、畸形 profile 元数据拒绝、普通 ESP 加 `--usb-only` 不调用镜像创建器。

## Host 兼容性证据

已复核现有日志 `code/build/hardware/usb-only-20261025-r1/host-compatibility.log`，记录命令对应模块为：

```powershell
python -m unittest tests.test_device_manager tests.test_usb_profile_packaging tests.test_usb_block_proxy tests.test_usb_runtime_qemu -v
```

结果：28 tests，22.951s，OK，0 skip。本轮仅复核日志与源码，未重跑这些测试。日志还保留 USB proxy native evidence 路径 `code/build/test/usb-block-proxy/run-3327a766aaac`。

SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `tools/build_usb.py` | `efd0eee33d9389f6bc3d3307ecedc9bf3c1b60a6d9871f4d7024ca2fd43b4b38` |
| `tests/test_device_manager.py` | `bba7eab48cf04e6361d70a7dea49aed126984556037dfa7a7b7913131df3d20d` |
| `tests/test_usb_profile_packaging.py` | `cabcf1400c5b6b3454fcf324fc0ec63024a464de834b3e1d5ee6090fc5bb0de9` |
| `host-compatibility.log` | `5ede15e0c503dd4215c47387c19ab37cb0206e3b5ebbcb86e18bd9c4bd119d63` |

## 关联 P8USBONLY1 runner 静态审查

本轮只读审查 `tests/run_usb_only_hardware_qemu.py`，SHA-256 为 `f610ef7cfc757ba5de93db88e2ca913335fcccc2a5924d71f41c0f3b2957dd6f`。未修改 runner，未执行 VM，未访问物理 U 盘。

- `make_single_media()` 将已验真的 ESP payload 复制到普通 raw MBR 文件中唯一的 0x0c 分区，核对每个 EFI/kernel/services 文件长度和 SHA，校正主/备 VBR hidden sectors。启动命令移除唯一原 vvfat EFI drive；只有 USB port1 的这一个 raw 文件同时承担 EFI 启动和数据，键盘 port2、鼠标 port3，没有第四口引导介质。
- `single_media_command()` 保持 q35 SATA 开启，并增加实际可写 NVMe、AHCI、VirtIO 三个独立 raw 哨兵盘。禁止 preexisting device/普通 drive 被替换掩盖，禁止 snapshot；`topology()` 从实际 QMP 核对四个 backing file、raw 格式、`ro=false` 及 PCI 控制器实例。
- `SingleMediaGuest` 保持 `usb_only=True`，继承原 `UsbGuest.hid()`。必须由 QMP make/release 经过 USB source、input queue 和真实 Terminal 消费产生单个 `a`，鼠标事件必须由 compositor 消费；F12 console 的 `pwd` 必须恰好消费四个 QMP 字符并返回新鲜 `/`。没有 UART 代替 HID 的分支。
- `_BLOCK_SNAPSHOT` 复用原 `UsbGuest.block_snapshot.__code__`，仅在私有 globals 中替换与新物理拓扑对应的三口枚举 oracle，原模块 globals 不变。原 medium/epoch、实际 BOT FLUSH CBW/CSW、全部用户页表 DMA 隔离、私有 lease、FS/block/xHCI channel 和 trusted snapshot 检查均保留；新检查进一步要求 PCI block admission/BAR/DMA/owner/token 为零，以及 FS device/volume 精确等于 MBR logical view。
- 两次启动复用同一个 USB 文件和三个内盘文件。第一次实际 shell 创建、append、删除、sync；停止 QEMU 后独立 FAT oracle 验完整 namespace、引导 payload 和长文件。第二次实际读回，停止后要求整个 USB SHA 与第一次一致。三个可写内盘的完整 SHA 在每次停止及最终清理后都必须等于初始值；全部必需启动和清理 manifest、runner 输入 SHA 也必须通过。
- root 新增的 `--accel/--cpu` 只选择并记录实际启动方式；WHPX 附加 `kernel-irqchip=off`，没有跳过上述契约。静态审查未发现该变更放宽验收门槛。

最终动态结果由协调器的独立主测记录。上述静态审查不替代实际成功的两次启动、HID、磁盘和截图证据。


## AI交付 2026-10-25T10:49:51+00:00 · codex-mcp-14619bbd432c41a6

四个声明路径已落到主源码/正确交付目录。verify_build 精确验证USBservices完整快照，CLI --usb-only不能重标普通ESP，设备管理器坏体fixture加入真实默认profile依赖。host28tests0skip（记录delivery和log），当前提交等待协调器独立2模块复验。未宣称VM/物理桌面通过，R2动态发现输入启动超时已保留，另P8USBSTART1处理，不在此补丁范围。
