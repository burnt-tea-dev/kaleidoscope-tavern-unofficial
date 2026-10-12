## 當前維護基線：0.6.150

T150在建置時產生legacy指南21個product投影，原28個page保全；native字串quote有界處理，W127配對T150与同SDK，G130保持。Ribbits1.0.10036登記structure適配保留來源connection及保守fallback。來源回歸与引擎／真人接受分開；[T150原说明](docs/RELEASE-NOTES-0.6.150.md)保留當時範圍。

**[private deployment time]** 已部署managed-server **T150／G130／W127／private-integration／Ribbits1.0.10036**，42包、BDS1.26.52.3 RUNNING。Canonical PR／CI、static、停服存檔first／restart、准入及逐檔／順序讀回通過。Poststart **257 warnings／0 errors**，其中 **230 watchdog（9 Spike、220 Slowdown、1 High Memory）**；啟動仍未全解決，不當效能驗收。

[下載v0.6.150-beta.1](https://github.com/casama233/kaleidoscope-tavern-unofficial/releases/tag/v0.6.150-beta.1)或[完整酒館BP／RP](https://github.com/casama233/kaleidoscope-tavern-unofficial/releases/download/v0.6.150-beta.1/Kaleidoscope_Tavern_Unofficial_0.6.150_baseline1.mcaddon)。[公開下載与LIVE核對](family/PUBLIC-DOWNLOAD-LIVE-STARTUP-20261013.md)確認六自有包 **9344檔** 完全相同；G130沿用原release，私有料理／Ribbits／其他host變體另有canonical來源。

reviewed integration及五份HUD變體內容不變；本輪native保留LIVE明確100／10ms門檻，舊R149 native未設而關閉對應告警，不能与不同窗口作百分比或全局效能比較。快開短空條、聲畫／操作及任意whole-HUD／title仍待[真人回歸](docs/HUD-COMPAT-CLIENT-HANDOFF-20261012.md)；`client=false`、`production_ready=false`、`pending_client_acceptance`。

## 歷史修補範圍：0.6.147

[T149核對](family/PUBLIC-DOWNLOAD-LIVE-HUD-20261013.md)保留原收據、窗口及native門檻限制。

[T148／G129／W125核對](family/PUBLIC-DOWNLOAD-LIVE-UI-20261012.md)保留原9339檔收據與驗收範圍；舊影片不挪作T149／G130驗收。

T147的有界HUD200修補已由[PR331](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/331)合併。雪克杯進度顯示100ms改為200ms，游標一tick移動維持50ms。T147／G128／W124家族已於2026-10-12通過static、一次停服存檔首次載入／重啟、完整准入與讀回後部署managed-server；真人驗收仍待完成。

[下載v0.6.147-beta.1](https://github.com/casama233/kaleidoscope-tavern-unofficial/releases/tag/v0.6.147-beta.1)或[完整酒館BP／RP](https://github.com/casama233/kaleidoscope-tavern-unofficial/releases/download/v0.6.147-beta.1/Kaleidoscope_Tavern_Unofficial_0.6.147_baseline1.mcaddon)。[公開下載與LIVE核對](family/PUBLIC-DOWNLOAD-LIVE-20261012.md)記錄實際archive與安裝內容；原[發版準備頁](docs/PUBLICATION-T147-G128-W124.md)保留當時狀態與公開Cookery API組裝說明。

HUD200有限診斷錄影支持連續可見改善，也保留末端停住觀察；實體輸入／封包時序及新正式家族完整驗收尚未證實。[原始診斷範圍](docs/RELEASE-NOTES-0.6.147.md)保持原文與證據身份。

T146在canonical T145上整合板面逆轉換、before-event安全原料快照與雪克杯100ms進度顯示。T146／W123／G125已於2026-10-11通過完整家族准入及一次新鮮存檔的首次啟動／保存／重啟後部署，真人驗收仍待完成。先前五段獨立HUD錄影保留已測範圍；按住換槽不確定，同秒快速重開尚未測。見[範圍與驗證](docs/RELEASE-NOTES-0.6.146.md)。

實際部署版本、主線來源、CI、原生與存檔證據統一見[當前基線](family/BASELINE-STATUS.md)。真人驗收仍待完成；release notes保留當時草稿審閱與證據身份，現況以此基線入口為準。

T144 修復真人回報的四個重複板面輸入框與板外文字（[private deployment time] 已部署），輸入、焦點與實際文字位置仍需真人確認。T145 在原生 use 事件副本未帶雪克杯動態屬性時，改以實際手持物品辨識；見[修補範圍](docs/RELEASE-NOTES-0.6.145.md)。實機搖晃仍需真人確認。

# 森羅物語：酒館（非官方）

[T140 指南修訂](docs/RELEASE-NOTES-0.6.140.md)保留三語完整製作方法，補齊 Kirsch、Kriek、酸櫻桃和酸櫻桃汁桶；獨立書與可選 Cookery 入口共用顯示。T141 承接該已發布指南與 T139 的原料、光效、倒轉 Mob、沉浸修補，新候選仍另做配套驗證。

T132 統一濺射瞬時效果與來源免疫，修復雪克杯回呼誤操作／失敗重試及保存回滾、感知類別和查詢順序，補上指南逐格動畫、板面反斜線保存及較短 HUD 尾巴；[變更及驗收範圍](docs/RELEASE-NOTES-0.6.132.md)。[PR 處置索引](docs/audit/PR-DISPOSITIONS.md) 保留尚未完成的工作及先前證據。

Java酒館的基岩版移植，包含釀造、調酒、酒架／酒櫃、家具與獨立酒館指南。指南保留共用七入口；Cookery整合使用同一份內容。[English](README.md)。

## 現行來源與需求

- 版本及精確相依以 [baseline.json](baseline.json) 為準；更新見 [CHANGELOG.md](CHANGELOG.md)。
- 目前已部署開發家族為酒館 **0.6.150**、世界名酒 **0.1.127**、燒烤 **2.8.130**、私有整合 **1.0.34**；精確相依、來源與有界驗證見[家族鎖](family/upstream.lock.json)和[當前 baseline](family/BASELINE-STATUS.md)。
- 基岩版1.26.50以上；目前引擎目標為BDS1.26.52.3。BP與RP兩側一起啟用。
- Cookery可選，家族目前核驗作者1.6.0；世界名酒須搭配其宣告的酒館版本。
- 升級前備份世界並移除重複舊包。私有料理整合是另一個識別明確的addon，不是私有酒館分支。

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

酒館原作程式BSD-3-Clause、美術CC BY-NC-SA4.0，字型及其他素材各保留自己的聲明。見[CREDITS.md](CREDITS.md)、LICENSE-CODE、LICENSE-ASSETS。旧安装／下载说明移到[歷史封存](docs/archive/pre-reorganization-README.zh-TW.md)。bridge編輯開啟根config.json；見[工作流程](docs/BRIDGE-WORKFLOW.md)。
