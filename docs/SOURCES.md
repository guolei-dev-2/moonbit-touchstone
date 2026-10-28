# 来源、验证工具与样例

本库自身采用根目录MIT LICENSE，格式和RF运算独立实现于MoonBit。
不是scikit-rf绑定，不包含其Python算法源码或上游示例数据集。

| 外部来源 | 角色 | 许可证或使用边界 |
|---|---|---|
| [IBIS Touchstone 2.1](https://www.ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf) | 文件布局、参数和元数据语义 | 链接规范，不重新分发规范全文 |
| [Qucs技术文档](https://qucs.sourceforge.net/tech/node6.html) | 源/负载功率增益与双向输入反射定义，eq1.49–1.57 | 链接数学定义，未复制上游代码或文档全文 |
| [scikit-rf2.1.0电路连接说明](https://scikit-rf.readthedocs.io/en/v2.1.0/tutorials/Circuit.html) | 10轮物理终端输入的同类能力/边界调查 | 链接既有电路能力，不复制上游实现；独立参考用自行建立的戴维南波方程 |
| [scikit-rf频段裁剪](https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.crop.html)、[Keysight迹线限值说明](https://helpfiles.keysight.com/csg/89600B/Webhelp/Subsystems/gui/content/mnu_utilities_limittests.htm) | 11轮选点与限值流程的同类调查 | 仅链接功能资料；本项目采样/未知状态合同自行明确，不复制代码或声称仪器认证 |
| [hcjbat/moonbit-notary0.1.0](https://mooncakes.io/docs/hcjbat/moonbit-notary)、[WeiR-h/moonldif0.7.0](https://mooncakes.io/docs/WeiR-h/moonldif@0.7.0) | 12轮通用证据清单/输入身份及另一领域复核模式调查 | 仅查阅公开说明，未导入/复制代码；回执不是这些工具的替代或安全属性声明 |
| [Node24 crypto](https://nodejs.org/docs/latest-v24.x/api/crypto.html) | 12轮文件宿主用标准createHash计算SHA256 | 使用Node内置API，无新增依赖或自制散列算法；实际CLI运行版本24.11.0 |
| [MoonFrame0.5.5](https://mooncakes.io/docs/ihb2032/MoonFrame@0.5.5)、[moonlake0.5.0](https://mooncakes.io/docs/superbigcup325/moonlake@0.5.0) | 13轮MoonBit表格/CSV与下游查询能力调查 | 查阅版本化公开说明，未导入/复制代码，不将定制RF表格称为通用CSV创新或已验证集成 |
| [scikit-rf表格导出](https://scikit-rf.readthedocs.io/en/latest/_modules/skrf/io/general.html)、[Keysight迹线CSV导出](https://helpfiles.keysight.com/csg/e5072a/measurement/data_output/saving_trace_data_to_a_file.htm) | 13轮射频数据交给表格工具审阅的既有流程 | 仅链接参考；本项目CSV列是自己的GT审阅契约，不声称仪器/Excel兼容认证 |
| [scikit-rf2.1.0 Circuit](https://scikit-rf.readthedocs.io/en/v2.1.0/tutorials/Circuit.html)、[Touchstone写出](https://scikit-rf.readthedocs.io/en/v2.1.0/api/generated/skrf.network.Network.write_touchstone.html) | 16轮带负载多端口转外部端口网络并写文件的同类调查 | 既有流程参考，无新增依赖或复制代码；独立原四端口波方程自行建立，不以自己降维再读回为唯一真值 |
| [Shewchuk浮点展开资料](https://www.cs.cmu.edu/~quake/robust.html) | 09轮复匹配功率裕量中的平方分裂/TwoSum展开 | 链接既有数值算法资料，本地MoonBit实现；不附C代码或论文全文 |
| [scikit-rf](https://github.com/scikit-rf/scikit-rf/blob/master/LICENSE.txt) | 2.1.0 独立网络与格式对照 | BSD-3-Clause |
| [NumPy](https://github.com/numpy/numpy/blob/main/LICENSE.txt) | 2.5.3 数组/复数矩阵参考 | BSD-3-Clause |
| [SciPy](https://github.com/scipy/scipy/blob/main/LICENSE.txt) | 1.18.1 参考验证环境 | BSD-3-Clause |

2026-09-22核对上游许可证文本；版本由tools/requirements.txt锁定。
这些Python库仅开发验证依赖，不进入MoonBit库/Node CLI运行路径，源码ZIP不包含其发行包。
表内是项目主许可证，不代表依赖二进制轮子的全部第三方组件许可；
若将来一并分发参考环境，应保留各发行包原有的完整许可与版权文件。

examples/attenuator.s2p及常规测试矩阵、噪声和频率数据由本项目合成；
合成验证脚本调用参考库产生/读取临时文件。另有 Johanson 与 NXP 官方公开模型输入的有限历史核对，
来源、日期、哈希与范围分别见 PUBLIC-SAMPLE.md 和 ../evidence/public-breadth-20261027/README.md。
原厂文件及完整数值导出不随源码分发；这些是厂商模型输入，不是本项目新做的设备测量。
evidence记录参考结果和源码散列，不表示上游或设备厂商认证。AI辅助事实保留。

频段示例及 band-limits.json 也是本项目合成数据/要求，不是实际产品的合格指标。
`tools/verify-bands.py` 复用独立 scikit-rf 数值属性与 NumPy 掩码，不导入本库计算结果作为真值；
VSWR 有源反射、采样不充分、明细截断和判定优先级为本项目明确制定的接口契约，见 docs/BANDS.md。
