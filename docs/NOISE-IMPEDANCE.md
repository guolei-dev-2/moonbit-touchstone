# 以物理源阻抗查询噪声系数

接收方持有二端口噪声Touchstone文件和以Ω给定的源规格时，可使用`Document::noise_figure_impedance(source_ohms)`或现有`noise`命令的`source_mode:"impedance"`。新入口直接保留物理复阻抗，不要求调用者先猜参考阻抗或把它舍入成Γ。旧`noise_figure(gamma_source)`及noise默认Γ模式、完整输出和源功率余量判断保持不变。

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs noise examples/noise-source-impedance.ts '@examples/noise-source-ohms.json' NEW-NF.json
moon run examples/noise_source_impedance --target js
moon run examples/noise_source_impedance --target wasm-gc
```

文件例程使用噪声参考50Ω、Rn25Ω、Fmin0dB和Γopt0，S端口参考另为75/100Ω。物理源150Ω得到线性噪声因子5/3，即约2.218487496dB。公开包例程另实际消费50Ω与50+j50Ω，对应因子1与3/2；输出的`input_text/cases`只是该例程包装。

## API与单位

```moonbit
let doc = @rf.parse(text)
let curve_db = doc.noise_figure_impedance(@rf.complex(150.0))
```

方法返回原网络频率顺序上的dB数组，源为全频段常量复阻抗。两个分量须有限，实部严格大于0；零电阻、纯电抗、负电阻不具有此常规NF定义，直接raise。缺少噪声记录不当成显式无噪声，非二端口也不接受。确有一条零协方差记录则是合法理想模型，可以得到0dB。

物理源约定来自`doc.noise_reference_ohms()`，不是`doc.raw_network().reference_ohms()[0]`。文件中option line的R是噪声参考，2.x的`[Reference]`可另指定网络参考；2.x噪声记录Rn为物理Ω。原Γ入口仍要求相对于独立噪声参考的有限Γ且源功率余量为正。两种输入不混用，不自动替换参考或修改源。

## 文件模式及接收条件

```json
{"source_mode":"impedance","source_ohms":[150,0]}
```

新物理模式是专门的NF接收路径，输出以下字段：

| 字段 | 含义 |
|---|---|
| source_mode / source_ohms | impedance与实际物理[R,X] |
| noise_reference_ohms | 独立噪声参考Ω |
| network_reference_ohms | 文档原网络的参考向量 |
| frequency_hz / figure_db | 原频率顺序与对应NF曲线 |
| quantity / source_units / figure_units | source_noise_figure / ohm / dB |

物理模式只接受`ports/source_mode/source_ohms`这些用户选项。混入Γ的`source`、噪声圆阈值`figure_db`、未知字段或夹具路径均报错，夹具文件不会被读取。此模式不额外请求A/S相关矩阵或噪声圆，因此不为一个NF查询强加无关的S协方差转换条件。

省略`source_mode`仍走原Γ模式，`source`保持原来的必填含义；也可显式给`source_mode:"gamma"`。该路径仍输出原`a/s/figure_db/circles`四项。不要把旧输入中的`figure_db`圆阈值和输出的同名NF数组混为一谈。模式值须为已知字符串，不推断Ω/Γ单位。

成功退出0；配置、解析、模型、数值或IO错误退出2并写stderr。报告在计算完整后才写出，计算失败不输出部分数值曲线。沿用ASCII/预算和独占输出，已有目标、输入输出同路径或不存在的父目录不能覆盖/创建成成功报告。

## 计算及数值边界

复用既有Hermitian链噪声协方差及其插值：单条记录视作常量，多条记录不外推。若`C`已归一化除以4kBT0，物理源`Zs=R+jX`的同一二次模型为

`F = [R + C00 + 2 Re(C01) R + 2 Im(C01) X + C11 (R²+X²)] / R`。

它等价于`Fmin + Rn/Gs * |Ys−Yopt|²`，NF为`10log10(F)`。新方法复用原有二进制缩放乘积与抵消求和，保留R并在最后还原比例；既有Γ算法、增益缩放primitive、噪声参数/协方差模型和插值代码没有重写。有限输入若导致不可表示的最终线性因子或既有协方差模型错误，就明确失败，不钳位或伪造0/Infinity/NaN结果。

基础手写模型对纯实源R的独立因子为`R/100+25/R`。因此1e308Ω的NF仍约3060dB，而先转Γ会舍入到单位圆；旧Γ入口继续拒绝Γ=1。可表示的1e-300Ω也有有限结果；最小正subnormal源在该非零噪声模型下因子溢出则报错。显式零协方差模型的0dB不等于把溢出或缺失噪声变成0。

这是当前double与噪声模型下的有限数值能力，不提供全Double精度定理、连续频带或物理器件认证；噪声参考不等于仪器参考平面/校准证明。没有新增参考波、噪声模型、文件格式或通用报告框架。

## 独立接收验收

新[文件消费者](../tools/verify-noise-source-impedance.py)用冻结手写因子1、5/3、3/2和独立log10验值；稀疏协方差对应5/3、2、7/3，真实Document插值后为11/6、13/6。复最优源30+j40与反号源30−j40验证交叉项符号；独立噪声参考100Ω时源50Ω因子为9/8。Γ/Ω一致与原完整ΓJSON只作兼容控制，不是唯一数值oracle。

公开包例程在JS/Wasm-GC实际运行，输出的文本再写成真实文件供CLI消费；另有任意文件、实际S参考重归一化、独立噪声参考、零正向S视图、数值极端与错误/保护控制。新API7项黑盒测试两后端各通过；严格all-target检查不冒称新的native运行。物理模型、输入均为项目合成，不是新测量。

同类公式与用途参考[scikit-rf Network.nf](https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.nf.html)及其官方源代码；本项目既有归一化/单位约定见[RF0.3](RF-0.3.md)。不主张公式原创或生态唯一。
