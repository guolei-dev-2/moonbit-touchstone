# 原始频点的频段文件导出

`Document::crop(start_hz,end_hz)`和`crop`文件命令为**无噪声文档**保留Hz闭区间内的原始记录，并输出可继续分析的Touchstone文件。返回新文档，原输入不变。它不插值、不补边界频点、不改变参数/端口或参考，不是连续频带合格证明。

## 实际文件接收

宽频扫频模型常需要只把工作频段交给下一分析程序。[scikit-rf的crop](https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.crop.html)也明确提供无插值频率裁剪。本库原来可以手动取得频率数组、挑选原点并组合`Document::interpolate`；新入口接收两个Hz界限，直接完成文档和文件工作流，不要求文件调用方枚举所有频点。这里不声称既有组合能力不存在，也不把官方工作流文档当作本项目外部采用证言。

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs crop examples/crop-wideband.ts @examples/crop-query.json NEW-CROP.ts
node tools/touchstone.mjs dump NEW-CROP.ts
node tools/touchstone.mjs metrics NEW-CROP.ts '{"input":0,"output":0}'
moon run examples/crop_document --target js --release
moon run examples/crop_document --target wasm-gc --release
```

手写示例是0/1/2/4MHz的三端口物理Z对角矩阵，端口参考25/50/75Ω。裁剪1e6..2e6Hz仅保留原点1和2。随后原有指标接收者在端口0得到反射1/3、1/2，VSWR2、3和独立对数损耗。所有矩阵、元数据和实际写出文件由公开包/文件接收例程完整消费；合成示例不代表器件测量性能或外部客户采用。

## 输入到输出约定

- `start_hz/end_hz`必需、有限、非负且前者不大于后者；均为Hz，不随文件原单位改变。保留满足`start<=f<=end`的全部原点，保持原顺序和每个复分量。无“最近频点”选择。
- 区间可伸到原范围外，只取交集；相等端点仅在恰有该原点时保留一条。空交集明确报错，不输出空网络或发明样本。
- 保留原参数物理单位、端口顺序/参考、独立文档参考约定、原始混合模矩阵基底/描述符和Information行。混合模文件按原始存储坐标裁剪，之后仍可用既有单端/模态视图。
- 现有Document writer仍输出规范2.1/Hz/RI/full；原注释、排版、格式和版本不逐字保留。裁剪只删除频率记录，不是原文件字节切片。
- 有任何实际噪声记录时，新入口明确拒绝。它不静默删除或重采样噪声，也未定义新的噪声裁剪模型；原合法带噪输入仍可由既有解析、规范化及噪声接口处理。
- CLI仅接受`ports/start_hz/end_hz`，未知选项或夹具路径键拒绝且不读取第三文件。成功退出0并输出Touchstone；配置、空选区、噪声或IO错误退出2，无部分输出。已有输出和输入同路径都拒绝覆盖。

## 后续分析的边界

```moonbit
let original = @rf.parse(text)
let selected = original.crop(1.0e6, 2.0e6)
let new_file = selected.write()
```

后续分析看到的是裁剪后的新迹线。原群时延仍需至少两点且传输非零，端点及差分孔径也会按新迹线确定；单点文件导出成功不意味着群时延有定义。原文件/端口预算和所有旧入口、默认值、错误域保持，没有新格式、RF/校准/采样模型或全数值域/性能保证。

## 独立验收

`crop_test.mbt`核原始完整SI矩阵、非对齐/相等/外伸/空区间、非顺序混合模基底/参考、非法界限、带噪保留及单点下游错误。公开例程`examples/crop_document`在JS/Wasm-GC实际裁剪并调用旧指标。

`tools/verify-crop.py --evidence FRESH_PATH`按原始整数/分数矩阵与固定点号给出预期，用独立有限解码器读完整规范输出，再由真实文件CLI读回和计算指标。反射来自独立`(Z-R)/(Z+R)`，VSWR用有理数，对数用独立log10；旧显式频点组合仅是兼容控制。原工作输入、实际测试复制件、公开包输出文件、编译物与全部stdout/stderr身份分开记录，失败输出不覆盖。

必要CI门为`Consume original-frequency cropped documents from package and files`；完整持续验证计划见[CI-PLAN](../CI-PLAN.md)。不把自产verifier的标志或云端artifact元数据当作完整内容读回。
