# 森羅物語：酒館 — 非官方 Bedrock 移植

種植、釀酒、調酒，打造自己的小酒館。本 addon 將 [Kaleidoscope Tavern](https://github.com/KaleidoscopeMods/KaleidoscopeTavern) 帶到 Minecraft 基岩版。

[English](README.md) · [下載](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/releases) · [更新紀錄](CHANGELOG.md)

## 功能

- 種植釀酒材料，發酵酒品、調製雞尾酒。
- 用酒瓶、酒櫃、座椅與可自訂文字的告示板布置酒館。
- 在遊戲內酒館指南查閱配方與器具用法。
- 可搭配「醉世界」擴充酒品，或將指南整合到 Cookery。

這是仍在開發的獨立移植，並非官方版本。部分效果與操作和 Java 不同，畫面及音效尚未完成全部客戶端驗證；具體限制見[功能對照](docs/PARITY-MATRIX.md)。

## 安裝

1. 備份世界，從 **Releases** 下載 `.mcaddon`，不要下載 GitHub 的原始碼 ZIP 當作安裝包。
2. 匯入 Minecraft 基岩版，在世界中同時啟用行為包（BP）和資源包（RP）。
3. 使用該版本要求的 Minecraft 版本與實驗設定；若搭配醉世界，須安裝它指定的精確酒館版本。

酒館有獨立指南，**不需要 Cookery**。可選配套須另行取得；下載不包含它們或私有伺服器整合。配方與機器用法請在遊戲內指南查閱。

## 語言

- 資源文字提供 **English、简体中文、繁體中文**；另收錄部分上游日文、俄文翻譯，缺項回退英文。
- 指南支援英文、簡中、繁中，請在指南設定內選擇；預設繁中，不會跟隨 Minecraft 客戶端語言自動切換。
- 部分機器拒絕操作的提示仍只有繁中。語言檔鍵值齊全不等於每個介面都已翻譯。

## 開發

需要 Python 3 與 Node.js。正式來源在 [`runtime/BP`](runtime/BP/) 和 [`runtime/RP`](runtime/RP/)。

在乾淨、已提交的 checkout 執行：

```sh
python3 tools/check_release.py
python3 tools/build_release.py
```

產物輸出至 `dist/`。[`baseline.json`](baseline.json) 記錄來源版本與精確相依；開發主線可能比公開下載更新。參與修改先讀 [AGENTS.md](AGENTS.md) 與[基線維護](docs/BASELINE-MAINTENANCE.md)，並執行受影響功能的既有檢查。

## 問題回報

請提供 addon／Minecraft 版本、配套包、實驗設定、重現步驟，以及預期與實際結果。畫面或音效問題請附截圖或短片；先查看[已知問題](docs/BUGS.md)，不要公開私人世界、憑證或第三方完整包。

## 鳴謝與授權

原作：**Kaleidoscope Official Production Team／YSBB**。Bedrock 移植：**casama233 與貢獻者**。本專案不代表原作者或 Minecraft 官方。

程式碼採 [BSD-3-Clause](LICENSE-CODE)，原始及衍生美術採 [CC BY-NC-SA 4.0](LICENSE-ASSETS)。其他資產保留各自條款，詳見[鳴謝](CREDITS.md)。
