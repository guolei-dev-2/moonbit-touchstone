# 噪声系数近单位圆源修复（第20轮）

本轮只核既有“二端口噪声文件→指定源Γ的噪声系数查询”。`Document::noise_figure`和`noise`命令的公共接口保持，源Γ相对于文档的正实噪声参考阻抗，合法域为有限复数且`1−ReΓ²−ImΓ²>0`。数学上的单位圆和域外没有常规正可用源功率，必须拒绝。

修复前用合法合成Touchstone 2.1文件复现。文件含1 GHz单点、Fmin=1 dB、Γopt=0、Rn=50 Ω，噪声参考50 Ω；普通匹配源成功得到约1 dB，相关矩阵满足既有物理检查。以下数值按JSON输入可表示的binary64分量计算；不是把十进制理想数视为无穷精度实数。

| 源Γ的实部、虚部 | 独立预期 | 修复前 | 修复后 |
| --- | --- | --- | --- |
| `1−2^-53`, `nextDown(2^-26)` | 320.34118276990307 dB | 162.55619765854985 dB | 320.34118276990307 dB |
| `0.6`, `nextDown(0.8)` | 164.7746851547134 dB | 162.55619765854985 dB | 164.7746851547134 dB |
| `1−2^-53`, `2^-26` | 域外，余量为`−2^-106`，应拒绝 | 误接受为162.55619765854985 dB | 以原域错误拒绝 |

第一个合法源的精确余量为`3·2^-106−2^-158>0`，对应的源实电阻为正。旧代码先取舍入后的模长g，再用`1−g²`检查域及作分母，掩盖这些差异。现仅在`noise.mbt`的`noise_figure`中复用库里已有的私有`gain_margin`，同时用于严格域检查与分母；不改该辅助函数，不加epsilon或钳位，不缩小合法域。

独立参考采用Python标准库Fraction保留输入binary64的精确分量，Decimal以160位计算原噪声参数公式。由[scikit-rf官方噪声圆关系式](https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.nf_circle.html)解得`F=Fmin+4(Rn/Zref)|Γs−Γopt|²/[(1−|Γs|²)|1+Γopt|²]`。本例简化为`10^0.1+4|Γs|²/(1−|Γs|²)`；不以生产代码的模长/相关矩阵转换或scikit-rf的double边界输出作为唯一判据。这是既有RF算法的数值修复，不主张新算法。

可运行文件例程：

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs noise examples/noise-source.s2p '@examples/noise-source-options.json'
moon test noise_source_test.mbt --target js --deny-warn
python tools/verify-noise-source.py --evidence NEW-NOISE-SOURCE.json
```

第20轮实际证据见[回执](../evidence/noise-source-20261028/independent-first.json)：新增3项公共API回归在JS/Wasm-GC/native各3/3；6个实际Node文件CLI进程、5项消费者检查通过，3个有限结果的绝对误差小于2e-11 dB。消费者检查还核对原输入字节、普通匹配源完整输出与修复前一致，以及合法请求中不依赖源的相关矩阵/噪声圆一致；单位圆、相邻域外及轴上1加非零最小次正规虚部均明确拒绝。修复前四次CLI及失败数值也保留于证据，不以成功覆盖原问题。

本轮没有重跑历史集合、增加厂家输入或扩大文件格式；噪声矩阵、插值、级联/去嵌入、噪声圆、GT和Node逻辑保持。有限dB结果不代表器件测量性能、认证或全double域正确；原先线性噪声因子不可表示、缺失/不可实现噪声记录等错误边界保持。没有新Ω源查询、线性因子溢出的对数专用返回、发布或赛事提交。
