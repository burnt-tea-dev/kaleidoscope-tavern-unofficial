# 森羅物語：酒館（非官方）

Kaleidoscope Tavern 的 Bedrock 移植，包含釀酒、調酒、家具、儲物與共用酒館指南。[English](README.md)。

## 安裝與目前來源

公開下載使用 [Releases](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/releases)，同時啟用 BP／RP，並使用該版列出的相依。Git 主線是開發來源，不能當成伺服器已安裝或正在運行的版本。

目前來源版本、包身份和精確相依只維護在 [baseline.json](baseline.json)。已審查的家族輸入見 [family/upstream.lock.json](family/upstream.lock.json)。變更查 [CHANGELOG](CHANGELOG.md)，公開來源與驗收界線查[家族狀態入口](family/BASELINE-STATUS.md)；舊 README 快照不代表今天的部署。

## 開發與驗證

先讀 [AGENTS](AGENTS.md)、[基線維護](docs/BASELINE-MAINTENANCE.md)及適用的[家族更新流程](family/UPDATE-WORKFLOW.md)。建置直接打包已提交的 runtime：

```sh
python3 tools/build_release.py
```

開發時做相關檢查，完整必要套件交由既有 CI。[功能對照](docs/PARITY-MATRIX.md)及[玩家回報](docs/BUGS.md)保留已實作、已知差異和待驗項目。開服及來源檢查不等於畫面、音效或真人驗收；私人整合是另一個私有附加包。

## 授權與歷史

原碼 BSD-3-Clause；原始及衍生美術 CC BY-NC-SA4.0。見 [CREDITS](CREDITS.md)、LICENSE-CODE、LICENSE-ASSETS。先前版本快照留在 [Git 歷史](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/blob/bb9e7cfb32b642ccfa563a1d3aca2abc9e744453/README.zh-TW.md)。
