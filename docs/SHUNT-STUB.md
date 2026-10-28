# 单并联理想短截线匹配

`synthesize_shunt_stub(load_ohms, reference_ohms~, termination~, tolerance?=1e-10)` 在一个设计点综合单并联短截线。主线与短截线均为理想、无损、均匀线，具有相同的正实特性阻抗 `reference_ohms`，采用 exp(jωt)。这是独立的纯 MoonBit 库入口，复用现有 Complex 和 Network。

## 输入、单位与主周期

- `load_ohms: Complex` 是有限负载阻抗 Ω，`reference_ohms` 必须有限且大于零；负电阻及非有限输入抛出 Failure。
- `termination: StubTermination` 必须显式选择 `Open` 或 `Short`，没有默认端型。
- 距离从负载向信号源量，到该平面并联短截线。返回主线距离 θ=βd 与短截线长度 φ=βℓ，单位为弧度；另给各自导波波长比例 θ/(2π)、φ/(2π)。没有传播速度、基板或频率输入，不输出毫米尺寸。
- θ、φ 的主周期均为 `[0, π)`，即波长比例 `[0, 1/2)`。加整数倍 π 是同一理想单频解，不另列；距离与短截线长度不可互换。
- `tolerance` 必须有限且 `0 < tolerance < 1`，是离散解的绝对归一化输入导纳误差限 `|Z0 Yin − 1|`。它不改变负载域、精确已匹配分类、主周期或分支数。

## 返回合同

`ShuntStubMatch` 保存输入、端型、容差、`state`、`detail`、`solutions` 及 `free_distance_stub_radians`。`ShuntStubSolution` 含两种长度的弧度、波长比例和实际计算的 `normalized_admittance_error`。

| state | 含义与完整解集 |
|---|---|
| `finite` | 严格正电阻、非精确已匹配负载；返回主周期内两条有限离散解，按主线距离递增排序；连续族字段为空。两条解都通过声明的导纳误差限才成功。 |
| `already_matched` | 输入精确满足 `Re(ZL)==Z0 && Im(ZL)==0`。`solutions` 为空；连续距离族字段给透明短截线的固定 φ：开路为 0，短路为 π/2。所有 θ∈[0,π) 均为解，不以两个代表冒充穷举。 |
| `no_solution` | 有限被动负载的实部精确为零，包括短路及纯无功负载。无损网络无法产生实功率耗散以匹配正实 Z0；没有离散解或连续族。 |
| `numerical_limit` | 正电阻非匹配负载在数学上有两解，但当前 Double 无法完整表示/区分，或正向残差不能满足所要求容差。解数组和连续族均为空；`detail` 说明原因。不把它称为物理无解，也不静默丢弃一条解。 |

非常接近匹配的有限输入仍走非匹配路径；不以 epsilon 吞掉负载虚部。未通过验证的局部候选不对外返回。`finite` 是本理想单频模型的数值结果，不是实物或全频性能认证。

## 算法与奇点

将输入按 max(R,Z0,|X|) 缩放。以负载反射相位旋转到归一化电导为 1 的两个交点，再求对应的开/短短截线电纳。交点的缩放反射方向为 `(-D, ±2√(RZ0))`，其中 `D=√((R−Z0)²+X²)`；实现使用缩放量、hypot 与 atan2，避免直接形成过大的乘积或以 `R−Z0` 作分母。

主线 θ=π/2 是 tan 坐标的极点，但不是物理奇点，必须保留。例如 ZL=50+j50Ω、Z0=50Ω 有 θ=π/2 和 θ=π−atan(1/2) 两条解。开路短截线 φ=π/2、短路短截线 φ=0 才是无限并联电纳，不能作为有限解；若舍入命中这些位置，返回 `numerical_limit`。非匹配候选若舍入成透明短截线或两条完全相同的解，同样不宣称完整成功。

离散候选随后用 sin/cos 传输线输入导纳与短截线电纳相加检查 `|Z0 Yin−1|`。极端比例导致缩放分量下溢、近匹配相位消失、极点附近消减或过严容差都可能给 `numerical_limit`；不承诺整个有限 Double 域都能综合。

## 独立正向验收与消费者

[可运行示例](../examples/shunt_stub_match/main.mbt) 将综合结果转换成当前 Network API 的主线和并联 ABCD 网络，级联后以真实负载阻抗端接，读取一端口 S11 及已有指标。运行：`moon run examples/shunt_stub_match --target js`，或 `--target wasm-gc`。JSON 同时保留综合状态、每条解与实际 Network 消费结果。

独立验收使用另一实现的物理 ABCD 正向模型：`L=[[cosθ,jZ0sinθ],[j sinθ/Z0,cosθ]]`，`P=[[1,0],[j bs/Z0,1]]`，其中开路 `bs=tanφ`，短路 `bs=−cotφ`；取 `M=P·L`，`Zin=(A ZL+B)/(C ZL+D)`，检查 Γin 与 Zin，而不重做综合根求解。普通样例使用角度模 π 距离 ≤2e−12 rad、`|Γin|≤2e−11`、`|Zin/Z0−1|≤1e−10`。恰在主周期切口附近，0 与趋近 π 按周期比较，不要求跨后端分支位级相同。

手算覆盖 100Ω、25Ω、50+j50Ω、100+j50Ω（Z0=50Ω），每种端型的两条分支；另有普通复负载、连续距离族、纯无功、非法输入和数值限制。独立预期先于新实现形成，来源与执行回执在本轮交付报告中。

范围止于这一个理想单并联短截线模型。不包含不同短截线阻抗、串联/双短截线、微带制造尺寸、基板色散/损耗、Q 或带宽优化、自动 CAD 以及仪器校准；无纳秒级或零分配性能承诺。

参考：[Zahn, Stub Tuning](https://eng.libretexts.org/Bookshelves/Electrical_Engineering/Electro-Optics/Electromagnetic_Field_Theory%3A_A_Problem_Solving_Approach_%28Zahn%29/08%3A_Guided_Electromagnetic_Waves/8.05%3A_Stub_Tuning)，[scikit-rf Impedance Matching](https://scikit-rf.readthedocs.io/en/latest/examples/matching/Impedance%20Matching.html)。方程按上述电压/电流及距离约定使用；本轮独立数值验收采用解析 ABCD，不声称运行了 scikit-rf 优化器。
