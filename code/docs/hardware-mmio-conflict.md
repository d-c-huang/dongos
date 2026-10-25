# S01 / 0x03030002 的原始内存冲突现场

用户真机记录：`DONGOS BOOT FAILED`、`DONGOS S01 IRQ PREPARE`、CPU COUNT=8、FIRST ERROR=`0x03030002`。这是 `boot.device_policy.RamConflict`，不是 CPU 数量限制。它发生于设备映射规划，尚未安装设备 PTE、invalidate 或读取 IRQ 控制器寄存器。

触发条件是：完整 4 KiB 设备页与已验证 UEFI 描述符重叠，且该描述符类型不为 11（MMIO），或 attributes 的 RUNTIME 位为 1。错误名不能证明该页就是普通 RAM。当前缺少设备/描述符事实，因此 P8MMIO1 只增加现场，不放宽任何接受条件，也不删除设备或改变超时。

UEFI 将 Reserved 标为不可用；ACPI 的 AddressRangeReserved 与具体 EFI 类型不是一一对应。不能仅凭常见 APIC 保留范围，就把任意 Reserved、RAM 或 Runtime 页转换为设备映射。依据：[UEFI 2.10 内存类型](https://uefi.org/specs/UEFI/2.10/07_Services_Boot_Services.html)、[ACPI 6.5 系统地址图](https://uefi.org/specs/ACPI/6.5/15_System_Address_Map_Interfaces.html)。

## 诊断记录与原合同

新增版本化 `Conflict` 为11个u64/88B，字段顺序为 version、valid、error_code、slot、address、page、descriptor_index、kind、base、pages、attributes。DG 的 error 是保留字，因此第三字段使用 error_code；ASM/C 的线性偏移保持16。所有字段由真实失败分支从原描述符读取；先填 valid=0，再以 compiler_fence 后的 valid=1 发布。

原 Plan=184B、Views=88B、plan/prepare旧接口及输入/Plan失败原子性保持。新 nullable 诊断接口在写输出前检查对齐、88B加法及与所有输入/Plan/View/Space的别名，合法非冲突调用清空上下文，非法/别名输出完全不写。只有真实 RamConflict 记录有效；错误之后不进行 query/map/invalidate。没有 MMIO 探测，也不创建额外页表别名。

runtime7 通过新的三参数导出传入独立内核 BSS；其它级别继续原两参数入口。屏幕只在 S01、失败标记、首错、记录版本/valid及记录错误均精确匹配时绘制现场；所有文字仍在原 screen_draw Gate/几何检查内，无额外 framebuffer writer。新紧凑布局的标签x56、全64位值x238、y120..344，640×480也有界；没有有效现场时保留原阶段画面，首次CPL3前禁用规则不改。

## 真机屏幕字段

所有数值均为16位十六进制：

| 字段 | 含义 |
| --- | --- |
| STAGE / CPU COUNT / FIRST ERROR | 原启动阶段、ACPI CPU数与首错 |
| DEVICE SLOT | 0=LAPIC；1–8=IOAPIC；9=HPET；A=内存型PM timer |
| DEV ADDRESS | ACPI提供的寄存器地址；整页地址为其低12位清零 |
| UEFI TYPE | 原始描述符类型；0=Reserved，7=Conventional，B=MMIO |
| DESC BASE | 冲突描述符物理基址 |
| DESC PAGES | 4KiB页数，范围为[base,base+pages×4096) |
| EFI ATTR | 完整原始attributes，最高位是RUNTIME |

屏上不猜设备型号或替代地址。descriptor_index 与整页地址也保存在88B记录中，供源绑定观察器审查。

## 验证和介质

原生探针执行真实 planner/prepare/renderer：debug/release及O0/O2、所有设备槽与类型、stride48、多页/半开区间、完整64位、输出别名和原子性、失败零query/map/invalidate、Gate/禁用/边界及真正删guard/截断等坏体。正常 runtime7 USB-only 两次启动继续运行原桌面、HID、文件持久性、代码/池/页表及CPU健康强观察器，并确认成功时上下文全零。

受控冲突 VM 只在私有 EFI 候选交付的内存图中加入/标记 LAPIC Reserved 描述符；正常 kernel/IMG/服务字节不变。必须由真实 planner 产生 error2 和现场，核对原图、88B记录及屏幕像素，不通过主机写 guest 内存或寄存器。该候选不发布到H:，不能当作真实机器的内存图。

完整证据位于 `build/hardware/usb-mmio-20261025-r1/`。独立复验和实际启动都通过后，核对原 SanDisk serial `4C530000010320109015`，备份当前 H: 的4文件，再显式flush/fsync并逐文件全SHA读回、原卷只读审计；不格式化、改分区或写内盘。

下一次实机启动仍以 `USB DIAG R4` 为引导入口。若仍在 S01 失败，请拍下整屏，尤其 DEVICE SLOT、DEV ADDRESS、UEFI TYPE、DESC BASE、DESC PAGES、EFI ATTR。这次现场会决定后续兼容修复；当前不宣告真机桌面/HID或冲突已解决。
