# P2PCIDWHPX1 严格 WHPX 复验

现有归档在目录迁移后因原路径校验被拒绝。首次重建时工作树里的 P9 观察器仍在编辑，构建器正确拒绝输入变化。随后从完整冻结副本重新构建，P2 专用 runtime7 镜像成功生成。宿主 PCID 及构建合同测试实测 48 项通过，零跳过。

同一冻结镜像做两次严格四核执行，均使用 `--require-pcid --accel whpx --kernel-irqchip off`。第一轮 CPU 配置 `host`，第二轮 `host,-vmx`。两次均实际启动 QEMU，串口均记录 OVMF `PlatformPei` 的 #GP（APIC 3，RIP `0x834eee`），均在 `DONGOS_P1_START` 前超时。两个 QEMU 进程都确认停止、退出 0。

- [host 结果](../../../../code/build/test/p2-pcid-whpx/run-f7ab83d6ec75/guest/result.json) · [OVMF 串口](../../../../code/build/test/p2-pcid-whpx/run-f7ab83d6ec75/guest/boot-1/serial.log)
- [host,-vmx 结果](../../../../code/build/test/p2-pcid-whpx/run-f7ab83d6ec75/guest-no-vmx/result.json) · [OVMF 串口](../../../../code/build/test/p2-pcid-whpx/run-f7ab83d6ec75/guest-no-vmx/boot-1/serial.log)

两次均未取得 DongOS 逐核 PCIDE、暖 tag 或退休回执。PCID 门等待能正常启动并暴露必要 CPU 特性的执行环境。物理显示 WC 保留独立真机验收。


## AI交付 2026-11-05T12:56:39+00:00 · codex-mcp-50488d53a0084e80

完整冻结P2专用镜像重建成功。宿主48项零skip。严格WHPX四核、kernel-irqchip off分别CPU host和host,-vmx两次实际运行，OVMF PlatformPei同一RIP #GP，未进入DONGOS_P1_START；两次QEMU均停止退出0，保留完整日志。当前环境没有逐核PCIDE、暖tag、退休证明，未用TCG替代。


## AI交付 2026-11-06T07:58:17+00:00 · codex-mcp-e30a159488a44d74

### 本机 PCID 能力预检（2026-11-06，主线 686c14b）

按用户要求直接沿用本记录。在原任务的 `q35,kernel-irqchip=off` 与 `-accel whpx -cpu host` 上运行独立、一次性的单核 BIOS CPUID 探针，绕过此前失败的 OVMF 阶段以区分能力问题。真实客体退出 33（探针完成），原始 CPUID.01H:ECX=`F6F83203`（PCID 位 17 为 0），CPUID.07H.0:EBX=`F1BF07A9`（INVPCID 位 10 为 1）。宿主 Windows CPUID 同样报告 PCID=0、INVPCID=1。单独用 `host,+pcid,+invpcid,enforce` 检查，QEMU 退出 1，原文为 `host doesn't support requested feature: CPUID[eax=01h].ECX.pcid [bit 17]`。TCG 对照同一探针正常退出 33，两个特性均为 0。三次过程均已结束，使用临时镜像与 QEMU snapshot，无物理盘操作。

实际命令、工具指纹及原始日志位于本机 `code/build/test/p2-direct-20261106/`。回执 `cpuid-result.json` SHA-256 `e8fe19784b3e37249d2c80df6de5f710f50855147f7db4da788ca2d87352b7ef`。WHPX 原始字节 `F6F83203\nF1BF07A9\n` SHA-256 `e9770f38fee7814cf1cdf8cc9f4a49ec8cf3d3b7a55dee3f26a8560d54e51102`，显式特性拒绝日志 SHA-256 `e428cdae962d71b596cb73278ec64333b34ded7ed757d394c826938ed4a8cb1c`。

本机执行 `python -X utf8 -B -m unittest tests.test_p2_pcid tests.test_p2_pcid_build -v`，48 项通过、零跳过。本轮只做能力预检，未重跑同配置的完整 DongOS 四核门，既有两次 OVMF 失败保持原样。严格逐核 PCIDE、暖 tag、跨代复用与错 tag 负控仍需支持 PCID/INVPCID 的执行环境。
