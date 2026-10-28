# 实际源、负载下的传输功率增益

设计人员拿到放大器的Touchstone文件后，常需判断一组实际源/负载匹配是否能达到目标增益。MAG描述适用条件下的最大可用增益，|S21|²描述两端匹配时的增益；实际源、负载存在反射时，需要包含双向反馈的传输功率增益GT。这个本地拓展提供逐频点结果，可直接供MoonBit应用或CLI读取。

## 使用

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs transducer-gain examples/power-gain.s2p
node tools/touchstone.mjs transducer-gain examples/power-gain.s2p '@examples/power-gain-options.json'
moon run examples/power_gain --target js
moon run examples/power_gain --target wasm-gc
```

示例为本项目合成的两频点双向放大器，未使用厂商测量模型。1GHz的S矩阵为`[[.25,.125],[2,-.25]]`。默认两端匹配得到GT=4（约6.0206dB）；选Γs=.5、Γl=.25后得到精确比值9216/2645（约3.48431），而非继续把|S21|²当作实际功率增益。

MoonBit根包新增：

```moonbit
let net = @rf.parse(text, ports=2).network_only()
let points = net.transducer_gain(
  source=@rf.complex(0.5),
  load=@rf.complex(0.25),
)
println(points.to_json().stringify())
```

`source`和`load`都是可选的复数反射系数，默认0。CLI对应`[real,imag]`数组，并拒绝此命令中的未知选项。端口0为源/输入，端口1为负载/输出，矩阵仍为行优先S[out,in]。Γ分别相对于各自端口的固定正实参考阻抗，允许两端参考不同；它不是直接以ohm填写的阻抗。单端口或多于二端口、非有限值、|Γs|≥1或|Γl|>1会报错。源需具有正的可用功率；单位圆上的负载可表示不吸收实功率的开路、短路或纯电抗。

若已知物理源/负载Ω，10轮提供[独立阻抗入口](IMPEDANCE-GAIN.md)：`transducer_gain_impedance(zs,zl)`及`transducer-gain-impedance`命令，键名为source_ohms/load_ohms。它不会改变此处Γ参数的含义。

需要在指定频段检查GT要求时，可用11轮[采样限值报告](GAIN-CHECK.md)：直接消费此处迹线，保留零/奇点/上溢/下溢语义，并定位最差原始频点；没有改变GT数值计算。

输入网络可使用已有S/Y/Z/H/G/ABCD/T表示，在可转换为S时消费。Document调用`network_only()`获得分析视图，未写出或变换噪声文件，也不计算噪声系数。原网络、参考阻抗、频率和文件元数据不被修改。

09轮[匹配边界修复](MATCHING-REPAIR-20261028.md)按解析后的binary64复分量直接判断1−re²−im²，保留近单位圆的小正裕量，拒绝实际域外值。域检查没有容差或静默投影；不能把舍入为1的模长等同于精确无耗负载。可运行的近边界参数见`examples/power-gain-near-circle.json`。

## 定义与结果

GT=Pload/Pavailable-source，为线性功率比；dB采用10log10(GT)。使用既有[Qucs射频技术定义](https://qucs.sourceforge.net/tech/node6.html)中源/负载功率因子与双向输入反射关系得到：

`D=(1-S11Γs)(1-S22Γl)-S12S21ΓsΓl`

`GT=|S21|²(1-|Γs|²)(1-|Γl|²)/|D|²`

每个`TransducerGainPoint`包含`frequency_hz`、`gain:Double?`、`gain_db:Double?`及`state`。MoonBit的`None`在派生JSON中省略对应字段。

| state | gain | gain_db | 含义 |
|---|---|---|---|
| finite | 正有限数 | 有限数 | 正功率比在double范围内 |
| zero | 0 | 无 | 精确零传输或无耗负载 |
| singular | 无 | 无 | 反馈式D=0，优先于零功率判断 |
| overflow | 无 | 有限数 | 正功率比超过double上限 |
| underflow | 0 | 有限数 | 正功率比舍入为零，仍保留对数值 |

例如S21=1e200、匹配两端时，功率比超出double但增益仍为4000dB；S21=1e-200为-4000dB，不应与精确零传输混为一谈。有界复尾数和二进制指数防止直接平方溢出；反馈分母先计算det(S)，展开项按尺度求和，避免大尺度秩一矩阵丢掉低阶反馈项。普通binary64相消仍限制极近奇点的精度，有限GT不代表无条件稳定、全频稳定、压缩点或实际器件认证。

## 验证及兼容

08轮新增8项测试覆盖独立有理数例、复反射/相位、单位圆负载、域错误、真奇点、上/下溢、秩一尺度和其他网络表示；当轮与相关RF/格式11项一起在JS/Wasm-GC/native各19项通过。纯MoonBit示例在JS/Wasm-GC实际运行，文件CLI消费合成S2P和选项JSON。09轮只运行受影响的GT8项及新增匹配2项，三后端各10项；新边界/文件消费者见修复记录。

独立脚本[verify-gain.py](../tools/verify-gain.py)以四个入射/反射波未知量建立线性方程，用精确Fraction复数消元求功率；没有照抄库的展开分母或尺度算法。32个固定普通复数场景另用NumPy直接求解，对数参考使用160位Decimal。共71次桥接请求、66次点结果检查，另有5次真实文件CLI运行（两次成功、三次预期退出2，包含无关夹具选项）。原始输入/响应及版本见[回执](../evidence/transducer-gain-20261028/independent-final.json)，后端命令见[检查](../evidence/transducer-gain-20261028/CHECKS.json)。初次oracle误以为可选JSON字段为null，实际派生序列化会省略None；失败回执保留并已纠正预期。

08轮公共API仅增加方法和点类型；既有导出未删除或改签名，05—07数值/RF/格式源码保持。09轮接口及05—08其他生产实现保持，新NXP查询只核对所选3点，没有重复历史厂家或完整旧集合。未增加Python运行依赖，没有自动匹配网络综合、主动负阻终端增益定义、频变Γ输入或非线性模型。

生态调查核对了[MoonElec](https://mooncakes.io/docs/SupremeHuaji/MoonElec)的公开计算接口和[circuit-solver](https://mooncakes.io/docs/hsy-bit/moonbit-circuit-solver@0.1.1)的公开说明；它们的重点分别是通用电工计算和电路求解。相关RF库[scikit-rf](https://github.com/scikit-rf/scikit-rf)已有广泛增益分析能力。本拓展的交付差异是MoonBit内的Touchstone到实际终端GT报告，无Python运行时；不主张算法原创，也不据有限检索声称生态或全网唯一。
