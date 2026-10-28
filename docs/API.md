# 公共API与证据约定

当前模块为 `guolei-dev/touchstone@0.3.0`，源仓库为 [guolei-dev/moonbit-touchstone](https://github.com/guolei-dev/moonbit-touchstone)。完整签名以 [pkg.generated.mbti](../pkg.generated.mbti) 为准。数学实现留在MoonBit，Node仅承担文件/CLI/桥接；Python只参与开发验证。

## 实际消费入口

| 任务 | 当前公共API | 语义 |
|---|---|---|
| 读取 | `parse(text, ports=2)` | 返回Document；旧版文件可显式给端口数；语法或预算不合法时raise |
| 单端网络视图 | `document.network_only()` | 返回Network；带噪运算使用Document方法以传播噪声 |
| 参数互转 | `network.convert("Z")` | 返回Network，目标Z单位ohm；数学不可表示或数值不安全时raise |
| 参考重归一化 | `network.renormalize([75.0,75.0])` | 有限、正实且频率不变的端口参考 |
| 指定混合模对 | `network.to_mixed_mode([(0,1),(2,3)])` | 零基不重叠配对，返回Document；同对参考相等，剩余端口保留S |
| 无源/互易诊断 | `network.diagnostics(tolerance=1e-9)` | 返回每个采样点的诊断；三态定义见RF约定 |
| 回损/VSWR | `network.metrics(output,input)` | 零基端口；无穷损耗用标志，VSWR区分finite/infinite/active；[一端口示例](ONE-PORT-METRICS.md)展示公开模块与相同文本的文件消费 |
| 已知夹具去嵌入 | `measured.deembed(left,right)` | Network或Document的方法；需要匹配频点和参考、可逆夹具链，不提取未知夹具 |

这里的“document”“network”是变量名。库使用MoonBit的 `raise`，错误带原因；CLI将输入/数学失败报告到stderr并退出2。不要依赖不存在的 `Touchstone::from_string`、`to_z_params`、`ZParams` 或 `RfError::SingularMatrix` 接口。

既有`network.terminate_ports(...)`可由调用方封装为Document写出；16轮增加独立文件命令[terminate-file](TERMINATE-FILE.md)，避免把原`terminate`分析JSON误当成Touchstone。它不增加公共库接口，也不改原JSON或回执协议。

文件格式与分析表示分开：Touchstone 1.0/1.1/2.0/2.1按标准接受S/Y/Z及适用二端口H/G；ABCD/T仅作为二端口API/JSON分析表示，写Touchstone前须显式转回合法文件参数。参考定义及资源边界完整保留于 [SCOPE](SCOPE.md) 与 [RF-0.3](RF-0.3.md)。

理想一端口短路S=−1可转换成Z=0；理想开路S=1的I−S为零，无法用有限Z表示，必须失败。这是目标表示的奇点，不能笼统把短路/开路都叫坏输入，也不能加扰动伪造有限解。

真实纯MoonBit示例在 [examples/rf_03/main.mbt](../examples/rf_03/main.mbt)，导入别名为 `@rf`，展示指定差分对、CMRR、稳定性与带噪级联：

```sh
moon run examples/rf_03 --target js
moon run examples/rf_03 --target wasm-gc
moon build --target js --release --deny-warn
node tools/touchstone.mjs rf-convert examples/attenuator.s2p '{"parameter":"Z"}'
```

CMRR的balanced/input/output定义分别保留，不混称差分放大器电压增益比。噪声相关矩阵、合法源反射、插值、级联、去嵌入与离散频段职责均继续适用；这些示例不扩大为仪器校准、全频因果性或器件认证。

## 验证职责与历史记录

已完成的数值回执按原事件和来源保留，本期文档校准不重跑历史大集合或厂商模型。

| 记录 | 实际覆盖 | 独立参考 | 日期/回执 |
|---|---|---|---|
| 旧RF集合 | 368请求、1103断言，参数/混合模/端接/稳定性/噪声级联等 | scikit-rf/NumPy及独立公式 | [2026-10-23](../evidence/rf-20261023/reference.json) |
| 上限端口集合 | 30无源案例+9混合模组正反18请求+7预期拒绝=55请求 | 无源用NumPy eigvalsh/解析幂波不变量；混合模正向用scikit-rf2.1.0 renumber/se2gmm，反向对照原始独立网络 | [2026-10-27回归](../evidence/hardening-20261027/reference.json) |
| 后端回归 | JS与Wasm-GC各31/31 | 现有MoonBit测试，含32端口解析不变量 | [原始检查](../evidence/hardening-20261027/CHECKS.json) |
| NXP BFU530W | 单偏置98频点S、S→Y、写出重读 | scikit-rf独立读取/转换 | [2026-10-27](../evidence/public-breadth-20261027/RESULT.json) |
| Johanson | 1551频点及有限频段采样检查 | scikit-rf/NumPy | [2026-09-27](../evidence/reassessment-20260927/johanson.json) |

55请求中的7个拒绝是预期错误路径，既不是运算失败率，也不是数值误差观测。该集合不含新的仪器标定、夹具或群时延测量。其混合模观察值按表示分开：

| 表示/单位 | 正向最大复数绝对差 | 反向最大复数绝对差 |
|---|---:|---:|
| S／无量纲 | 2.680161805326998e-16 | 1.8561541192951836e-16 |
| Y／siemens | 2.081668281462914e-17 | 5.150245627764264e-18 |
| Z／ohm | 1.1368878926877637e-13 | 1.7708057242771247e-14 |

脚本混合模断言为rtol=3e-8、atol=3e-9（绝对项随表示单位解释）；以上是有限合成输入的观察最大值，不能替换为全域binary64精度保证。无源回归使用ε=1e-7，与API默认1e-9分开；未认证精确±ε浮点切点。旧368/1103中的最大绝对差2.44131825866134e-10也只属于原集合。

NXP的S最大差1.6165091241761062e-15为无量纲、Y最大差7.928654179053002e-17为siemens。原回执没有报告NXP群时延误差，不能补写≤1e-12s。没有一个“1.8e-10双精度松上界”能由浮点格式本身保证全部网络运算。

## 来源、身份和交付边界

项目源码MIT；附送样例attenuator及新回归输入为项目合成。NXP/Johanson公开模型可下载性不等于MIT再分发权，原ZIP/S2P及完整数值导出继续不随代码分发，见 [THIRD-PARTY](../THIRD-PARTY.md)。规范链接与参考库归属保留于 [SOURCES](SOURCES.md)。

本地两份申报保持逐字相同；未提供原始通知和当时上传附件，历史材料不一致原因仍未确认。不能断言原附件永久不可考，也不能用现有源码/验证回执反证历史上传。现有工作区是源码快照，不伪造git历史。本地源码完成、远端CI/发布、报名材料上传和赛事结果分别记录。31/32端口证据只说明有限输入回归，不包括峰值内存、高并发或稀疏求解；后者是未来候选。
