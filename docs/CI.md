# GitHub Actions 验证

`.github/workflows/ci.yml` 对 push、pull request 和手动运行执行真实验证。普通 Ubuntu 24.04 runner，单个 `check` job，25分钟上限；只授予仓库内容读取权限。没有自动发布、付费或自托管 runner 配置。

SDK 固定为 `.moonbit-version` 的 `0.10.14+7d59c7ec9`，安装到该次 runner 的临时目录。使用[官方 Unix 安装器](https://cli.moonbitlang.com/install/unix.sh)，先核本次审阅的安装器 SHA256，再由 `tools/ci-identity.py` 核实际编译器版本。安装器更改会使校验失败，需审阅后更新；不会静默改用最新 SDK。

checkout、setup-node、setup-python 和 upload-artifact 使用经官方仓库核对的提交 SHA。Node 24、Python 3.14 的实际补丁版本及全部 Python 包版本会写入该次回执；三个直接数值参考依赖由 `tools/requirements.txt` 精确固定。安装和验证失败会直接令 job 失败。

验证包含格式检查、四后端严格类型检查、完整 JS/Wasm-GC 单元测试、release JS 构建、生成公共接口差异检查、Node 文件 CLI、scikit-rf/NumPy/SciPy 独立解析及 RF/频段/波动对照。短截线示例在 JS 和 Wasm-GC 上实际构造 Network、级联并端接负载，再由独立物理 ABCD 模型复核；既有 band_check、rf_03 及一端口消费者继续执行。最后检查模块封包与全部已跟踪源码没有运行时改写。

新回执统一写入 `_build/ci/`，不覆盖源码附带的历史证据。`tools/verify-rf.py --evidence PATH` 可以指定本次输出，省略参数仍保留旧默认位置；其内部固定的案例日期属于历史 fixture 元数据，实际执行时点以 GitHub run 和 identity 回执为准。

`verification-<commit SHA>` artifact 保留7天，含提交/树身份、各源文件 SHA256、实际工具/依赖版本和独立验值 JSON。GitHub run 的终态及每个必要 job 才证明该次远端验证完成；README 或旧证据里的日期、数字都不能替代它。artifact 到期后可在同一提交重现，不把重复跑绿计为新的功能轮次。

后续有内容的改动应先给出实际场景与预期，完成必要代码、独立回归及文档，再核同一仓库同一提交的真实 CI。首次完整导入为阶段0，不计后续11轮；没有有价值的候选时如实记录，不拆分文件或空提交凑数。
