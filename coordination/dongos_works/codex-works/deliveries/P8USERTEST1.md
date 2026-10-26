

## AI交付 2026-10-26T11:17:46+00:00 · codex-mcp-918a30d10dd649bf

仅修改tests/test_user_smp_integration.py，原production selector断言错误地要求ROOT/kernel/smp_probe.dg；实际runtime6/7 builder已采用完整kernel-profile-src快照。改为精确output/kernel-profile-src/smp_probe.dg且字节等于当前原源码；保存完整kernel DG source_before/after核相等，使用现有verify_profile独立验证完整生成source集/hash/静态表0合同，保留normal selector/链接程序集/未built/无kernel.elf等断言。实际python -m unittest tests.test_user_smp_integration -v最终3项14.982s PASS/0skip。code/build/hardware/usb-user-diag-20261026-r1/native-routing-final.log；旧native-integration过期路径失败与第一修正缺source_boundary的失败日志均保留，最终补齐真实前后源码校验元数据而非标旧失败为通过。未改生产builder或放宽断言；待正式独立复验源码稳定后验收。
