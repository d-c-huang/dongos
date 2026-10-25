# P8LAPIC1：Runtime MMIO LAPIC 定向兼容

真机照片已明确：S01/error03030002，CPU COUNT8，slot0，LAPIC address/base FEE00000，pages1，typeB=MMIO11，attributes RUNTIME位设置。不是Reserved/RAM类型，也不是CPU数量触发。已据规范与源码审查将修复限定为可信MADT LAPIC，而非全局放开Runtime。

7声明文件已实现并冻结。生产仅 device_policy 一处谓词及注释改变：`kind != 11 || (runtime && slot != 0)`。无地址/完整attr串硬编码；没有新增UCcap位门（描述符是能力，PTE仍由已有机制固定UC）。所有非11、其他Runtime平台设备、retained重叠、重复页、几何、原子性与诊断清零保持，Plan184/Views88/Conflict88不变；user.devices、allocator、EFI服务与超时未改。

安全审查：EBS后无EFI RuntimeServices或SetVirtualAddressMap；BSP新root只映射显式白名单，原宽identity/HHDM已退休，PGE/PCID关闭并经既有WBINVD/MOVCR3，未批量WB映射Runtime区；allocator与SMP低页仍只type7&&!Runtime。device_memory固定supervisor WRITE|UNCACHED/NX，platform首次LAPIC读取前验证IA32_APIC_BASE与MADT地址。

原生证据：

- `build/test/device-policy/run-31ec3348207d`：debug/release×C O0/O2，原1041检查与85诊断检查，11slot/全部types/不同能力mask（含Runtime alone、1004、100D）/ctx0/原输入不变/retainederror3/duplicate/几何。旧全拒Runtime、误放全部Runtime、误放Reserved/RAM及原漏发布/attr截断共6实际坏体，均正常编译链接执行后oracle拒绝；ELF/COFF、source稳定、0skip。
- `build/test/device-memory-diag/run-e5448ff0358d/validation-summary.json`：真实prepare/policy+原typed依赖stub，debug/release各222场景；12mask×两API成功、ctx0/旧接口不碰ctx、11页先全部query后map/invalidate、flags严格WRITE|UC且无USER/EXECUTE，全部输入不改；其他10slot Runtime拒绝、所有非11拒绝、retainederror3零sideeffects、alias/ATTEMPTED等保持。吞plan错误/旧拒Runtime/误放全部Runtime3实际坏体×两模式正常exit1被拒绝；138源/编译器指纹稳定，0skip。

完整正常成品 `build/hardware/usb-lapic-20261025-r1/source/esp`，USB-only runtime7、test=false、源图前后一致。EFI29696B SHA `8e5a903d98cf8cf5dbaffcf75aa8c1cfcda580e65c0632dea9e74d521944f17b`；IMG2007170B SHA `a2995517b6b6d79e7d1448aee352e669e54a9b49e21b3a20904c603c83c593c9`；SERVICES33333248B SHA `b1525883415712c210e5bd0e228ecc80c6be230e3b7137949059246815faedc3`。

提交时正常 `live-full/` 两boot完整GUI/HID/FS/代码池页表/CPU观察器，以及 `runtime-proof/` 8CPU Runtime LAPIC实际回归均在root运行，尚不能宣告完成。后者私有EFI给LAPIC type11+Runtime原描述符，唯一private kernel guard cmp1→2在真实runtime_begin后保留S03/error1现场；必须原129ticks/65switches等完整IRQ合同、真实ROOT/UC PTE/NX/super、HHDM无别名、descriptor原样/ctx0、8CPU count、单stop/noresume、USB/3内盘整SHA、正常objects源图全不变后才能通过。私有候选不发布H，不能替代正常两boot。

原SanDisk已插回H并fresh核serial4C530000010320109015/disk2/USB非系统。独立五模块0skip/source稳定、所有实际VM全过全停后才accept/更新，先备份原MMIO诊断版4文件，逐文件flush/fsync/fullSHAreadback并readonlyFAT全审计，不format/partition/internal/Git。入口R4/内核S01–S14保留；真机是否越过S01/到桌面仍须用户下一轮反馈。


## AI交付 2026-10-25T15:28:56+00:00 · codex-mcp-14619bbd432c41a6

7文件已完成冻结，生产仅定向slot0/type11 Runtime兼容，其他Runtime设备/非11/retained/duplicates/geometry/allocator/EFI runtime/userdevices/预算保持，独立88B诊断不变。native真实policy1041+85/prepare各222场景，多mask(含alone/1004/100D)、真实flags WRITE|UC与query→map原子性、其他slot失败零sideeffects等通过；旧拒/误放Runtime及ReservedRAM/吞错误等真实坏体均正常oracle拒绝，ELFCOFF/source工具稳定0skip。完整USB-only runtime7 normal build source稳定，三artifacthash见delivery。Normal live-full两boot原全强门与8CPU runtime-proof实际回归正在root并行，未完成最终VM结果，不宣告总体通过/未写H。请求五模块独立0skip/source稳定复验；只有实际全部通过且全停后才accept/publish原H。无format/partition/internal/Git，物理效果待用户复测。
