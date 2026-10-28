# mixed文件转换的信息行修复

第16轮记录了`mixed`文件入口遗漏原Information信息行的相邻项。17轮核对当前承诺后将其闭环：README和SCOPE要求不静默丢弃信息元数据，而输入解析器和Document writer本已支持该信息块。因此修复的是既有文件路径，不新增格式或RF算法。

## 可运行反例与修复

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs mixed examples/mixed-information.ts '@examples/mixed-information-options.json' NEW-MIXED.ts
node tools/touchstone.mjs inspect NEW-MIXED.ts
```

项目合成三端口文件包含两频点、50/50/75Ω参考及3行Information。选择原端口0/1作为差分对，输出模式仍是D1,2、C1,2、S3。修复前转换成功、矩阵和模态正确，但实际输出重读的信息行从3变成0；修复后保留原3行，包括信息行内的`!`注释文字。

库的`Network::to_mixed_mode`只接收网络，本来无从知道文件信息；CLI先取`network_only()`再调用它，获得的新Document没有原信息。修复仅将文本写出改为使用既有`document`构造器接回原`information_lines()`，同时保留转换结果的原始网络、噪声参考和模态顺序。返回的network/order字段及所有模态计算代码不变。

无Information输入的输出文本与旧版逐字相同，已有混合模输入也只保留一份原信息。原带噪文件转换仍拒绝，不绕过既有噪声边界。文件拒绝覆盖、合法输入域、公共库API、端接/GT/报告/回执协议均保持。保留的是解析后的信息行，未承诺保留整个源文件的排版、注释或原始字节，也不解释新的信息关键字。

## 标准与项目承诺的区别

[IBIS Touchstone2.1第28页](https://www.ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf)描述可选Information块，并允许消费者忽略或由外部引用覆盖信息。本项目选择了更严格的信息保留承诺；此次不能被夸成“标准强制所有消费者保留信息”的修复。已有MoonBit Document API和writer足够完成，无新依赖、上游代码复制或通用元数据框架。

## 验证与历史边界

修复前4个Node进程记录合法输入/旧输出及无信息控制。修复后首次定向回归8个实际Node进程（3次直接编译桥接、5次文件CLI）、6项检查通过：

- 独立Python文本提取器逐行核对预期3行，删除新增Information块后与旧文本完全相同；network/order与旧快照精确相等。
- 无信息控制的完整解析响应与旧快照相等，text逐字相同。
- 实际CLI落盘和重新读取保留信息、频率、单端参考及混合模顺序。
- 已混合模合法输入的信息保留一次；新三端口输入经mixed→terminate-file后，单端降维文件继续保留信息和频率。
- 合法带噪二端口仍报错且不写输出。

第16轮当前验证工具曾无条件插入Information块；现在仅在块缺失时补测试夹具，避免修复后生产者已有信息时重复插入。该适配只改当前工具的夹具准备段，未改16轮冻结回执、参考脚本或数值断言，也没有重跑其27用例/6GT点。旧RF/GT/CSV/回执/厂家集合未重跑，无新增数值对照或厂家输入。

严格all-target编译、格式与生成接口检查通过。实际改动位于JS桥接，本轮没有将未运行的Wasm/native数值套件算作新覆盖。[独立消费者](../tools/verify-mixed-information.py)、[实现前反例](../evidence/mixed-information-20261028/BASELINE.json)、[实现前响应](../evidence/mixed-information-20261028/BEFORE-RESPONSES.json)及[修复后回执](../evidence/mixed-information-20261028/independent-first.json)保留来源和具体命令。

16轮历史记录的“report-only未修复”保持原日期；该项在17轮修复，没有回写历史。新源码/模块包和最终身份由本轮RESULT及DELIVERY-CHECK记录，仅本地交付，未推送、发布或提交赛事。
