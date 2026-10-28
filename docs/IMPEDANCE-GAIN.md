# 用物理终端阻抗查询GT

源和负载规格常以Ω给出，例如100+j20Ω的源、25−j10Ω的负载。10轮增加独立的物理阻抗入口，直接将它们与Touchstone网络组合，返回送到负载的功率与源可用功率之比GT。原Γ入口和09轮匹配边界实现保留。

## 文件与MoonBit用法

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs transducer-gain-impedance examples/power-gain.s2p '@examples/power-gain-ohms.json'
moon run examples/power_gain_ohms --target js
moon run examples/power_gain_ohms --target wasm-gc
```

选项文件为：

```json
{"source_ohms":[100,20],"load_ohms":[25,-10]}
```

使用本项目合成双向放大器文件，1GHz结果约GT=4.07069614569，即6.09668685977dB；2GHz约GT=2.18064564997。示例还输出两端50Ω匹配时的4和2.25，便于理解终端改变的影响。这些是线性合成数据，不是新做的器件测量。

11轮[GT采样限值报告](GAIN-CHECK.md)可在相同Ω条件下判断指定频段要求并定位最差点；`gain-check`使用terminal_mode=impedance及同样的source_ohms/load_ohms，不改变本接口的物理定义。

```moonbit
let net = @rf.parse(text, ports=2).network_only()
let points = net.transducer_gain_impedance(
  @rf.complex(100.0, im=20.0),
  @rf.complex(25.0, im=-10.0),
)
println(points.to_json().stringify())
```

两个参数都必填，分别是端口0的戴维南源内阻抗Zs和端口1的负载Zl，单位Ω。输入必须有限，Re(Zs)>0、Re(Zl)≥0；源需具有正可用功率。零/纯电抗负载可表示不吸收实功率的终端；负实部或非有限输入报错。理想开路需要无穷阻抗，超出此有限Ω入口；原Γ入口可用load=[1,0]表示。网络仍为二端口、固定正实端口参考阻抗，两个参考可以不同，且不会被终端阻抗改写。

| 输入单位 | API | CLI选项 |
|---|---|---|
| 无量纲复Γ | transducer_gain | source、load；默认匹配 |
| 物理复Ω | transducer_gain_impedance | source_ohms、load_ohms；均必填 |

独立命令会拒绝混入Γ键、缺项、错误数组、无关夹具文件及未知选项。结果复用`TransducerGainPoint`：frequency_hz、线性gain、gain_db、state。finite/zero/singular/overflow/underflow及可选JSON字段语义与[Γ接口](TRANSDUCER-GAIN.md#定义与结果)相同；反馈真奇点优先于零功率。S/Y/Z/H/G/ABCD/T输入在既有转换规则允许时转S消费；不写出或丢弃Document元数据。

## 为什么直接保留Ω

通常Γ=(Z−R0)/(Z+R0)，但极大正阻抗可能舍入成Γ=1，极小正阻抗可能舍入成−1。原Γ方法无法恢复转换前的信息。Ω入口直接保留源/负载的实、虚分量和正实功率因子；例如理想导线两端同为1e308Ω或同为最小正subnormal电阻，GT仍为1。巨大共轭电抗下的小正电阻也有对应独立回归。

从既有[RF功率增益定义](https://qucs.sourceforge.net/tech/node6.html)代入物理终端，可用齐次反馈式H及分子`|S21|²·16R1R2Re(Zs)Re(Zl)`求GT。实现按分量和二进制尺度保留各项，用浮点展开保留大数抵消的余项，不先形成舍入Γ、巨大系数或平方差。反馈矩阵系数本身的binary64相消仍限制极近奇点的精度；有限GT不代表稳定性、压缩点或器件认证。没有增加主动负阻终端GT、频变匹配数组、优化器或复参考功率波模型。

## 实际验证与差异

新增8项验收在JS/Wasm-GC/native各8/8通过，覆盖逐端口参考、独立有理数例、物理大/小电阻、共轭电抗、匹配大尺度秩一网络、正功率上/下溢、无耗负载、奇点、输入域和非S表示。纯MoonBit示例在JS/Wasm-GC运行；严格all-target检查与本地模块打包通过。

最终独立参考为55次桥接请求、52个点结果检查。Fraction直接解四个入射/反射波及戴维南电压电流边界，Decimal160计算dB，没有复制Γ转换或库中的物理多项式。最终另运行6个文件CLI进程（2个成功、4个预期错误）：合成文件核对2点；固定SHA的现存NXP BFU530W原文件做一组新Ω查询，返回98点而仅独立核对索引0/49/97三点。原模型、S矩阵及完整输出不附送。首轮已通过的4个旧Γ路由控制保留回执，在物理算法修订后没有重跑；旧GT/匹配全套也未重跑。

初版物理系数在大尺度秩一、物理匹配端口上丢掉常数，验收测试失败后修复；失败记录保留。最终[独立回执](../evidence/impedance-gain-20261028/independent-final.json)、[检查记录](../evidence/impedance-gain-20261028/CHECKS.json)与[设计/调查](../evidence/impedance-gain-20261028/DESIGN.md)绑定源码与编译身份。既有05—09生产实现及旧公开签名保持，仅新增方法和桥接分支。

生态调查核对[MoonElec0.1.0](https://mooncakes.io/docs/SupremeHuaji/MoonElec)公开计算接口、[circuit-solver0.1.1](https://mooncakes.io/docs/hsy-bit/moonbit-circuit-solver@0.1.1)公开说明，以及[scikit-rf2.1.0电路连接](https://scikit-rf.readthedocs.io/en/v2.1.0/tutorials/Circuit.html)。通用阻抗/电路连接已有成熟方案；本项目交付差异是无Python运行时的MoonBit Touchstone＋终端Ω到GT报告，不主张RF算法原创或生态唯一。
