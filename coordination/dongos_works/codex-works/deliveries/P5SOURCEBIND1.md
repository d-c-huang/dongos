

## AI交付 2026-11-06T06:50:00+00:00 · codex-mcp-e30a159488a44d74

修复fixture.hashes/prepare/链接检查，将build排除限定source_root/build，真实kernel/build源码完整纳入；未改replay验证器/内核/期限。新增真实临时目录测试，根输出排除、nested profile复制与双方哈希绑定、两端篡改和目标删除拒绝。宿主24项0skip1.271s；独立review_bkl重跑24项0skip1.123s，并分别在内存恢复旧hashes、旧prepare、两者，新测试均实际拒绝；额外源端删除亦拒绝。fixture SHA fc936636ab2c05c48b34e9e0f2091c8cf408427fe19915bf1689e5ab2ed3fc5d；test SHA110ab9597173802ea78127a4d9e9ff2fe5e65fe9bba16bccaff0e9b122711afa。原BKL control/fault客体exit0但replay因漏kernel/build/storage_profile.dg均exit1，旧档案保留。正式复验后将仅更新同一冻结构建的测试观察器，记录新source manifest/fixture身份并另建新运行回执；机器码和全部构建输入不变，当前尚未新跑，不冒充旧档案通过。
