# `core.errors`

<!-- 由 tools/dongdoc.py 生成，请勿手工编辑；修改源码注释后重新生成。 -->

core.errors — standard-library error codes shared by all std modules. Modules that need a failure status must import and reuse these codes instead of declaring duplicate numbers, so codes stay unique across the final program.

- 源码：[errors.dg](../../std/core/errors.dg)
- 导入：`import core.errors;`（编译时提供包含该模块的 `--root`）

## 目录

| 名称 | 类别 | 摘要 |
| --- | --- | --- |
| [`BufferTooSmall`](#error-buffertoosmall) | 错误码 |  |

## 错误码

<a id="error-buffertoosmall"></a>
### `BufferTooSmall`

```dong ignore
pub error BufferTooSmall = 0x0100_0001;
```

*（源码中没有文档注释。）*

<sub>[源码第 7 行](../../std/core/errors.dg#L7)</sub>
