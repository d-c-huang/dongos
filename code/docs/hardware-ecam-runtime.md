# S15 PCI ECAM 访问与 Runtime MMIO

新真机照片明确停在 S15 PCI DISCOVERY，error=0x050A0002、CPU COUNT=8。此阶段的调用链为 `device_host.preflight_discovery → discover → hardware → devices.configuration_read → read32 → configuration_address/window/mmio_range`。它只读 PCI 配置头，不访问 BAR、不绑定设备角色，也不授权 DMA。

当前错误可来自配置描述符类型/Runtime 属性、framebuffer 重叠或 MCFG 边界。此前同机 LAPIC/IOAPIC/HPET 均带 Runtime，故 Runtime ECAM 是重点怀疑项；这张照片本身仍没有证明具体描述符或分支，不能把推测写成实机根因。

## 定向兼容

Runtime 兼容仅适用于 `ecam && kind==11 && 请求完整位于已校验 MCFG aperture`。读取地址仍由可信 ACPI 的 base、bus、device、function 生成，沿原配置边界校验，映射为内核 supervisor WRITE|UNCACHED、NX 的单页 WINDOW。当前 EBS 后路径不调用 EFI RuntimeServices/SetVirtualAddressMap，RAM 分配仍只使用非 Runtime type7，新根不为 Runtime 范围批量建立 WB/HHDM 别名。

`ecam=false` 的 BAR/DMA 路径继续拒绝所有 Runtime 描述符。Reserved(type0) 的非 Runtime MCFG 旧例外保留，Runtime Reserved 仍拒绝；RAM、Runtime Code/Data 和其他非11类型仍拒绝。配置窗口边界、framebuffer 排除、物理限制及 map 前 guard 顺序不变。本次不改固件服务、设备接管、DMA 归属、安全规则或超时。

## 只读拒绝上下文

`user.devices.PCI_CONFLICT` 是私有128B固定 BSS，16个 u64：version、valid、reason、error_code、physical、bytes、ecam、descriptor_index、kind、base、pages、attributes、mcfg_first、mcfg_end、framebuffer_base、framebuffer_bytes。只记录首个 ECAM Denied，valid 最后发布；成功和非 ECAM 拒绝不写该记录。记录没有分配、映射、失效或硬件 I/O 副作用，也不授予任何权限。

原因1为描述符策略、2为 framebuffer 重叠、3为配置范围。描述符原因保留原始 index/type/base/pages/attributes；非描述符原因的描述符字段为零。framebuffer 是物理范围；边界拒绝尚未借用 RuntimeView 时 framebuffer 字段为零。

Dong 的 pub var 并不直接导出 ELF 全局数据符号，因此跨模块使用纯导出访问器 `dong_configuration_conflict` 返回这个固定内核 BSS 地址，不修改编译器或 builder 的符号规则。原 renderer 仅在 S15、首次错误050A0002、版本1/valid1/ecam1及相同 error_code 时读取此记录并显示14行。访问器的实际指令和 ABI 纳入原生守卫验证；字段中的地址仅作为十六进制数绘制，不解引用。沿用原640×480下界、几何检查、四 qword Gate及 ABI。S01 的88B平台 MMIO 诊断保持原合同；其他错误回退到原显示。

## 验证及介质

新原生探针保留生产 raw64、mmio_range、configuration_address、window、read32 及上下文写入函数原体，只隔离 startup/paging/invalidate/最终 volatile load 硬件边界，验证真实 View 布局、12属性组合、用途区别、非11/Runtime Reserved、MCFG首尾/非零首总线、framebuffer、输入只读和失败零 I/O。旧 Runtime 全拒、误放 BAR Runtime/RAM/Reserved Runtime、取消范围/FB检查、提前 map 等实际坏体必须由 oracle 正常拒绝。原屏幕守卫增加实际128B编译器布局/符号和上下文像素测试。

证据在 `build/hardware/usb-ecam-20261026-r1/`。正式定向复验要求零 skip/source稳定，BAR/DMA旧回归继续执行；正常成品仍需原完整 USB-only 桌面双启动。私有 EFI 提供真实 MCFG Runtime type11 描述符并验证实际 PCI 发现/映射，旧规则反控须在 S15 显示与原描述符一致的拒绝上下文，候选不发布。

验证后只备份更新原 SanDisk H: 的正常文件，flush/fsync、SHA读回及只读 FAT32 检查，不格式化、改分区或写内盘。真实 Intel 电脑是否越过 S15、后续 USB/桌面/键鼠是否正常，仍需用户反馈；若仍拒绝，请拍下完整原因、物理范围、UEFI、MCFG 和 framebuffer 字段。
