# 混合模CMRR与损耗的稳定dB计算

`Document::mixed_mode_metrics(output_pair,input_pair,cmrr=...)`与现有`modal-metrics`文件入口使用相同的混合模矩阵和功率波约定。两种模态的比值可能有有限dB，即使其中一个线性模长已超出double范围；不应把中间溢出写成`cmrr_state="finite"`和字符串`"NaN"`。

[合成四端口文件](../examples/modal-scale.s4p)用D1,2 D3,4 C1,2 C3,4顺序，50Ω单端参考，对应100/100/25/25Ω模态参考。Sdd21=Scc21=1.5e308+j1.5e308，其他选中转换项为零。复分量均有限，文件能合法解析；相等幅度的balanced CMRR应为0 dB，差分插损约−6166.532125137753 dB。它是尺度反例，既不是无源模型，也不是实际器件测量。

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs modal-metrics examples/modal-scale.s4p '@examples/modal-scale-options.json'
```

旧实现先取溢出后的线性模长，返回`cmrr_db="NaN"`和`differential_insertion_loss_db="-Infinity"`，同时把CMRR标为finite。修复仅在`mixed_mode.mbt`增加私有对数模长辅助函数：正常有限非零模长仍取原`log10(magnitude)`路径；溢出时用`log10(scale)+0.5log10((re/scale)²+(im/scale)²)`，scale为最大分量绝对值。它不计算超出范围的线性模长，也不加epsilon、钳位或拒绝原合法输入。

CMRR定义保持：balanced取Sdd/Scc，input取Sdd/Sdc，output取Sdd/Scd。分子和分母皆为精确零时为undefined；仅分母零为positive_infinity，仅分子零为negative_infinity；两者非零时为finite且`cmrr_db`是有限数值。其余状态省略`cmrr_db`。模态损耗的精确零保持None（JSON字段缺席），代表正无穷损耗；不把它伪造为有限数值。这些状态不是本轮新增协议。

已有解析、模式顺序/参考阻抗、单端变换、Complex::magnitude、GT/helper、噪声、Node和所有公共库接口保持。CMRR是功率波幅度比，不自动换成差分放大器电压增益定义。非S参数仍须先满足原转换条件；这里没有稳定性、无源性或器件认证承诺。

开发验收入口：

```sh
moon test modal_scale_test.mbt --target js --deny-warn
python tools/verify-modal-scale.py --evidence NEW-MODAL-SCALE.json
```

独立参考用Python标准库Decimal100，直接计算`−10log10(re²+im²)`及`10log10(norm_desired/norm_denominator)`，不调用生产模长或缩放辅助函数。新增3项公共API回归在JS/Wasm-GC/native各3/3；9次实际文件CLI／7项消费者检查通过，覆盖原合法反例、三种CMRR定义、四项模态损耗、四类零比值状态及普通输入完整输出字节一致，见[回执](../evidence/modal-scale-20261028/independent-first.json)。没有重跑旧全套或增加厂家输入。

定义来源：[Keysight Balanced Measurements](https://helpfiles.keysight.com/csg/e5080a/s1_settings/balanced_measurements.htm)的balanced-to-balanced差分/共模传输比，以及[scikit-rf混合模矩阵约定](https://scikit-rf.readthedocs.io/en/latest/examples/mixedmodeanalysis/Mixed%20Mode%20Basics.html)。这是既有数值表示的修复，不主张新RF算法或全double域正确性。
