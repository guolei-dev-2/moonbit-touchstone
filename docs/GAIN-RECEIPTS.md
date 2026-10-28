# GT回执与复核

普通`gain-check`报告能说明终端、限值和判定，但没有绑定原文件。12轮增加可选`gain-record`和`gain-review`，将实际读取的字节与有效查询保存，再用当前本地实现复算比较。旧`gain-check`输出不变；解析、GT及采样报告算法不变，公共库API没有新增或修改。

## 实际文件用法

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs gain-record examples/power-gain.s2p '@examples/gain-check-ohms.json' NEW-RECEIPT.json
node tools/touchstone.mjs gain-review examples/power-gain.s2p '@NEW-RECEIPT.json'
```

第一条文件命令故意使用4–7dB限值，保存`fail`回执并返回3；第二条复算一致，返回0，JSON中的`recorded_status`和`current_status`仍是`fail`。自动化脚本应允许第一步的预期分析退出码，不能用仅接受0的命令链跳过复核。

已随包提供与原合成文件绑定的示例，不需要先创建输出：

```sh
node tools/touchstone.mjs gain-review examples/power-gain.s2p '@evidence/gain-receipt-20261028/receipt-fail.json'
node examples/gain_receipt_demo.mjs NEW-OUTPUT-DIRECTORY
```

示例脚本只接受一个尚不存在的目录，其父目录须已存在；保存失败回执和成功复核结果。两个CLI命令均可用第四个参数保存JSON，已有文件拒绝覆盖；省略时输出到标准输出。选项或回执可用`@文件`提供，沿用ASCII、1MB预算；输入沿用ASCII、64MB预算。

## 回执内容与有效条件

封套`schema`固定为`touchstone.gain-receipt.v1`，根对象只有以下四个键：

| 键 | 内容 |
|---|---|
| schema | 协议版本字符串 |
| input | `sha256`为64位十六进制，`bytes`为实际字节数 |
| request | `command:"gain-check"`及有效查询条件 |
| result | 原`gain-check`的完整JSON结果，保持其结构 |

`gain-record`接收与[gain-check](GAIN-CHECK.md)相同的选项。MoonBit将默认`terminal_mode:"gamma"`、默认源/负载`[0,0]`展开；Ω模式保留`source_ohms/load_ohms`，频段以Hz、界限以dB保存。未给的可选界限不写入，显式0界限必须保留。若传入或由`.sNp`文件名推得`ports`，将有效提示一并保存；自带端口声明的`.ts`无须该提示。复核使用保存的提示，因此相同字节改名不会被新的文件后缀误导。

Node只对本次读取并传给MoonBit的同一个ASCII字符串做SHA256和字节计数，不另开文件取指纹。注释、空格、CRLF/LF均参与身份；字节变化即要求新回执，即使网络数值等价。封套不保存文件路径、用户身份、时间或执行文件认证。

## 复核结果与退出码

基本封套、schema、输入元数据及记录状态有效后，先比较SHA256和长度。任何一个不同即返回`input_mismatch`，不解析网络、不重算GT。身份相同时只允许执行保存的`gain-check`请求，由MoonBit重新计算并比较完整解析JSON。根键顺序、嵌套对象顺序、空白和等值数字写法不影响比较；数组顺序、值以及结果中增加/缺少的键有意义，比较不使用数值容差。

| 命令/退出码 | 含义 |
|---|---|
| gain-record 0 / 3 / 4 | 保存的采样判定为pass / fail / inconclusive |
| gain-review 0 | `status:"reproduced"`，输入及完整结果一致 |
| gain-review 5 | `status:"input_mismatch"`或`"result_mismatch"` |
| 两者 2 | 配置、回执、格式、域、重算或文件IO错误 |

复核JSON的`kind`为`gain_receipt_replay`，包含`status`、`input_match`、`result_match`、`recorded_status/current_status`、记录/当前`input`、`changed_sections`和`current_result`。输入不一致时`changed_sections`为空数组、`current_result`为null，`result_match/current_status`也为null；它没有声称结果曾被比较。结果不一致时`changed_sections`列出发生变化的结果顶层键，`current_result`供用户查看本次判定。

格式错误、未知schema和缺少身份直接报错；请求只可指定`gain-check`，其余查询选项在身份一致后的重算时校验，错误仍返回2。旧普通报告会给出需要重新`gain-record`的错误；不自动给历史报告补一枚当前文件指纹。回执不能执行其他命令，也不读取其中嵌套的夹具路径。用户注释请放在封套外，避免改动协议或结果。

复核仅说明“这份输入、所存条件与当前实现能复现所存结果”。这是无签名回执；持有人可同时修改请求和结果后另造一致记录，因此不证明作者、原始时间、历史未改、真实性或跨版本数值等价。`reproduced`不能代替采样pass，更不代表连续频带、稳定性或器件认证。

13轮增加[逐点CSV审阅](GAIN-CSV.md)，可配合回执交付选中采样点的明细。CSV不包含输入身份、终端条件或参考阻抗，不能替代此回执；已有v1协议仍只重放gain-check，不接受gain-csv。

## 实测与职责

持续CI另运行[新鲜文件审计链](../tools/verify-gain-file-chain.py)：四点手写网络独立计算GT，与同一实际输入生成的回执、复核及CSV联检；包含原始CRLF字节、等长非法输入的先身份后解析、结果/条件篡改和占用输出保护。它不依赖下列历史封存结果，补持续消费验收，不声称发现了产品计算缺陷或增加RF算法。

新增[文件示例](../examples/gain_receipt_demo.mjs)实际保存fail并成功复现。[独立Python消费者](../tools/verify-gain-receipt.py)使用标准库hashlib和协议断言，41个实际CLI进程/30项工作流检查覆盖Γ/Ω、三种判定、0上下限、CRLF、改名、版本化文件、改输入/结果/请求、JSON重排、hex大小写、非法回执及旧报告。另2个实际CLI进程/2项检查覆盖复核JSON保存和拒绝覆盖，共43/32；演示的2个子进程另行记录，不重复计入。

两次旧普通`gain-check`输出与封存11轮参考相等，没有重跑旧39请求/27份报告或数值全套。NXP只做固定输入的身份及复现流程，复用封存汇总参考，不计新增GT数值对照；原厂输入、矩阵和完整GT输出不随包分发。

桥接为JS专用，本轮实际运行Node24.11.0及固定MoonBit工具链；严格all-target编译与格式检查通过，没有将未运行的Wasm/native流程算作新覆盖。MoonBit负责条件规范化、既有报告重算和结构比较，Node只处理IO、参数、指纹和退出码。设计、检查和原始命令见[封存证据](../evidence/gain-receipt-20261028/FINDINGS.md)、[41进程回执](../evidence/gain-receipt-20261028/workflow-first.json)及[输出分支回执](../evidence/gain-receipt-20261028/review-output-check.json)。没有新增运行依赖。

已调查[Mooncakes notary](https://mooncakes.io/docs/hcjbat/moonbit-notary)的通用证据模式、[moonldif0.7.0](https://mooncakes.io/docs/WeiR-h/moonldif@0.7.0)的另一领域输入身份/复核模式，以及[Node crypto](https://nodejs.org/docs/latest-v24.x/api/crypto.html)标准接口。本项目增加的是Touchstone实际终端GT的文件消费步骤，不主张新密码学、通用公证或生态唯一。
