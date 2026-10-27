# P8APCHECK1 — actual AP activation checkpoint

Implemented explicit AP CHECK R1. Unlike the prior pre-AP stop, this executes the real original IPI publication, successful user_smp_activate on every AP, original ready2 waiting and actual service queue projection. The private AP assembly then records its bit and parks at CLI/HLT instead of entering idle. BSP observes all park bits under the existing until limit and stops before retiring the view or unlocking the Domain. This diagnostic change is deliberately not normal AP idle/dispatch/CPL3 acceptance.

Six declared files are present. Capture reads the actual boot/domain/queue/Header state into17u64/136B fixed BSS, preserving the first failing CPU, once and done-last behavior. Fifteen scalar rows use the original geometry/cache Gate. Original normal sources/deadlines/locks/selector, seventeen ELFs and service bundle are preserved; private user_boot.o is the fourth substituted object, with nine strict real build commands and both actual EFI image digest consumers verified.

Root initial native:2 tests9.593s PASS0skip, debug/release O0/O2, ELF/COFF; wrong-lock/repeat/missing-done/ignore-error/ready1/ignore-park/last-error actual bad bodies must fail independent C assertions. The final test additionally asserts the real Header256B/ready200/last_error208 layout and will be rerun by formal verification. The first full graph compile found duplicate external linker symbol declarations; fixed by a second assembly alias for the private BSP caller, without changing either observation or mask source. The failed candidate is retained; final candidate-r2 completes all9 commands and strict verify.

Root8CPU actual single-USB VM is running at submission. It must check captured and live Header ready/errors, CPU GS/RIP/IF0/HLT, AP publication and park bits, actual queue, no user services/device authority, full executable bytes and all15 screen rows, whole USB/three writable internal sentinel images unchanged, single stop/cleanup. No VM or Intel result is claimed prematurely. Formal module must pass0skip/source-stable, and root must review source/contract/test effectiveness before acceptance/publication. User confirmed original SanDisk is reinserted as H:; backup/identity/flush/readback/native FAT32 rb remain gated on acceptance. Intel next photograph and normal runtime failures remain pending.

## Storage-contract rework

First formal job8ec0aee364f3422b9561850c754987fb passed2 tests/9.703s/0skip/source-stable, but root actual vm-r1 correctly rejected the report's address outside BSS: EMPTY.first_cpu=16 made the compiler emit initialized data. No acceptance/publication occurred. Task was returned and reclaimed; EMPTY is now entirely zero, with first_cpu=16 assigned on the first actual capture. Native test now checks the actual emitted BSS symbol and136-byte allocation, in addition to the prior ABI/behavior oracles. Nine-command candidate-r3 build, root VM and formal module must all run again; failed candidate/VM/formal history is retained.


## AI交付 2026-10-27T12:38:29+00:00 · codex-mcp-5c7de4d7c45b49d1

六文件已落盘，explicit AP CHECK R1保留normal IPI/activate/ready2 wait/projection，只在私有AP成功激活后记录park bit并CLI/HLT，BSP原until内等待mask后、unlock前capture stop；不是idle/BKL竞争/CPL3成功。原native2tests9.593s0skip、7类真坏体debug/release失败有效，最后补Header256/offset200/208断言由formal再跑。九实际命令candidate-r2+strictverify通过，保留首轮duplicate extern编译失败并用asm alias修复。Root实际8CPU单USB VM仍运行，未宣称成功。正常源/17服务/原时限策略保持，申请独立复验后root实审及VM通过再写H；用户已确认H。


## AI交付 2026-10-27T12:41:12+00:00 · codex-mcp-5c7de4d7c45b49d1

已实际修正报告BSS契约：EMPTY全零，first_cpu NONE16在first run初始化；native新增actual assembly BSS STATE136断言。root重跑2tests9.419s通过0skip，九命令candidate-r3严格build/verify通过。保留首formal2tests通过但rootVM因.data地址拒绝的真实返修记录，无验收/写盘。新root8CPU VM-r2正在以candidate-r3执行；原CPUready/park/header错误/队列/坏体/onlyprivate hook边界都保留。六文件冻结，申请formal全模块再跑，root实审和VM全部通过后再验收。
