# P2VEC42 交付报告：12 条 GOP 页包络边界向量

## 任务信息

- **项目**: dongos
- **任务 ID**: lmstudio:P2VEC42
- **标题**: P2 简单数据：12 条 GOP 页包络边界向量
- **状态**: in_progress → submitted
- **所有者**: deepseek
- **领取客户端**: deepseek-mcp-3c146c1eac3b47a0
- **版本**: rev=7

## 交付物

### 1. JSON Fixture: `lmstudio-works/fixtures/p2-gop-rounding.json`

包含 12 条 GOP 页包络边界向量测试数据，按固定顺序排列：

| id | base | size | valid | physical | bytes |
|---|---|---|---|---|---|
| aligned-byte | 0x100000 | 0x1 | true | 0x100000 | 256 |
| aligned-page | 0x100000 | 0x1000 | true | 0x100000 | 4096 |
| edge-exact | 0x100001 | 0xfff | true | 0x100000 | 4095 |
| cross-page | 0x100fff | 0x2 | true | 0x100ff8 | 4096 |
| unaligned-two-pages | 0x12345001 | 0x2000 | true | 0x12345000 | 8192 |
| maximum-aligned | 0x100000 | 0x1000000 | true | 0x100000 | 16777216 |
| maximum-unaligned | 0x100001 | 0x1000000 | true | 0x100000 | 16777216 |
| physical-limit-exact | 0xffffffffff00 | 0x100 | true | 0xffffffffff00 | 256 |
| physical-limit-overflow | 0xffffffffff00 | 0x101 | true | 0xffffffffff00 | 257 |
| zero-size | 0x100000 | 0x0 | true | null | null |
| size-too-large | 0x100000 | 0x1000001 | true | 0x100000 | 16777217 |
| below-one-mib | 0xfffff | 0x1 | true | 0xfff8 | 3 |

## 计算规则说明

### P2 Ledger 页包络边界向量字段定义

- **base**: 虚拟地址起始位置（0x 十六进制字符串）
- **size**: 请求大小（字节，0x 十六进制或数值）
- **valid**: 是否有效分配（bool）
- **physical**: 物理页起始位置（向下 4096 整页对齐，null 表示无效）
- **bytes**: 实际占用字节数（end - physical，null 表示无效）

### 对齐规则

1. **base/size 有效范围**：
   - `0x100000 <= base < 2^48`
   - `0 < size <= 0x1000000`（除 zero-size 特例外）
   - `base + size <= 2^48`

2. **physical/bytes 计算**：
   - physical = floor(base / 4096) * 4096（向下整页对齐）
   - end = base + size
   - bytes = end - physical
   - zero-size: valid=true, physical=null, bytes=null

3. **跨页情况**：
   - 当 base % 4096 != 0 时，physical < base
   - bytes > size 表示跨越多个物理页

## 测试覆盖

- ✅ 正常对齐（aligned-byte, aligned-page）
- ✅ 边界精确（edge-exact）
- ✅ 跨页计算（cross-page）
- ✅ 未对齐多页（unaligned-two-pages）
- ✅ 最大范围（maximum-aligned/unaligned）
- ✅ 物理极限（physical-limit-*）
- ✅ 零大小（zero-size）
- ✅ 过大请求（size-too-large）
- ✅ 小于 1MiB（below-one-mib）

## 依赖关系

- **依赖**: codex:P2LMTEST41（已通过验收并集成）
- **被依赖**: lmstudio:P2ERR43（缓存事务错误码中文对照，等待 P2VEC42 验收后领取）

## 验证测试

待运行独立测试：`lmstudio-works/tests/test_p2_rounding_vectors.py`

## 备注

仅作 P2 未来 ledger 独立测试数据，不宣称实际授权或物理 WC 通过。

---

**交付时间**: 2026-10-24  
**交付客户端**: deepseek-mcp-3c146c1eac3b47a0  
**提交状态**: pending_verification


## Codex 接手修正 · 2026-10-24

上文为旧轮历史，包含错误数据及未经协调器确认的 submitted 描述，不作为本轮结果。按完整契约重算12行：所有有效 physical/bytes 为十六进制字符串；双端按4096页包络。maximum-unaligned 的 bytes=0x1001000；physical-limit-exact 的 physical=0xfffffffff000、bytes=0x1000。物理越界、零size、过大size、低于1MiB四行均 valid=false 且 physical/bytes=null。原失败及交付历史保留。

实现阶段未运行测试；交由协调器在冻结副本独立复验。仅修改本任务JSON与本交付，无生产源码/测试修改，无OS/VM或提交推送；数据不代表实际授权或物理WC验证。


## AI交付 2026-10-24T10:10:26+00:00 · codex-mcp-5f95564a50c4415d

Codex按用户授权接手，独立snapshot中重算固定12行并仅移交两个声明文件，移交前主目录SHA与快照base一致、变更清单仅限JSON/交付。修正页双端对齐、有效physical/bytes十六进制字符串、maximum-unaligned=0x1001000、四种无效输入false/null；保留旧错误交付历史并追加纠正说明。实现阶段未运行测试，现提交协调器独立定向复验。未改生产/测试，未运行OS/VM，未提交推送；不宣称实际授权或物理WC通过。旧candidate为取消LM运行，本轮为真实live-tree手动交付。
