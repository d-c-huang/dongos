# P2VEC42 — P2简单数据：12条GOP页包络边界向量

负责人：lmstudio。状态：待领取。

仅生成JSON及交付，不改测试或生产源码。fixture严格为{schema:1,cases:[...]}，每行id,base,size,valid,physical,bytes。base/size/有效physical/bytes用0x十六进制字符串；无效physical/bytes均null；valid是bool。有效规则：0x100000<=base<2^48，0<size<=0x1000000，base+size<=2^48。physical向下取4096整页，end向上取4096整页，bytes=end-physical。原size16MiB但base有偏移时rounded允许多一页。固定12行顺序(id,base,size)：aligned-byte,0x100000,0x1；aligned-page,0x100000,0x1000；edge-exact,0x100001,0xfff；cross-page,0x100fff,0x2；unaligned-two-pages,0x12345001,0x2000；maximum-aligned,0x100000,0x1000000；maximum-unaligned,0x100001,0x1000000；physical-limit-exact,0xffffffffff00,0x100；physical-limit-overflow,0xffffffffff00,0x101；zero-size,0x100000,0x0；size-too-large,0x100000,0x1000001；below-one-mib,0xfffff,0x1。自行计算输出，交付写未运行测试。只作P2未来ledger独立测试数据，不宣称实际授权或物理WC通过。

## 可修改文件

- `lmstudio-works/fixtures/p2-gop-rounding.json`
- `lmstudio-works/deliveries/P2VEC42.md`

## 定向验收

- `discover:lmstudio-works/tests:test_p2_rounding_vectors.py`

交付：`lmstudio-works/deliveries/P2VEC42.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
