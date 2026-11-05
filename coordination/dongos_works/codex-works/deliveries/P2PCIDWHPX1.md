# P2PCIDWHPX1 严格 WHPX 复验

现有归档在目录迁移后因原路径校验被拒绝。首次重建时工作树里的 P9 观察器仍在编辑，构建器正确拒绝输入变化。随后从完整冻结副本重新构建，P2 专用 runtime7 镜像成功生成。宿主 PCID 及构建合同测试实测 48 项通过，零跳过。

同一冻结镜像做两次严格四核执行，均使用 `--require-pcid --accel whpx --kernel-irqchip off`。第一轮 CPU 配置 `host`，第二轮 `host,-vmx`。两次均实际启动 QEMU，串口均记录 OVMF `PlatformPei` 的 #GP（APIC 3，RIP `0x834eee`），均在 `DONGOS_P1_START` 前超时。两个 QEMU 进程都确认停止、退出 0。

- [host 结果](../../../../code/build/test/p2-pcid-whpx/run-f7ab83d6ec75/guest/result.json) · [OVMF 串口](../../../../code/build/test/p2-pcid-whpx/run-f7ab83d6ec75/guest/boot-1/serial.log)
- [host,-vmx 结果](../../../../code/build/test/p2-pcid-whpx/run-f7ab83d6ec75/guest-no-vmx/result.json) · [OVMF 串口](../../../../code/build/test/p2-pcid-whpx/run-f7ab83d6ec75/guest-no-vmx/boot-1/serial.log)

两次均未取得 DongOS 逐核 PCIDE、暖 tag 或退休回执。PCID 门等待能正常启动并暴露必要 CPU 特性的执行环境。物理显示 WC 保留独立真机验收。


## AI交付 2026-11-05T12:56:39+00:00 · codex-mcp-50488d53a0084e80

完整冻结P2专用镜像重建成功。宿主48项零skip。严格WHPX四核、kernel-irqchip off分别CPU host和host,-vmx两次实际运行，OVMF PlatformPei同一RIP #GP，未进入DONGOS_P1_START；两次QEMU均停止退出0，保留完整日志。当前环境没有逐核PCIDE、暖tag、退休证明，未用TCG替代。
