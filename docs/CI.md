# GitHub Actions 验证

`.github/workflows/ci.yml` 对 push、pull request 和手动运行执行真实验证。普通 Ubuntu 24.04 runner，单个 `check` job，25分钟上限；只授予仓库内容读取权限。没有自动发布、付费或自托管 runner 配置。

SDK 固定为 `.moonbit-version` 的 `0.10.14+7d59c7ec9`，安装到该次 runner 的临时目录。使用[官方 Unix 安装器](https://cli.moonbitlang.com/install/unix.sh)，先核本次审阅的安装器 SHA256，再由 `tools/ci-identity.py` 核实际编译器版本。安装器更改会使校验失败，需审阅后更新；不会静默改用最新 SDK。

checkout、setup-node、setup-python 和 upload-artifact 使用经官方仓库核对的提交 SHA。Node 24、Python 3.14 的实际补丁版本及全部 Python 包版本会写入该次回执；三个直接数值参考依赖由 `tools/requirements.txt` 精确固定。安装和验证失败会直接令 job 失败。

验证包含格式检查、四后端严格类型检查、完整 JS/Wasm-GC 单元测试、release JS 构建、生成公共接口差异检查、Node 文件 CLI、scikit-rf/NumPy/SciPy 独立解析及 RF/频段/波动对照。短截线示例在 JS 和 Wasm-GC 上实际构造 Network、级联并端接负载，再由独立物理 ABCD 模型复核；既有 band_check、rf_03 及一端口消费者继续执行。最后检查模块封包与全部已跟踪源码没有运行时改写。

新回执统一写入 `_build/ci/`，不覆盖源码附带的历史证据。`tools/verify-rf.py --evidence PATH` 可以指定本次输出，省略参数仍保留旧默认位置；其内部固定的案例日期属于历史 fixture 元数据，实际执行时点以 GitHub run 和 identity 回执为准。

`tools/verify-gain-file-chain.py --evidence _build/ci/gain-file-chain.json`专门验收新鲜输入的GT文件审计链，不引用历史数值payload。它按独立有理数功率公式检查四点的GT/CSV值、零与奇点空值，真实保存失败回执并成功复现，再核等长非法输入/换行字节变化、结果/源条件篡改及已有输出保护。业务fail的退出3、复现成功的退出0和身份/结果不一致的退出5分别断言，不用忽略退出码吞掉失败。

`tools/verify-termination-chain.py --evidence _build/ci/termination-chain.json`生成耦合五端口并保留原1/3端口，以完整五端口Fraction波方程核导出矩阵和Ω增益；有限独立解码器核当前writer的2.1/RI字节及端口顺序，再由现有消费者读回。Ω/Γ等价与主动Γ合法对照、信息保留、带噪输入的旧网络入口合法/新文件入口拒绝，以及占用、输入输出同路径、缺失父目录、真实奇点保护都执行真实CLI。它不复用旧四端口fixture或历史baseline，也不是新产品解析器。

群时延限值的纯MoonBit例程在JS/Wasm-GC真实运行，再由`tools/verify-delay-check.py`用手算相位比例核秒值、原点、孔径、状态及新CLI错误/文件分支。新API黑盒测试随完整两后端单测执行；旧delay作为兼容控制，未充当独立真值，旧数值算法没有重写。

`tools/verify-s-compare.py`使用冻结的两频两端口分数案例，真实消费两份原始文件，核相位翻转delta1和3-4-5比例delta5/16、8元素计数、原坐标/全局及每Sij见证、双源字节身份和read-once。严格条件不兼容、声明不足、噪声排除、不可表示运算和文件错误均有真实CLI；旧gain-review改字节仍input_mismatch。此桥接消费者在JS执行，不把all-target检查记为新Wasm/native运行。

物理源NF公开包例程在JS/Wasm-GC实际输出曲线与参考条件，`tools/verify-noise-source-impedance.py`以独立手写因子和Decimal实阻公式核对，再经真实文件消费。覆盖S参考变更/独立噪声参考、稀疏协方差插值、复最优源符号、极端正源/不可表示因子、旧Γ完整输出和输入/输出保护。新API黑盒测试随两后端全套执行，没有重写或移除旧科学门。

`Consume finite Cartesian DB input and output`运行`examples/db_cartesian`的JS/Wasm-GC公开包接收者，再由`tools/verify-db-cartesian.py`以90位Decimal原始预期核全部DB字段、复矩阵、单位/参考/信息及真实文件消费。保留普通输出、真正分量溢出、MA/零DB及独占输出错误；未改变旧科学门或公共接口，也不将类型检查当作native运行。

`Consume finite group-delay seconds from package and files`实际运行JS/Wasm-GC公开包，再以`tools/verify-delay-finite-seconds.py`的100位Decimal atan级数/数学π及手算割线核完整秒值与限值报告。真实文件接收覆盖正/负/零、原点/孔径、首个极值、fail/覆盖/空选区、真溢出和独占输出；普通完整旧输出兼容控制保留，没有改变旧科学生成器或将检查当作native运行。

原频点导出的双后端公开包及`tools/verify-crop.py`实际写出、独立解码、文件读回并计算旧指标，核原始整数/分数矩阵、完整元数据及独立反射/VSWR/dB。新门和错误/身份边界见[CI-PLAN](../CI-PLAN.md)；原门全部保留，手工显式频率组合仍是兼容控制，不被冒充缺陷。

`verification-<commit SHA>` artifact 保留7天，含提交/树身份、各源文件 SHA256、实际工具/依赖版本和独立验值 JSON。GitHub run 的终态及每个必要 job 才证明该次远端验证完成；README 或旧证据里的日期、数字都不能替代它。artifact 到期后可在同一提交重现，不把重复跑绿计为新的功能轮次。

后续有内容的改动应先给出实际场景与预期，完成必要代码、独立回归及文档，再核同一仓库同一提交的真实 CI。首次完整导入为阶段0，不计后续11轮；没有有价值的候选时如实记录，不拆分文件或空提交凑数。
