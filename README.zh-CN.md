# 森罗物语：酒馆 — 非官方 Bedrock 移植

种植、酿酒、调酒，打造自己的小酒馆。本 addon 将 [Kaleidoscope Tavern](https://github.com/KaleidoscopeMods/KaleidoscopeTavern) 带到 Minecraft 基岩版。

**简体中文** · [繁體中文](README.zh-TW.md) · [English](README.md)

[下载](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/releases) · [更新记录](CHANGELOG.md)

## 功能

- 种植酿酒原料、发酵饮品并调制鸡尾酒。
- 用酒瓶、酒柜、座椅和可自定义文字的告示板装饰酒馆。
- 通过游戏内的酒馆指南查询配方和设备用法。
- 与「世界名酒」（World Liquor）配合扩展酒品，或选择将指南整合进 Cookery。

这是仍在开发的独立移植，**并非官方版本**。部分效果和操作与 Java 版仍有差异，画面与音效尚未完成全部客户端验证；详见[功能对照](docs/PARITY-MATRIX.md)。

## 安装

1. 备份世界，从 **Releases** 下载 `.mcaddon`，不要把 GitHub 源代码 ZIP 当成安装包。
2. 导入 Minecraft 基岩版，同时启用行为包（BP）和资源包（RP）。
3. 使用该版本所需的 Minecraft 版本和实验设置；若搭配世界名酒，必须使用它指定的**精确 Tavern 版本**。

酒馆有独立指南，**不需要 Cookery**。可选配套必须另外获取；本下载不包含配套包或私有服务器整合。配方和机器用法请查看游戏内指南。

## 语言

- 资源文字支持 **English、简体中文、繁體中文**；另外包含部分上游日文及俄文翻译，缺失的文本会回退到英文。
- 指南支持英文、简体中文、繁体中文，可在指南设置中选择；**默认繁体中文**，不随 Minecraft 客户端语言自动切换。
- 部分机器的操作拒绝提示仍只有繁体中文。语言文件存在对应条目，不意味着所有界面已完成翻译。

## 开发

需要 Python 3 和 Node.js。正式来源位于 [`runtime/BP`](runtime/BP/) 和 [`runtime/RP`](runtime/RP/)。

在干净且已提交的工作区执行：

```sh
python3 tools/check_release.py
python3 tools/build_release.py
```

构建产物输出至 `dist/`。[`baseline.json`](baseline.json) 记录来源版本及精确依赖；开发主线可能比公开下载版本更新。修改前请阅读 [AGENTS.md](AGENTS.md) 和[基线维护](docs/BASELINE-MAINTENANCE.md)，并执行受影响功能已有的检查。

## 问题反馈

请提供 addon 与 Minecraft 版本、配套包、实验设置、复现步骤，以及预期与实际结果。画面或音效问题请附截图或短视频；先查看[已知问题](docs/BUGS.md)，不要公开私人世界、凭据或第三方完整资源包。

## 致谢与许可

原作：**Kaleidoscope Official Production Team／YSBB**。Bedrock 移植：**casama233 与贡献者**。本项目不代表原作者或 Minecraft 官方。

代码采用 [BSD-3-Clause](LICENSE-CODE)，原始及衍生美术采用 [CC BY-NC-SA 4.0](LICENSE-ASSETS)。其他资产保留各自许可，详见[致谢](CREDITS.md)。
