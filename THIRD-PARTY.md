# 来源与许可边界

项目源码 MIT。Touchstone 格式规范来自 [IBIS](https://ibis.org/touchstone_ver2.1/)；规范与公式参考不作为本项目可重新许可的文档内容。没有复制标准全文。

独立开发参考为 scikit-rf 2.1.0（BSD-3-Clause）、NumPy 2.5.3（BSD-3-Clause）、SciPy 1.18.1（BSD-3-Clause）；仅在开发/参考环境安装，不作为 MoonBit 运行依赖。由它们产生的合成测试数据与真实厂家测量分开记录。

Johanson S2P/PDF 的再分发许可未确认，所以只给下载 URL、SHA-256、重现代码和少量数值事实，不附原始文件，不将其放入 MIT 源码许可范围。详见 [公开样本说明](docs/PUBLIC-SAMPLE.md)。

NXP BFU530W 官方 S 参数模型的再分发许可同样未确认；原 ZIP、S2P 及完整数值导出不随源码附送，也不按 MIT 再许可。固定 URL、哈希、选定偏置及98频点的历史核对见 [NXP来源说明](evidence/public-breadth-20261027/README.md)。

近邻还有 Rust touchstone crate 等成熟实现，不能声称转换/级联是本项目首创。Mooncakes 查重及候选决策见团队交接包；未发现同名包不能证明生态没有同类。

RF极值独立回执为说明参考分歧摘录了scikit-rf2.1.0的max_gain属性源码，其BSD版权/许可保留于 [scikit-rf-LICENSE.txt](evidence/rf-extreme-repair-20261028/scikit-rf-LICENSE.txt)。该摘录属于独立验证来源，不是本库MoonBit实现代码，也不按MIT重新许可。

09轮匹配功率裕量修复参考[Priest/Shewchuk浮点展开资料](https://www.cs.cmu.edu/~quake/robust.html)中的既有数值方法，自行在MoonBit中实现有界平方分裂与TwoSum展开；不主张算法原创，未引入其软件发行包或分发论文/C源码。新NXP核对仍沿用上述私有输入与有限数值事实边界。
