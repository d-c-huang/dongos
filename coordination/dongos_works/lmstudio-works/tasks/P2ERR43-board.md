# P2ERR43 — P2简单数据：缓存事务八种错误码中文对照

负责人：lmstudio。状态：待领取。

只生成JSON及交付。fixture严格为schema=1,module='mm.runtime_cache',errors数组。8项，每项严格name,code,meaning字段；code为0x十六进制字符串，meaning为简短准确中文。常量：Invalid=0x06150001(参数/状态无效)、Authority=0x06150002(可信CPU/根/权限前提不满足)、Forest=0x06150003(页表森林与授权别名闭包不符)、HardwareState=0x06150004(PAT/MTRR等硬件状态不符)、Held=0x06150005(事务资源须保持持有)、Deadline=0x06150006(截止期限)、Capacity=0x06150007(容量不足)、Storage=0x06150008(调用方存储范围/别名不合法)。用于后续C/D诊断，不增加枚举、不改数字、不声称真机验证。交付写未运行测试，由Codex读取真实生产源码复验。P2VEC42验收后才执行，LM同一时刻仅一项。

## 可修改文件

- `lmstudio-works/fixtures/p2-cache-errors.json`
- `lmstudio-works/deliveries/P2ERR43.md`

## 定向验收

- `discover:lmstudio-works/tests:test_p2_cache_errors.py`

交付：`lmstudio-works/deliveries/P2ERR43.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
