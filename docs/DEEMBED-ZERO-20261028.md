# 截止频点的已知夹具去嵌入

截止或隔离样本的S21可以精确为零，同时整个DUT S矩阵有限。已知左右夹具可逆时，恢复有限S不应额外要求DUT在每个频点都有正向传输。例如两侧理想直通夹具应保持全零S的匹配隔离网络不变。

现有API和命令保持：`Network::deembed(left,right)`、`Document::deembed(left,right)`和`deembed`文件入口。此处覆盖没有噪声记录的有限网络。频网须严格匹配，夹具外侧参考与测量一致，夹具链须可逆；结果端口参考是左夹具内侧和右夹具内侧。没有自动插值、隐藏重归一化或未知夹具提取。

运行[匹配隔离网络](../examples/deembed-opaque.s2p)与[直通夹具](../examples/deembed-thru.s2p)：

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs deembed examples/deembed-opaque.s2p '@examples/deembed-zero-options.json' NEW-DUT.s2p
node tools/touchstone.mjs metrics NEW-DUT.s2p '{"input":0,"output":1}'
```

输出保留原测量的Information行；文件输出须选择尚不存在的路径。`metrics`对零传输给出`insertion_loss_infinite=true`并省略有限损耗字段，不把它伪造成0 dB。示例为项目合成数学模型，不代表实测器件或热噪声推断。

旧实现先构造被测T矩阵，对S21除零，因此合法隔离文件虽能解析，在直通夹具下去嵌入仍报`zero complex denominator`。修复仅对S21精确零使用等价形式；非零时保留原链矩阵计算。

以下m为被测S，数学矩阵索引为一基。设A=T(left)⁻¹，B=T(right)⁻¹，P=[[-m11·m22,m11],[-m22,1]]，K=A·P·B。由非零m21时T(m)=P/m21可推得恢复S为：

`[[K12/K22, m12·det(A)·det(B)/K22], [m21/K22, −K21/K22]]`。

其中`det(A)=left.S21/left.S12`、`det(B)=right.S21/right.S12`。约去公共m21后，该式可在m21=0且K22非零时恢复有限S，并保持反向传输及相位；代码数组索引为零基。夹具仍先经过原可逆性检查，K22=0的真正恢复极点仍报错；没有加epsilon、钳位或扰动。

Document仅在实际需要噪声协方差传播时才做原ABCD转换。没有噪声记录的DUT不再因无关ABCD表示而失败。带噪路径原有物理/链表示检查保持，不新增零传输噪声模型。`cascade`原有非零正向链表示限制没有在此扩大。

开发验收：

```sh
moon test deembed_zero_test.mbt --target js --deny-warn
python tools/verify-deembed-zero.py --evidence NEW-DEEMBED-ZERO.json
```

独立参考用Fraction从连接边界波方程生成测量数据，恢复值与原始DUT比较，不调用生产T/ABCD算法。3项新增API测试在JS/Wasm-GC/native各3/3；实际文件链8次调用、9项检查通过，其中6次成功、2次为预期拒绝。覆盖理想夹具恒等性、不同内外参考、零/非零混合频点、反向传输/相位、写出重读、后续指标消费、普通输出字节一致及错误边界，见[回执](../evidence/deembed-zero-20261028/independent-first.json)。未重跑历史集合或增加厂家模型。

已知夹具逆操作也见[scikit-rf官方Network实现](https://scikit-rf.readthedocs.io/en/latest/_modules/skrf/network.html)。这里的零传输延拓是现有链关系的代数推导，不是新校准方法、全double域正确性或连续频带认证。
