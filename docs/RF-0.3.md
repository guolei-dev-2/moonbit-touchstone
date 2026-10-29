# Touchstone 0.3.0 射频计算约定

本轮在 MoonBit 核心实现模态、噪声与放大器计算。独立数值回执及六项工程检查见 [CHECKS](../evidence/review-20261023/CHECKS.json)；API 完整签名见 [pkg.generated.mbti](../pkg.generated.mbti)。

## 模态与参考阻抗

`Network::mixed_mode(order)` 的 order 使用 Touchstone 的 D/C/S 模式项（文件端口为一基）；`to_mixed_mode(pairs)` 用零基端口对，输出 D 对、C 对、未配对 S 端口顺序的 Document。`single_ended(order, single_reference_ohms)` 还原单端。

同一差分对两端参考阻抗相等，不同对可不同。差分电压 Vd=V+−V−，差分电流 Id=(I+−I−)/2；共模 Vc=(V++V−)/2，Ic=I++I−，所以有效参考 Zd=2Z0、Zc=Z0/2。变换由电压/电流关系导出，S/Y/Z 的数值缩放不能混用。任意不相等的对先由调用者显式重归一化到选定共同阻抗。

文件 `[Reference]` 保存原单端参考值；`Document::modal_network()` 返回模态矩阵及有效 D/C/S 参考，`single_ended_network()`/`network_only()` 返回还原的单端网络。`raw_network()` 是文件原样矩阵，不得直接假定单端。SDD/SDC/SCD/SCC 按输出模式/输入模式区分；`mixed_mode_metrics(output_pair,input_pair)` 提供差分损耗与模式转换/CMRR，精确字段以生成接口为准。

