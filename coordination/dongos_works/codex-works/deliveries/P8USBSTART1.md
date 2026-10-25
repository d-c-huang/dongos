# P8USBSTART1 — USB 专用启动与大卷挂载缓存

日期：2026-10-25。实现已实际保存主源码，等待协调器独立复验；不声明真机桌面通过。

## 原因与修复

P8USBONLY1 R2 mixed-run-1 实际启动中，INIT_FAILURE kind2/3 id4（input）在原10秒期限失败。USB 模式原先仍先探测 PS2，关闭 i8042 的真实 USB 拓扑会消耗期限。现在 USB_ONLY 直接关闭 PS2/tablet/IRQ 状态，调用原 `usb_ready()` 认证；只有 kernel cfg13 READY 的固定 tag 和有效 incarnation 才能成功，保留1024次有界查询和1023次yield。USB 模式从不执行 PS2端口、tablet.setup 或IRQ绑定；默认原有 PS2初始化、失败后USB fallback和tablet流程保留。

现有 mount_cache 的262144簇资格与默认32KiB bitmap一致，但真实 H 有1899872簇。资格上限改为同一硬件 profile 的 `FAT_AUDIT_BYTES*8`，默认阈值不变。两条32-sector cache、mount-only生命周期、错误原样返回且不重试、finish全清及真实FAT独立审计均保留。随后两处固定512B cache-hit复制改为64次unaligned u64复制，精确覆盖[0,512)，支持非8byte对齐out，无新增缓存或越界读取。

R3 已记录 DONGOS_INPUT_USB_READY，之后 config1（FS）完整审计超时，保留原失败。关联 P8USBONLY1 的 fat.mark_chain 单遍优化另由该任务实现；本补充未改内核进程期限。R4包含两项任务的最终源码重新构建。

## 完成的预检

- `tests.test_usb_input_usbonly`：1 test /468.841s/0skip，`code/build/test/usb-input-usbonly/run-9dbb4c3d314c`。22个编译器真实DG输入闭包加6个测试依赖前后SHA一致。38个debug/release变体均ELF/COFF，122次native执行：88正常/认证失败场景、34真坏体。原12默认坏体保留，新增USB profile PS2/tablet/IRQ触达、跳过认证及错误PS2标志坏体。最大栈2240B。USB成功场景实际main→认证→READY→RPC pump/reply→GUI事件，硬件触达全0；测试最后yield故意返回错误以退出生产无限循环，不把main返回0冒作成功。无READY精确1024 queries/1023 yields/ready0，错误、无tag、epoch0及越界均拒绝。
- `tests.test_input_service` + `tests.test_usb_input_entry`：5 tests/135.891s/0skip，USB entry `run-4dfb1adf0d51`。默认PS2 IRQ/ACK/背压及原RPC身份坏体保留。旧input_service NAMES未覆盖新profile；本轮由上项真实完整22-DG闭包绑定其新依赖，不越范围修改旧文件。
- `tests.test_usb_mount_cache`：1 test/120.922s/0skip，`code/build/test/usb-mount-cache/run-754a2178239d`。两profile两模式各15944checks；高簇与恰好cap资格、默认保持原阈值、双line/尾裁剪、metadata和prefetch错误不重试、invalid begin完整快照、finish全清、非8byte对齐512B输出与双侧canary。old-limit实际坏体正常rc1，ELF/COFF，source_stable=true。
- `tests.test_fs_service`：2 tests/96.435s/0skip，`code/build/test/p5-fs-service/host/run-740a7adc14c6`。原体debug/release各1804checks，reserved真实坏体均正常rc1；15个输入指纹稳定；仅fixture源列表加入真实hardware_profile依赖。

独立源码复查确认 USB bitmap首次下标检查、链上界及完整审计仍在；cache uint64 复制精确64次且所有字节仍来自原已成功读回的line。最终协调器job、验收和集成状态由协调器登记，不手改状态文件。


## AI交付 2026-10-25T11:04:46+00:00 · codex-mcp-14619bbd432c41a6

已实际落盘8个声明路径并冻结。USB input直接原认证READY，1024边界保留且不触PS2/tablet/IRQ，默认原流程保留；mount_cache资格使用共享bitmap上限、仅两处512B拷贝改64个unaligned u64，其余生命周期/错误/边界不变。完整预检：输入1test468.841s/122native/38编译、旧input5tests135.891s、cache1test120.922s、fs_service2tests96.435s，均0skip且各真实输入稳定，详情delivery。R3确认inputREADY后FS超时另main FAT单遍优化处理；原guest期限未延长。待本任务5模块协调器独立完整复验，实际桌面由main单介质VM另验证。
