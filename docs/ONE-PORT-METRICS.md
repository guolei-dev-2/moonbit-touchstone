# 从一端口阻抗扫频读取回损与VSWR

应用显示输入匹配状态时，不能把匹配点的无穷回损、全反射的无穷VSWR和主动反射的无定义VSWR画成同一个有限数字。现有`Network::metrics(output,input)`提供数值、损耗无穷标志和`vswr_state`，不需要另写射频公式或解析器。

运行[公开模块示例](../examples/one_port_metrics/main.mbt)：

```sh
moon run examples/one_port_metrics --target js
```

示例只导入`guolei-dev/touchstone`，调用`parse(text).network_only().metrics(0,0)`，输出`input_text`及`metrics`数组。`input_text/metrics`外层是这个示例的包装，不是新增库或CLI协议。合成输入为Touchstone2.1 Z RI、50Ω正实参考、5个频点；Z数值是物理ohm。没有厂家模型或测量数据。

| Z（Ω） | Γ=(Z−50)/(Z+50) | 回损 | VSWR |
| --- | --- | --- | --- |
| 0 | −1 | 0 dB | 无穷，state=infinite |
| 50 | 0 | 无穷，return_loss_infinite=true | 1，state=finite |
| 150 | 0.5 | 约6.02060 dB | 3，state=finite |
| −150 | 2 | 约−6.02060 dB | 无定义，state=active |
| 50+j50 | 0.2+j0.4 | 约6.98970 dB | 约2.61803，state=finite |

`SignalMetric`的JSON省略None字段：零反射的`return_loss_db`和`insertion_loss_db`缺席，由对应`*_infinite`标志说明；全反射或主动反射的`vswr`缺席，由`vswr_state`区分。不要把字段缺席当成0，也不要仅靠字段缺席判断物理原因。

本例一端口且output=input=0，因此通用结构中的`transmission_magnitude`与`insertion_loss_db`也取S11。这是所选矩阵元素的标量投影，不是二端口穿透损耗或增益测量。真正二端口传输应选择不同的input/output。负实Z在此是合法有限主动网络模型；它不表示无源器件合格。

同一文本保存到文件后，现有入口为：

```sh
node tools/touchstone.mjs metrics INPUT.s1p '{"input":0,"output":0}'
```

文件CLI直接输出指标数组。需要核对模块和文件行为时，先按README构建release JS bridge，再运行开发用验收工具：

```sh
python tools/verify-one-port-consumer.py --evidence NEW-ONE-PORT-CONSUMER.json
```

工具执行一次模块示例，取它实际输出的文本按原ASCII字节写入真实.s1p，执行一次文件CLI，核对完整指标数组及上述解析预期。需要使用特定本地Moon工具时可给`--moon PATH`。输出证据路径和同名`.cases`目录必须尚不存在。Python只用于独立开发验收，库和示例运行不依赖Python。

公式采用[scikit-rf官方阻抗/VSWR关系](https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.tlineFunctions.zl_2_swr.html)，回损为`−20log10|Γ|`。主动反射的VSWR状态沿用本项目合同，不将原始公式在|Γ|>1时的负数称为合法无源VSWR。本例没有新增数值算法、格式、API或命令，也不保证所有有限double、连续频段或实际器件性能。本次5点模块/文件消费者证据见[独立回执](../evidence/one-port-consumer-20261028/independent-first.json)；历史全套没有重跑。
