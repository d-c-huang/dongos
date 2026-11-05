# P5RECBOUND1 独立审查

2026-11-05，用户明确授权；非作者子代理 `/root/review_recovery` 只读审查，协调器转录。结论 PASS，任务 submitted rev4。

已核原任务书、实现、测试有效性及正式复验 856e2bb666b84899b024da8f27be865c（6+3 tests，0 skip，source_stable）。新增乘法上界检查早于乘法，输出 word 与 token/steps 的重叠在任何写入前拒绝。原随机1600步/模式和8类负控保留。生产 PINNED 拒绝与分配前登记仍在。

独立额外运行9项宿主测试：79.154s，OK，0 skip；build/independent-p5recbound1。两类新坏体 debug/release 均编译链接并正常退出1，打印 BOUNDARY_ASSERT（step-span/output-alias），不是panic/超时。正常体均 BOUNDARY_PASS。

源码 SHA256：device_recovery.dg 304e83e073374c4212c6e1b5a69aa9ec626f440fd8ae87e2e459bdc207e28fbb；test_device_recovery.py 801a0e3612b48d3e8b10c69bef384f9a22e7873273d26cc383fab8d93ef4c986；docs/device-recovery.md cf3af64c52563ee76f15e2e07d12d70425ac91e55a170f3595db57ee20408b48。测试前后稳定。

非阻断：文档旧检查点仍写4项，目前恢复测试6项。证据仅宿主实际Dong原生契约与源码守卫，不证明硬件DMA drain、物理回收、真实OS/VM或完整P5。
