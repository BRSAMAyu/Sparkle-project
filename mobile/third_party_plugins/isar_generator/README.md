### Code generator for the [Isar Database](https://github.com/isar/isar) please go there for documentation.

## Sparkle vendored fork（FIX-558）

- **上游版本**：isar_generator 3.1.0+1（pub.dev，2026-09-28 从 `~/.pub-cache` 原样复制）
- **fork 动机**：上游模板直接输出 64-bit xxh3 schema/index/link id 字面量，
  dart2js CFE 拒绝（"The integer literal ... can't be represented exactly in
  JavaScript."），导致 Flutter Web 全模式构建失败（FIX-558，阻塞 V4-F web preview）。
- **本地补丁（唯一改动文件）**：`lib/src/code_gen/collection_schema_generator.dart`
  - id 超出 JS double 精度域（|v| > 2^53）时输出 `int.parse(r'<十进制串>')`
    替代 int 字面量；VM 保持精确 64-bit，web 侧确定性就近取整（Isar schema id
    只需平台内自洽，不跨平台比对）。
  - 该情形下顶层 schema 声明由 `const` 降为 `final`（int.parse 非常量表达式）。
  - JS-safe 域内的 id 输出不变，其余 6 个既有 isar 生成文件零漂移。
- **升级注意**：升级上游时必须重新套用本补丁；diff 点见上。
