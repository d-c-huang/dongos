

## AI交付 2026-10-28T11:46:01+00:00 · codex-mcp-b0b0a56f66684e46

已实现标准显式PSI表兼容。驱动有界读取PSI并验证完整标准USB2(1/2/3,12/1.5/480Mb/s)或USB3(4,5Gb/s)集合，检查对称/双工/保留位/重复/长度和next重叠；内核独立读取验证，Extension48B不变，协议项legacy_control承载内核验证的速度集合，授权侧校验数量/集合/全跨度。PSIC0保持原逻辑，不接受任意ID映射。新增实际precheck/服务日志58场景及真实kernel PSI成功/错速/重复/重叠/双工场景。首轮6 tests PASS(370.255s,无skip)，随后增加authority直接mask/数量/跨度正反例及kernel/authority PSI错误实现控制，新增部分交独立复验执行，尚未宣称通过。完整构建进行中；真机PSI原始word未读回，当前修复只消除已确认的一律拒绝，真机成功仍待测试。
