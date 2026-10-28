# 显式端接后导出可复用文件

用复Γ/Ω负载关闭多端口模型中的指定端口后，常需把剩余二端口交给GT、频段报告或其他Touchstone消费者。原`terminate`提供网络JSON分析；16轮独立`terminate-file`将相同既有运算结果写成Touchstone，避免用户另写JSON转文件程序。端接算法、原命令输出和公共库API保持。

## 实际文件链路

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs terminate-file examples/loaded-four-port.ts '@examples/terminate-four-port.json' NEW-TWO-PORT.ts
node tools/touchstone.mjs gain-record NEW-TWO-PORT.ts '@examples/terminated-gain-check.json' NEW-GAIN-RECEIPT.json
node examples/terminate_file_demo.mjs NEW-OUTPUT-DIRECTORY
```

项目合成四端口在原端口1接75+j15Ω、端口2接25−j10Ω，保留原端口0/3；新文件将其编号为0/1，参考仍是50/75Ω。后续GT用100+j20Ω源、30−j12Ω负载，0.9–1.1GHz、3–10dB限值，刻意得到fail并正常保存回执、退出3。示例脚本接受一个尚不存在、父目录已存在的目录，生成降维文件与该失败回执；脚本成功退出0表示流程按预期完成。

选项[terminate-four-port.json](../examples/terminate-four-port.json)为：

```json
{"terminations":[[1,75,15],[2,25,-10]],"impedance":true}
```

`terminations`必填，每项为`[原始零起点端口,实部,虚部]`。默认`impedance:false`表示无量纲复Γ；true表示Ω。数组为空时输出现有单端S视图，仍保留全部端口。至少一个端口须保留，不增加排序参数；其余端口按原编号升序留下，频率和原始频点索引保持。三元组长度、精确整数端口、重复/越界及未知键均校验；新命令不读取夹具路径。

第四个参数可省略，Touchstone输出到标准输出；否则独占创建文件，已有路径拒绝覆盖。成功退出0，配置/格式/数学/IO错误退出2，不把奇异反馈写成伪造有限网络。合法有限复负载与主动端接沿用既有算法的范围；新的文件入口没有追加被动性限制。后续GT的源/负载功率域则按其独立约定检查。

## 文件与元数据约定

新入口通过`Document::network_only()`取得单端网络，再调用`Network::terminate_ports`和既有Document writer，输出规范化的单端S Touchstone。混合模输入因此不会把过时的Mixed-Mode Order带到降维结果。输入已有的信息行保留；排版、注释或原始字节不逐字保留。

带噪声记录的文档明确拒绝，因为现有端口降维没有对应的噪声方向/端口数变换，不能把原二端口噪声赋给新网络。没有噪声记录不等于证明实际器件无噪声。原`terminate`作为纯网络JSON分析的旧语义不变；文件新入口没有静默删除噪声的开关。

输出文件不会自动认证原多端口输入、负载选项或原端口映射。请一并保留原文件和端接选项。后续`gain-record`绑定实际降维文件的字节与GT查询，v1协议没有变成多步骤的来源认证。频点索引保持的是频率序列，端口编号已按上述规则重新编号。

纯MoonBit调用方本来即可组合既有API，无新增方法：

```moonbit
let reduced = doc.network_only().terminate_ports(
  [(1, @rf.complex(75.0, im=15.0)), (2, @rf.complex(25.0, im=-10.0))],
  impedance=true,
)
let text = @rf.document(reduced, information=doc.information_lines()).write()
```

此片段适用于没有噪声记录的文档；完整可运行的文件例程见[terminate_file_demo.mjs](../examples/terminate_file_demo.mjs)。数学和格式处理在MoonBit，Node仅负责文件/argv/桥接及示例步骤调度，无新运行依赖。

## 验收与边界

持续CI还运行[新鲜五端口文件链](../tools/verify-termination-chain.py)：乱序关闭0/2/4、保留1/3并核60/90Ω参考，按完整原五端口波方程精确分数解独立核导出S和后续GT，另独立解码实际导出字节。Γ等价/主动合法对照与噪声拒绝、输入和占用输出保护均使用新生成数据；不改变原域/IO政策，不把下列历史脚本裸重跑算新成果，也不声称修复了生产计算缺陷。

主验收由24个已通过的CLI前缀用例与修正噪声夹具后的3个剩余用例组成，共27个用例、19项消费者检查；不再次执行已通过前缀。6个GT点以独立原四端口全部入射波方程求解，覆盖Ω、Γ主动内部负载和带显式信息行的混合模输入。参考直接施加四个端口的源/负载条件，不用降维矩阵或同一Schur公式充当唯一真值。

实际文件覆盖标准输出/落盘、信息/参考/端口顺序读回、空端接、后续GT/回执复核、非法选项、分数/重复/越界/全删端口、带噪拒绝、奇异反馈、拒绝覆盖和输入不变。原`terminate`JSON与实现前新输入基线相等。示例另以2个工具CLI子进程运行；基线2个进程单独记录。开发期两处夹具错误的失败记录保留，未算作旧端接算法缺陷。

严格all-target编译、格式与生成接口检查通过。桥接支持JS，本轮不将未运行的Wasm/native数值套件算新覆盖；旧RF/GT/CSV/回执全套及厂家集合没有重跑。新输入均为项目合成，不是新测量或厂家认证。

原始命令、参考和验证组合见[完整消费者证据](../evidence/terminate-file-20261028/independent-complete.json)、[检查](../evidence/terminate-file-20261028/CHECKS.json)及[设计](../evidence/terminate-file-20261028/DESIGN.md)。同类连接与写出已有成熟用途，见[scikit-rf Circuit](https://scikit-rf.readthedocs.io/en/v2.1.0/tutorials/Circuit.html)和[write_touchstone](https://scikit-rf.readthedocs.io/en/v2.1.0/api/generated/skrf.network.Network.write_touchstone.html)。差异是本项目原生MoonBit端接到GT文件消费入口，不主张算法原创、唯一或通用电路/仪器兼容认证。
