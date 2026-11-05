# P5DMARETIRE1 交付

2026-11-05，按用户要求由 Codex 接手原 Cursor 任务，保留编号与文件范围。已写入两份完整候选模块、契约、原生 Python/C/Dong fixture 和本交付，共 7 个声明文件。

候选入口绑定实际 DmaContext、原 owner/incarnation/device generation 和独立 memory root/generation；通过真实页表森林全块预检后，逐页撤销完整 DMA lease 的用户映射，要求新的全在线 CPU sequence/ack/Seen 确认。任何 mutation 后失败永久 sticky；DMA 物理页、PINNED、Frame 与所有 table receipts 始终持有。partial/physical=0/未知别名拒绝，没有释放、清零、重绑或驱动重启能力。

协调角色实际运行 `python -m unittest discover -s ../coordination/dongos_works/cursor-works/tests -p test_p5_dma_retire.py -v`：2 tests / 0 skip，46.807 秒通过。证据 `code/build/test/p5-dma-retire/run-5b84d7414ccf/summary.json`：debug/release 各 31 个正向/拒绝场景、2 个真实坏体，共 66 次原生进程执行。正确实现全部退出 0；遗漏 ACK 与遗漏完整别名检查的坏体均由 C 数值断言退出 1。完整生产依赖图在两模式编译通过。输入 SHA 前后相同。

早期全量 NASM 超时不计作测试通过；最终保留全部受测可达汇编原体，未使用入口变为陷阱，完整汇编与保留列表归档，最终全组测试通过。分配/硬件边界是显式宿主替身，因此没有 guest/真机 INVPCID、设备 drain、物理回收证据，也不宣称 P5 完成。

源码仍在候选路径，未写入生产 memory/device_host，未提交或推送 Git。提交后等待独立源码审查及协调器复验；未自行验收或集成。


## AI交付 2026-11-05T02:18:03+00:00 · codex-mcp-891e96b2a2a74c41

7个声明文件已落盘。实际上下文/独立代际绑定、完整真实页表森林别名预检、逐页unmap_live后新全核确认；物理DMA/pin/表receipt永久持有，失败sticky，partial/physical0拒绝。协调角色实测2tests/0skip通过46.807秒，debug/release共66个原生场景含4次真实坏体断言拒绝，完整生产模块编译通过，源稳定。证据code/build/test/p5-dma-retire/run-5b84d7414ccf；NASM无关函数收缩及硬件mock边界详见契约。未运行OS/VM、未集成生产、未自行验收。


## AI交付 2026-11-05T06:43:15+00:00 · codex-mcp-20924f20ca174a06

针对独立BLOCK两项返修：新增独立可信prepare入口，复用真实Context/lease/BSP/IF0/BKL停机检查；永久attempt在allocate前锁存，失败不可重试；退休入口零分配并绑定准备root/gen/inc/pages，未准备拒绝。标记区段移memory末尾保留旧metadata提取边界。测试新增分配后失败重复/未准备/准备身份拒绝/同步Context partial physical0，逐次对照allocator和完整kernel/owner/other页表；新增取消attempt锁存真实坏体。实际2 tests/186.472s/0 skip/OK，run-b436e06d5b5d；新3类坏体均断言exit1，生产两模式closure编译通过。首次误启动旧C夹具对新prepare接口的失败记录保留，不计通过。独立审查者正在只读复审当前源，旧rev5 BLOCK不被覆盖；本提交待复审及新正式复验，不代表验收。未集成生产、不运行OS/VM、不提交推送。
