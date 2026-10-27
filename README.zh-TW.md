## 當前維護來源

當前來源及精確相依以 [baseline.json](baseline.json) 為準，已審查家族配對見 [family/upstream.lock.json](family/upstream.lock.json)。原生瓶擺放朝向玩家的反方向，藥水顯示與創造模式選取共用嚴格唯讀儲存；WATER／EMPTY維持Java無持久物品資料的行為。取消指南設定仍返回原指南，設定按鈕顯示目前語言名稱。既有三語、個人音量、廚房臨時語言、存檔鍵及音效行為保持；保留依[第三方設計審查](docs/THIRD-PARTY-TAVERN-REVIEW.md)自行實作的導航改善。這些是來源實作說明，不代表真人通過。

**公開下載：[酒館 v0.6.185](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/releases/tag/v0.6.185)**，本輪已審查配套為世界名酒 0.1.164 及可選 Grilling 2.8.157。公開檔案只含自有 Tavern BP/RP，不含作者包或私人整合；一般匯入不會組裝完整家族。精確作者相依見下方與公開家族 lock。

**發布範圍（2026-10-27）：** v0.6.185 由來源 `06c7c97cb2b0dbf0b7181660e1347b2f08d190a4` 發布，21 個上傳資產已全部下載並核對。當日本輪 T185/G157/W164 配套已通過完整家族原生首啟／重啟及資料保存檢查；此固定範圍結果不代表真人玩法、畫面或客戶端驗收通過。

**部署記錄：** 實際伺服器身份、私人整合版本、部署時間與正式收據留在私人維護記錄；本頁不抄易變的 LIVE 運行狀態。公開版本與驗收界線見[家族現況與修復主線](family/BASELINE-STATUS.md)。

目前仍需**全部物品Blockbench第一人稱／側面貼圖檢查**及具體玩法、聲畫與真人驗收。T160側面、T167游標與T169圖形過期修補已保留；詳見[差距矩陣](docs/PARITY-MATRIX.md)和[玩家回饋](docs/BUGS.md)。`client=false`、`production_ready=false`、`pending_client_acceptance`。

**歷史範圍：** 原 T183／G155 來源候選與 T170／G149／W148 穩定通道發布保留各自版本與證據。後者依使用者已核准的來源／編輯器／CI／包證據發布；本次整理不新增該發布的真人門檻，也不把兩份舊記錄重標為 T185 驗收。[早期README完整記錄](https://github.com/casama233/kaleidoscope-tavern-unofficial/blob/115942e55e9946cfd257fbcdc41c849f75b77509/README.zh-TW.md)與逐版說明保留原範圍。

# 森羅物語：酒館（非官方）

Java酒館的基岩版移植，包含釀造、調酒、酒架／酒櫃、家具與獨立酒館指南。指南保留共用七入口；Cookery整合使用同一份內容。[English](README.md)。

## 現行來源與需求

- 版本及精確相依以 [baseline.json](baseline.json) 為準；更新見 [CHANGELOG.md](CHANGELOG.md)。
- 來源、公開下載、倉庫最後記錄的部署與驗收統一見[家族現況](family/BASELINE-STATUS.md)；[PR處置](docs/audit/PR-DISPOSITIONS.md)保留歷史來源。
- 基岩版1.26.50以上；目前引擎目標為BDS1.26.52.3。BP與RP兩側一起啟用。
- Cookery 可選；本輪公開作者來源為 Cookery 1.6.4、ChineseFood 1.0.6，精確 UUID／版本及配對以[公開家族 lock](family/upstream.lock.json)為準；世界名酒須搭配其宣告的酒館版本。
- 升級前備份世界並移除重複舊包。私有料理整合是另一個識別明確的addon，不是私有酒館分支。
- 使用含reviewed integration Cookery RP修補的家族候選時，真人驗收前須乾淨安裝資源包，或只移除舊Cookery RP後重新安裝／下載。替換伺服器檔案不能證明客戶端已刷新；見[Cookery RP安裝前提](family/COOKERY-RP-INSTALLATION.md)。

## 建置

現有檢查工具使用Python3.12+、Node22+及Pillow11.3.0。

```sh
python3 tools/build_release.py
```

打包器直接封装已提交runtime/BP、runtime/RP，輸出至dist/。無需私服目錄、舊產物或玩法補丁。生成器是明確的來源編輯工具，不是一般打包前置。

## 驗證與限制

本機只跑受影響的既有檢查，完整必要套件交canonical CI。[測試分類](docs/audit/TEST-AUDIT.md)分清Java真值、正式交易守恆／回滾、真引擎保存與建置前置；[還原度表](docs/PARITY-MATRIX.md)與[問題場景](docs/BUGS.md)維護實際狀態。

來源一致與引擎載入不能證明客戶端畫面、音效或整條玩法。機器數量、支援的可堆疊原料 metadata、RGB 原作 texel 明暗、板面描邊與光效所有權已有修補，實際材質仍待真人。純相機 roll、彩字逐觀看者 16 格腳位／相機判定與第一人稱望遠鏡、任意 NBT／三份任意裝飾非堆疊原料、穿牆輪廓、原生多行板面 editor、掉落展示及部分原生效果仍有差距；現有 yaw 適配須明確 opt-in。雙手、動畫、視角、輸入及材質需真人核對，既有 LIVE 開發授權不變。

## 授權與歷史

酒館原作程式BSD-3-Clause、美術CC BY-NC-SA4.0，字型及其他素材各保留自己的聲明。見[CREDITS.md](CREDITS.md)、LICENSE-CODE、LICENSE-ASSETS。舊安装／下载说明移到[歷史封存](docs/archive/pre-reorganization-README.zh-TW.md)。bridge編輯開啟根config.json；見[工作流程](docs/BRIDGE-WORKFLOW.md)。
