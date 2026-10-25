# P2 帧缓冲授权账本

`user.memory` 在调度前从真实 `runtime.boot_info` 的 BootInfo PA/size 发布 GOP 授权，核对 RuntimeDisplay 和完整内核页表范围；物理宽度与 HHDM 加法分别检查，拒绝虚拟地址包络溢出。授权对象及 audit scratch 常驻 service_memory arena，BSS 只保存指针；initialize 不清除已发布对象。

`FramebufferSnapshot` 的 epoch、physical、bytes、count 和 64 个 Alias 构成只读快照。首项为完整 kernel HHDM GOP 页包络，后续按 memory slot 顺序保存用户前缀，保留八个 Alias 字段。当前消费者每根只有一个 compositor 连续前缀；同根第二次授权拒绝，不扩大到完整 GOP。

`map_framebuffer` 在写入前检查真实 root/generation、范围、absent、容量和 epoch，先保留 journal/held。全部 map 与现有 root invalidation 返回后才提交并增加 epoch；中途错误永久 held。stage_commit 和根快照拒绝 held，abort/destroy 不能将部分失败洗白。

正常 abort/destroy 在预留 epoch 后保持 held=2，原撤销 private branch、flush、unbind、表清理全部成功后才移除旧授权。失败保留旧项。重建使用新的 memory generation；不与 Catalog 或 Gate token 混用。

外部 device/resource、资源替换的新旧页包络、GUI aperture、owned Frame 和共享 object 映射入口拒绝 GOP 重叠，包含 padding。已有 shared RAM 路径继续要求真实 Frame 所有权。

`snapshot_framebuffer` 重核完整 root snapshot，使用实际 runtime_roots.audit 检查森林与独立发布授权相等，失败不发布输出。`recheck_framebuffer` 重核授权、epoch 和原根集合，不要求事务中 PTE 仍是 WC；因此 WC→UC 期间 authority 可以保持有效，而新的 WC 准入快照会拒绝。

`framebuffer_epoch_pointer` 仅供未来独占 cache owner 使用；调用者须遵守 Gate 与两次全读者屏障协议，不提供 reset API。这些 unsafe 接口要求可信 BSP owner、稳定对象和可读写 caller storage，不面向用户地址。

测试入口：`python -B -X utf8 -m unittest tests.test_framebuffer_ledger`（在 code 目录）。执行真实 memory/paging/runtime_roots；私有 fixture 仅追加导出，paging 的 map_live 包装仅用于第 N 次失败注入。startup、arena 分配和 CPU 指令边界明确 synthetic。C 独立按原始 PTE 下行并核对八字段授权，覆盖短前缀/完整尾页、正常与 abort 重建、隐藏 alias、部分失败、epoch 溢出、raw/view 不一致、撤销失败、根元数据改变以及 WC→UC 的 authority recheck。

五种真实坏 Dong 源在 debug/release 编译运行：不保持部分失败、用 view 替代 raw PA、忽略额外 alias、提前解除退休 held、放行外部 GOP。预期为 C 正常返回 1；编译错误、panic 和 crash 不算负控通过。

本组件不等于实际 C/D consumer 接线。新的镜像仍需客体运行验证；warm-PCID 全读者复用及物理显示 WC 性能不由本测试证明。正式验收与集成以协调器 P2LEDGER44 最新状态为准。
