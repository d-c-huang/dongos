# P2LEDGER44 — P2帧缓冲独立授权账本及映射撤销生命周期

负责人：codex。状态：待领取。

接续已集成B/OBS与CACHE组件。生产仅kernel/user/memory.dg；不改services或runtime_cache。阅读build/test/p2-historical36-review/cd-task-book-draft.md与cd-ledger-harness-notes.md作为设计参考，旧B待验文字已过时，不作为当前状态。本卡只实现独立ledger，不宣称C/D actual或物理WC通过。固定公开API：FramebufferSnapshot{epoch:u64,physical:u64,bytes:u64,count:usize,aliases:[64]runtime_roots.Alias}；snapshot_framebuffer(out:*FramebufferSnapshot,roots:*const RootSnapshot)!void；recheck_framebuffer(snapshot:*const FramebufferSnapshot)!void；framebuffer_epoch_pointer()*u64。永久ledger/scratch用service_memory arena，BSS仅指针，不增加大局部帧。publish_framebuffer在SMP前从runtime.boot_info真实BootInfo读取PA/size（不得将HHDM当PA），独立核完整kernel WC映射后发布；重复/不同aperture/overflow原子拒，initialize不清已发布ledger。每项保留root/identity/generation/VA/PA/bytes/flags/leaf_bytes，canonical序，kernel完整GOP页包络，user保持原compositor前缀。map前核slot/root/generation、全absent、容量/范围/冲突、epoch预算并预留journal；真实map/失效完成才提交；部分失败永久held并阻止snapshot/启动/再准入。stage_abort/destroy实际撤销且原失效退休完成后才删除授权，禁止新代覆盖旧代。所有外部PA/owned/share入口按实际页包络拒GOP重叠。snapshot准入核完整森林WC与独立发布项相等；recheck核epoch/authority/根代际，不强制转换中PTE仍WC；epoch仅独占cache提交，Gate token独立。必须执行真实memory+paging，C独立walker；synthetic只限startup/resources/hardware，列明来源和override。覆盖publish/map/abort/destroy/同slot新代、短user/全GOP尾页/隐藏alias/第N页失败/提前删项/padding/epoch溢出及失败不变；真坏DG须编译成功、同oracle正常exit1拒绝。可读取LM P2VEC42数据作边界用例，不得把fixture通过冒真实ledger通过。测试/交付须给source稳定证据，由协调器独立复验后验收集成。

## 可修改文件

- `kernel/user/memory.dg`
- `tests/framebuffer_ledger_probe.dg`
- `tests/framebuffer_ledger_probe.c`
- `tests/test_framebuffer_ledger.py`
- `docs/p2-framebuffer-ledger.md`
- `codex-works/deliveries/P2LEDGER44.md`

## 定向验收

- `module:tests.test_framebuffer_ledger`
- `module:tests.test_runtime_roots`
- `module:tests.test_paging`
- `module:tests.test_service_launch`
- `module:tests.test_desktop_recreate`
- `module:tests.test_gui_font_portal`

交付：`codex-works/deliveries/P2LEDGER44.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
