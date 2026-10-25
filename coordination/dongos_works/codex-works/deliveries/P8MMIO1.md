# P8MMIO1：S01 的原始设备页冲突现场

用户真机：S01 IRQ PREPARE、CPU COUNT 8、FIRST ERROR 0x03030002。已实际追踪到 device_policy.add 唯一RamConflict分支：完整设备页与固件描述符重叠，且type!=11或RUNTIME位非零。发生于query/map/invalidate之前，尚未进入IRQ平台或线程；不能凭错误名猜普通RAM、保留区或某个设备。

15声明文件已实现并冻结。只增加Conflict11×u64/88B，原Plan184/Views88与旧接口保持；新nullable诊断接口在alias/alignment/overflow验证后清零，只在真实RamConflict先valid0填原字段、fence后valid1发布。DG第三字段因保留字用error_code，offset16不变。Runtime7传独立BSS给三参数导出，其它级别旧入口不变。新紧凑9行只在phase1/failed/firsterror/record版本valid及recorderror完全匹配时渲染；原2writer/Gate/几何/首次CPL3禁用及原接受类型/权限/预算不改，无MMIO探测。

实际源码/ABI/契约/测试已审查，证据：

- `build/test/device-policy/run-7c7a670b630b`：debug/release×C O0/O2，原1041检查及53诊断检查；11槽/全部type、runtime、stride48、多页/半开区间、64位、stale/alias/overflow原子性。漏valid发布/attrs截断实际坏体均正常执行后被拒绝；ELF/COFF、source稳定、0skip。
- `build/test/device-memory-diag/run-c9c7b920ca5a/validation-summary.json`：完整真实prepare/policy原文编译，仅3外依赖typed stubs、host计数及明确host-only reset/read接口。debug/release各186场景，冲突error2原样传播、Plan/Views/inputs/guards不变、零query/map/invalidate/touch、ATTEMPTED/stale/null旧接口/invalidstate、成功先全部query后map+invalidate、底层失败传播；吞policy guard真实坏体由同oracle正常rc1拒绝。138源/编译器指纹不变，ELF/COFF通过，0skip。
- `build/test/boot-progress/run-9b1b08f6db1b`：原84+新增98=182场景，O0/O2/两format；11字段actual DG manifest↔ASM符号↔C offsetof/size交叉；64位/所有slot/精确门槛/guard/Gate/未arm/禁用保持。原2坏体及新错offset/32位值/valid截断3坏体全部正常执行拒绝。旧Gate完整回归 `run-c26bc685bfe6` 通过，源稳定。

完整正常USB-only runtime7成品 `build/hardware/usb-mmio-20261025-r1/source/esp`，test=false且完整源图前后一致；真实ELF符号可由旧工具解析。EFI29696B SHA `fd7ae7302e6b212d069feb20ea9093dffd079cd130f5f33205c0a0b0d53cab03`；IMG2007170B SHA `d0a88eb28a2fa599a2597d4708c7c14d98c2df48de7d89270d56fd08a62ca611`；SERVICES33333248B SHA `a0466f5f43e312ea5b4727eddcae0a8ac2c5a3e92259d9c827fb99a712e755c1`。正常live-full两boot观察器正在实际运行，新增断言成功上下文88B全零+phase14/failed0/error0/view0/cpus4；全部原GUI/HID/FS/CPU/代码/页表强门保持。

受控冲突只通过独立私有EFI交付的LAPIC Reserved描述符fixture触发，不修改正常kernel/IMG/服务或放宽policy，不用主机guest写入；将核对真实rawmap/11字段/9行像素、映射前失败、USB及可写内盘整SHA和停机。提交时该fixture与normal gate尚未全部完成，不能宣布整体通过；最终note须记录真实结果，任何失败历史保留。

原SanDisk已插回H，fresh核serial4C530000010320109015、disk2 USB非系统盘。只有独立五模块0skip/source稳定、root实际正常/冲突VM全部通过且停机后才更新，先备份当前S01阶段版4文件、flush/fsync、逐文件全读回及原卷只读审计。不格式化/分区/写内盘/Git；正常候选才发布，私有EFI fixture留作证据。下一次用户照片需包含DEVICE SLOT/DEV ADDRESS/UEFI TYPE/DESC BASE/PAGES/ATTR；这次任务只增加事实，不宣告真机冲突已解决。


## AI交付 2026-10-25T14:41:42+00:00 · codex-mcp-14619bbd432c41a6

15声明文件已完成冻结，原RamConflict接受谓词/Plan184/Views88/旧接口语义不放宽。新增版本88B原始Conflict及新诊断prepare接口，输出别名/对齐/overflow安全、真实分支发布、其他调用清零，runtime7独立BSS，screen精确门槛+原Gate2writer内9行full64字段，首次CPL3禁用保持。原生真实policy/prepare/renderer全通过：1041+53planner checks、debug/release各186prepare场景且冲突零query/map/invalidate/touch、182renderer场景，真实吞guard/漏valid/截断/错offset坏体均正常rc1拒绝；source/tool稳定0skip，旧Gate回归过。完整USB-only runtime7 build源稳定，三成品hash见delivery；normal live-full两boot实际运行，私有EFI rawmap冲突fixture在准备/构建验证，尚未完成最终VM审查，未写H。请求5模块独立0skip/source稳定复验；实际normal/fixture与停机全过后才能accept/publish。仅下一轮定位事实，未把Reserved放开、未猜根因，无Git。