`mixed_mode_metrics(..., cmrr="balanced")` 默认按平衡至平衡 VNA 的 `20log10(|Sdd/Scc|)` 定义。`cmrr="input"` 为 `Sdd/Sdc`（相同差分输出对不同输入模式的抑制）；`cmrr="output"` 为 `Sdd/Scd`（差分激励的输出平衡）。结果的 `cmrr_definition` 标明选择，三个比值不能混称同一种 CMRR。它们是功率波幅度比，不是差分放大器的电压增益 CMRR；电压定义还须计入 D/C 参考阻抗。默认平衡网络定义依据 [Keysight Balanced Measurements](https://helpfiles.keysight.com/csg/e5080a/s1_settings/balanced_measurements.htm)。旧实现默认 Sdd/Scd，现在须显式选择 output 取得该比值。

分子分母皆为精确零时CMRR为undefined；仅分母零为positive_infinity，仅分子零为negative_infinity，其余为finite。非有限状态省略`cmrr_db`。模态损耗的精确零幅度以None表示正无穷；有限dB不使用NaN/Infinity字符串。线性模长中间溢出时按分量缩放求对数，保留可表示的CMRR与损耗；详见[混合模dB修复与例程](MODAL-SCALE-REPAIR-20261028.md)。原有限模长计算路径与三种定义保持。

## 噪声相关矩阵

Document 保存二端口 Fmin（dB）、Γopt 和 Rn（ohm）及噪声频率/参考。`noise_correlation(representation="A"|"S")` 使用 Haus-Adler 链或散射相关矩阵，归一化除以 4kBT0；不是声称从没有温度信息的文件测得了绝对噪声功率。

`interpolate` 对 Hermitian 链噪声矩阵做分段线性插值，并同步网络；一条噪声记录按频率不变处理，多条记录禁止外推。`cascade` 同时组合传输和噪声相关矩阵；`deembed` 用左右夹具的网络与相关矩阵恢复 DUT，不只对 S 做逆运算。提供没有噪声记录的夹具时，其数学契约为显式零附加噪声，不自动推断其温度热噪声；真实有损夹具应给出相应噪声模型。

`noise_figure(gamma_source)` 计算指定合法源反射下的实际噪声系数（dB）；`noise_circles(figure_db)` 返回等噪声系数曲线。源反射须在物理允许域，去嵌入结果必须符合噪声可实现性条件；不能把负噪声或数学奇点伪装成合法有限参数。

源Γ相对于文档的`noise_reference_ohms`，须有限且`1−Re(Γ)²−Im(Γ)²>0`。20轮[源功率余量修复](NOISE-SOURCE-REPAIR-20261028.md)从复分量保留很小的正余量，并同时用于合法域检查和噪声系数分母；不以先舍入的模长或容差钳位代替。单位圆及域外仍拒绝；这不新增Ω源入口、噪声记录或不可表示线性噪声因子的支持。

后续逻辑第5轮追加授权[物理源Ω查询NF](NOISE-IMPEDANCE.md)：独立`Document::noise_figure_impedance`及noise的`source_mode:"impedance"`直接接收Re(Zs)>0的有限复Ω源，明确噪声参考与网络参考。沿用协方差/插值模型，只输出NF及条件；上面20轮的历史终点、原Γ入口与默认schema不变。

噪声计算检查相关矩阵的半正定性：先按参考阻抗归一化电压/电流单位，再以相对 1e-11 容差检查主子式。Rn、Fmin 为正仍不足以证明可实现。原始测量记录的语法解析与物理检查分开，解析可保留不可实现的测量值；涉及噪声数学运算时明确拒绝。不能把格式可读误写成物理模型合法。

## 链参数、端接与放大器

`Network::convert("ABCD")`：`[V1,I1]ᵀ = A[V2,-I2]ᵀ`，ABCD 分量单位分别为 1、ohm、siemens、1。

`convert("T")`：`[b1,a1]ᵀ = T[a2,b2]ᵀ`。这与 scikit-rf 的 a/t 约定一致；理想直通可以有有限链表示，而某些 Z/Y 表示可能奇异。ABCD/T 是分析表示，写 Touchstone 前应显式转回 S/Y/Z/H/G，不扩展文件的合法 option line 参数。

`deembed(left,right)`要求频网匹配、夹具外部参考与测量一致且夹具链可逆，恢复DUT参考为left.port1/right.port0。无噪声记录时，测量S21精确零也可恢复有限S；采用约去可去奇点的等价式，不构造无定义的被测T。非零传输路径不变，真正恢复极点仍拒绝。带噪路径仍需原链噪声表示可实现，不新增零传输噪声模型；详见[截止频点去嵌入](DEEMBED-ZERO-20261028.md)。

`terminate_ports(terminations, impedance=false)` 的端口为零基，默认复数值是 ΓL；`impedance=true` 时为复阻抗 ZL，按端口参考换算。对被端接子块求解反馈/Schur 补，保留其余端口的原顺序和参考，不能只删矩阵行列；奇异反馈明确拒绝。

阻抗端接实际使用齐次条件D·a=N·b，N=ZL−Z0、D=ZL+Z0，并按二的幂缩放；ZL=−Z0是Γ表示的极点，若完整反馈系统可逆仍可求解，不能单凭Γ不可表示拒绝。极大K下的有限MAG和小非零Rn也保持原物理语义，见[RF极值修复](RF-EXTREME-REPAIR-20261028.md)。

`stability()` 给出每点频率、|Δ|、K、输入/输出 μ、无条件稳定标志、线性功率 MSG/MAG 与 gain_state。MAG 只有在适用的稳定条件下才有定义；单向器件使用相应解析分支。可空指标和状态表示无定义/不适用，不应当作零。

`stability_circles(source=...)`、`gain_circles(gain,source=...)` 与噪声圆以广义方程 `a|Γ|²−2Re(conj(b)Γ)+c=0` 表示，允许圆、直线、空集和全平面；center/radius 只在相应状态有定义。gain 是线性功率比，不是 dB；source 选择源或负载平面。

## 无源性与容差

`Network::diagnostics(tolerance=1e-9)` 沿用既有的复Hermitian耗散矩阵H=I−SᴴS移位Cholesky测试，容差是无量纲绝对量，必须有限且0<ε≤0.01。依次判定：

- H−εI严格正定：`passive`。
- 前者不成立，H+εI严格正定：`boundary`。
- 其余：`active`。

在精确算术中对应最小特征值>ε、−ε<λmin≤ε、λmin≤−ε。严格正定与半正定不同：理想无损/奇异PSD在boundary，容差带内的轻微负特征值也可能在boundary，不能自动视为严格无源合格。浮点切点附近不作认证保证。Cholesky不是SVD、不输出奇异值，ε也不是IBIS文件规范规定的通用阈值。

上一轮只新增边界回归和文档，未改变这个算法或公共API。55请求的独立分组、实际观察误差及单位见 [API与证据约定](API.md#验证职责与历史记录)；不要把全部请求都标成scikit-rf数值对拍或新增夹具标定。

## 复现与标准

```sh
moon build --target js --release --deny-warn
moon run examples/rf_03 --target js
moon run examples/rf_03 --target wasm-gc
node tools/touchstone.mjs rf-convert examples/attenuator.s2p '{"parameter":"ABCD"}'
node tools/touchstone.mjs stability examples/attenuator.s2p
```

新 CLI 的完整选项以 `node tools/touchstone.mjs --help` 及桥接实现为准；独立差分的命令、容差、参考版本及实际通过数记录在 CHECKS。无噪声/混合模的原 CLI 继续兼容，文件拒绝覆盖规则不变。

| 命令 | 选项与返回 |
|---|---|
| rf-convert | `{"parameter":"ABCD"}` 或 `"T"`，返回网络 JSON |
| mixed | `{"pairs":[[0,1],[2,3]]}`，返回保留原Information信息行、带模态顺序的文档；输出路径写Touchstone，17轮修复说明见[记录](MIXED-INFORMATION-REPAIR-20261028.md) |
| single / modal | 无必需附加选项；分别返回单端/有效模态网络 JSON |
| single-file | 无必需附加选项；还原单端基底并写完整文档，保留信息/参考；已单端噪声保留，混合模噪声明确拒绝；[完整约定](SINGLE-ENDED-FILE.md) |
| modal-metrics | `{"output_pair":1,"input_pair":0,"cmrr":"balanced"}`，返回所选差分对指标 |
| terminate | `{"terminations":[[1,0.2,0.1]],"impedance":false}`；true 时复数为 ohm，返回降维网络 JSON |
| stability | 可选 `{"gain":1.0}`，返回稳定性、源/负载稳定圆及可用/工作增益圆 |
| noise | `{"source":[0.2,0.1],"figure_db":3}`，返回 A/S 相关矩阵、噪声系数和噪声圆 |
| noise物理源模式 | `{"source_mode":"impedance","source_ohms":[150,0]}`，返回NF dB曲线及物理源/独立噪声参考条件，不请求A/S或圆 |
| cascade / deembed / interpolate | 原有参数接口，现在通过 Document 同时传播网络与噪声 |

纯 Network JSON 是明确的确定性网络视图，不声称输出了完整带噪文档。CLI 的 noisy `mixed`、noisy `select` 与 noisy `legacy` 会明确拒绝：这些输出没有实现对应的噪声模态/端口重排传播，不能静默丢弃或保留错误方向的参数。`convert`/`renormalize` 保留同一物理噪声相关矩阵及独立 noise_reference；带噪的插值、级联和双夹具去嵌入均有 Document 接口。

独立数值复现（先完成上面的 JS release 构建）：

```sh
python -m pip install -r tools/requirements.txt
python tools/verify-rf.py
node tools/check-cli.mjs
```

新数值回执 [rf-20261023/reference.json](../evidence/rf-20261023/reference.json) 与原格式/矩阵回归分开保存；总检查收集实际命令、退出码和源文件绑定。不能把自己变换再逆变换作为唯一数值对照。

模态标准依据 [IBIS 2.1 的混合模章节与附录 A](https://www.ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf)。相关矩阵、链表示、稳定性与圆的独立参考是 [scikit-rf Network](https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.html)，上游实现与算法归属按 [THIRD-PARTY](../THIRD-PARTY.md) 说明。当前回执不构成全频因果性或设备认证。
