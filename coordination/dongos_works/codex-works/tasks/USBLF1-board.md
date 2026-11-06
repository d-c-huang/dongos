# USBLF1 — [P8] Windows换机后精确硬件策略LF检出修复

负责人：codex。状态：待领取。

当前Windows core.autocrlf=true将services/lib/hardware_profile.dg检出CRLF，USB generate严格DEFAULT_BYTES检查失败。保持策略内容/构建器严格字节契约，仅将本文件还原LF，工作区维护在根.gitattributes固定此路径text eol=lf；记录真实构建失败及现有profile/packaging测试。源文件逻辑与HEAD不变，不放宽默认策略验证。

## 可修改文件

- `services/lib/hardware_profile.dg`
- `codex-works/deliveries/USBLF1.md`

## 定向验收

- `module:tests.test_usb_only_profile`
- `module:tests.test_usb_profile_packaging`

交付：`codex-works/deliveries/USBLF1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
