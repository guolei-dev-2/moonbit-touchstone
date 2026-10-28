# 群时延采样限值

`Network::group_delay(output,input)`及`delay`返回逐点秒值。需要自动验收滤波器通带时，可使用新增的`Network::check_group_delay`或`delay-check`，保留原频点、违反位置和实际差分孔径，输出pass/fail/inconclusive。旧导数、解缠、`delay`数组及其他报告不变。

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs delay-check examples/group-delay.ts '{"start_hz":1000000,"end_hz":4000000,"input":0,"output":1,"minimum_seconds":0,"maximum_seconds":2e-7}' NEW-DELAY-REPORT.json
moon run examples/delay_check --target js
moon run examples/delay_check --target wasm-gc
```

文件示例的三个估计值为250ns、166.666…ns、125ns：第一点超过200ns，报告fail，CLI正常保存JSON并退出3。两个纯MoonBit例程输出相同含义的报告；普通例程进程退出0不代替报告的判定。

## 单位和范围

频段是有限、非负Hz闭区间，允许相等端点。`input/output`是原网络零起点端口；`minimum_seconds/maximum_seconds`至少给一个，须有限，若同时给出则前者≤后者。界限包含等号，没有隐式数值容差；0是有效限值，负延时和负秒界限也允许。

```moonbit
let report = net.check_group_delay(
  1.0e6, 4.0e6, input=0, output=1,
  minimum_seconds=0.0, maximum_seconds=2.0e-7,
)
```

先在完整原网络上调用既有`group_delay`，再选频段内原点。至少两个原频点，所选S[out,in]必须全迹线非零，计算须有限；即使零在选区外也按旧函数报错。新入口没有把未定义延时伪造为0、静默丢点或改为只在裁剪片段求导。

## 报告与孔径

`GroupDelayBandReport`的`scope`是`sampled_points_only`，`estimator`是`endpoint_or_centered_secant`，JSON的`kind`为`group_delay_band_report`。包含频段、端口、参考阻抗、显式number/null秒限、原点选中数、上下限违反计数及总失败数、覆盖、查询两端是否正好采到、带原索引的最低/最高估计和全部选中样本。空选区极值为null；数值并列时保留首个原点。

每条`GroupDelaySample`含`point/frequency_hz/delay_seconds`、`below_minimum/above_maximum/status`及`aperture_start_hz/aperture_end_hz`。差分孔径严格对应旧算法的原点max(i−1,0)到min(i+1,n−1)：全迹线两端为单侧割线，其余为中心割线，非均匀网格同样按这两个频率计算。选区边界的孔径可能伸到选区外，报告明确展示；没有插值、平滑或可配置仪器孔径。

| 状态 | 条件与CLI退出码 |
|---|---|
| fail | 任一选中估计违反有限界限，优先于范围未覆盖；退出3 |
| inconclusive | 没有已知违反，但无选中点或原频率范围未覆盖查询；退出4 |
| pass | 至少一个原点、范围覆盖且全部选中估计满足界限；退出0 |
| 错误 | 配置、原群时延计算或IO失败；退出2，没有伪造报告 |

单个原始点选区可以判定，因为导数先由完整迹线求得；选区内没有原点则不能通过。未正好采到查询边界但范围覆盖且有点时，报告只针对实际选中点。Node沿用原ASCII输入和独占输出规则，已有输出拒绝覆盖，fail/inconclusive报告仍可正常保存。未知选项（含夹具路径键）拒绝，不读取额外文件。

群时延取决于采样孔径和相位解缠。这里是现有S波定义下的离散估计，不保证连续频带、无混叠、仪器等价、因果性或器件认证；相邻真实相位变化≥π可能不能从采样恢复。参考：[scikit-rf群时延](https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.group_delay.html)、[Keysight延时与孔径说明](https://helpfiles.keysight.com/csg/e5080b/Tutorials/Comparing_the_PNA_Delay_Functions.htm)。不声称导数算法原创或生态唯一。

## 独立验收

新黑盒API测试覆盖均匀/非均匀手算相位、原点与孔径、负值/精确0、单点/空选区、覆盖与fail优先、非法秒限/频段/端口、少于两点及选区外零传输。[独立文件消费者](../tools/verify-delay-check.py)以精确四分之一圈相位比例给出秒值真值，实际执行新CLI的状态/输出/错误路径及双后端纯MoonBit例程，并单独控制旧delay数组保持；旧输出不是新数值oracle。

仅新增报告API、两种结果类型及一个文件命令；没有扩展既有BandMetric枚举或改动旧公共类型，没有新的Touchstone格式、噪声变换、参考波定义或运行依赖。
