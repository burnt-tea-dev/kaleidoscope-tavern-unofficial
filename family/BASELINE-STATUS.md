# 家族現行基線與修復主線

更新：**2026-10-26，香港時間**。本頁只保留一份現況摘要。修復收斂到 **T184／G157／W162／Cookery 1.6.4**；公開來源配對、完整家族准入、發布、部署與真人驗收分開記錄。核對起點為 Tavern [79ac1fb8](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/commit/79ac1fb82e06ddd07993cf7b9140dfbf1cfd09fc)，不是新的部署收據。

## 1. 來源、公開下載與家族准入

| 模組 | 本輪維護來源 | 公開下載 |
| --- | --- | --- |
| Tavern | **0.6.184**；[baseline](../baseline.json)、[BP manifest](../runtime/BP/manifest.json) | [v0.6.170](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/releases/tag/v0.6.170) |
| Grilling | **2.8.157**；完整 BP／RP 雜湊由[家族鎖](upstream.lock.json)選取 | [A2.8.149](https://github.com/burnt-tea-dev/kaleidoscope-grilling-unofficial/releases/tag/A2.8.149) |
| World Liquor | **0.1.162**；完整 BP／RP 雜湊由[家族鎖](upstream.lock.json)選取 | [v0.1.148](https://github.com/burnt-tea-dev/kaleidoscope-world-liquor-unofficial/releases/tag/v0.1.148) |

- **公開來源配對不等於完整家族可部署。** W162 的最終 T／G 來源 pin 已由 [PR149](https://github.com/burnt-tea-dev/kaleidoscope-world-liquor-unofficial/pull/149)固定至 canonical T184（`79ac1fb82e06ddd07993cf7b9140dfbf1cfd09fc`）／G157（`2e3ef63839e38f84b4a0109957077ac00a140697`），[四項 canonical CI](https://github.com/burnt-tea-dev/kaleidoscope-world-liquor-unofficial/actions/runs/40269373713)通過後合併為 `f207d4142ad24c5c582248ea0f8916ce67d207c1`。精確 peer commit 由各庫 CI checkout 與來源檢查選取，不再由發布請求的重複說明欄位維護第二份。
- **目前作者相依是 Cookery 1.6.4。** 私有 host-extension 的作者來源、UUID、API及保存契約仍須重新核對；只提高私有 manifest 的 T／W 版本不能證明已適配新作者包。私有實作、作者來源與原始收據保留在私有維護入口。
- 完整家族仍欠同一候選的作者契約整合、static、native、同一份停服存檔 first／restart、准入及部署後讀回。新世界初始化與既有世界遷移分別記錄，不能互相代替。
- T184 合併來源的 [Canonical validation 40227655798](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/actions/runs/40227655798) 13 個 jobs 通過；[native-persistence](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/actions/runs/40227655798/job/121272551139)驗證並重用相同執行輸入的原始 native 證據，沒有重新執行整套新世界或 LIVE 驗收。
- [發布請求](../.github/release-request.json)保持 `publication_request=false`；[Publish run 40227655780](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/actions/runs/40227655780)的 request 通過、publish 跳過。Workflow 整體綠勾不能證明已發布 T184。
- **`client=false`、`production_ready=false`、`pending_client_acceptance` 保持。** 純來源、工具或文件修正不新增真人通過結果，也不啟動 LIVE。

### 部署紀錄的邊界

公開索引曾記錄於 **2026-10-15 22:40:27 HKT** 部署的 T169／G144／W147／private-integration、42包及其原收據；紀錄保留在[原始快照](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/blob/115942e55e9946cfd257fbcdc41c849f75b77509/family/BASELINE-STATUS.md)。它不是本次的 LIVE 讀回，也不能用來認定伺服器目前仍是那個版本。接續部署應核對私有入口最新原始收據與實際檔案／順序，不能從本頁、main 或 release 版本反推。

## 2. 現行修復線

下表的 **P0／P1／P2只表示修復優先次序**，不是Grilling重建計畫的階段。Grilling仍在原[重建計畫P2](https://github.com/burnt-tea-dev/kaleidoscope-grilling-unofficial/blob/main/docs/REBUILD-PLAN.md)：[#255的T2.8](https://github.com/burnt-tea-dev/kaleidoscope-grilling-unofficial/pull/255)正在整合最新main，逐ID／可達表面引用、完整家族乾淨相容及同存檔正常重啟抽查等原出口條件未全閉合前不開始P3；T1.8的 **OWNER WAIVED不是PASS**，並行T4診斷也不是新增的P3前置條件。

| 工作線 | 已有來源結果 | 仍需閉合 |
| --- | --- | --- |
| **P0：家族來源及作者契約** | T184／G157／W162 runtime已選定；[PR428](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/pull/428)補現行附屬註冊及fresh-world工具；W162最終配對已通過PR149的CI並合併 | 重新核對私有host-extension的新作者來源，再完成相同候選的保存／准入／讀回 |
| **P1：雪克杯及HUD** | clone／abort／metadata、T165位置、T166快取、T167插值、T169尾幀窗口保留 | 同候選投料→搖晃→取消／換槽→重開→成功取出→放置／取回／重登；同步驗聲音、尾幀與延遲。跨維度／長title由 [#285](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/issues/285)承接 |
| **P1：穿串、調料瓶與餐盤** | 目前實作及交易差距由 [Grilling矩陣](https://github.com/burnt-tea-dev/kaleidoscope-grilling-unofficial/blob/main/docs/PARITY-MATRIX.md)持有 | 取得原料→配方／秘製串→烤製→同瓶三料及搖勻→撒料→取出／吃完或取消→保存重載。調料瓶runtime owner是Grilling [#168](https://github.com/burnt-tea-dev/kaleidoscope-grilling-unofficial/issues/168)，不另開酒館平行線 |
| **P1：全部物品顯示／動作** | [T174](../docs/RELEASE-NOTES-0.6.174.md)動態側面／UV與XP瓶材質、[T175](../docs/RELEASE-NOTES-0.6.175.md)已批准的傾斜酒架FP調整保留；有有限Blockbench結果 | [#288](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/issues/288)：逐ID核對材質／路由、第一第三人稱、主副手、動作與必要contexts。代表模型或舊畫面不關閉全量工作 |
| **P1：櫃架、瓶身與保存** | T179普通冰半透明及效果時計、T180原生藥水液體色、T181有界重試、T183朝向／重複讀取修補保留 | 四向真實點選／存取、原生資料保存、卸載／重載及實際光照／透明；來源反例通過不證明正式世界已恢復 |
| **P2：指南、黑板與容器** | T182設定取消返回同一指南；單輸入框、字形與原生座標修補保留 | 觸控／手把焦點、完整多行editor、板面距離／spyglass、W容器餘物由原矩陣驗收 |
| **P2：純視覺微醺** | 預設不改瞄準；yaw只接受明確opt-in；T179已補首次在線效果時計 | [#286](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/issues/286)：保持準星與原生手臂的純roll仍未完成。時計與相機視覺分開記錄 |
| **P2：原生效果／材質** | 特調source texel×cupRGB與六幀、部分原生酒效dispatch保留 | RGB材質／PBR／全視圖由 [#287](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/issues/287)承接；reach、target clear、step、XP、outline由 [#98](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/issues/98)承接 |

夜光新娘使用 `kaleidoscope_tavern:bottle_luminous_bride`，由酒館瓶身／展示主線負責。[Blockbench原生匯出](../art/blockbench/luminous-bride/README.md)不是當前Minecraft畫面驗收。World Liquor自有杯體、冰紅茶、酒效及容器行為由[該庫矩陣](https://github.com/burnt-tea-dev/kaleidoscope-world-liquor-unofficial/blob/main/docs/PARITY-MATRIX.md)負責。

使用者既有選擇保持：高階廚具架直接取放且無UI；T175酒架FP位置是可用性適配；Tipsy只影響視覺；W Treasure Guide生物掉落的已知保留問題不因本次整理自動修復或刪除。Java各Minecraft／loader分支依[java-upstream.json](java-upstream.json)追蹤，未重新查核的時間不得改成今天。

## 3. 完成度與性能的記法

每項同時記錄交付位置與還原證據，**不用PR數、測試數、版本號或來源檔案數推算完成百分比**。

| 證據 | 可作的結論 |
| --- | --- |
| 當前source＋可分辨的行為案例 | 指定修補已實作，或仍有來源差距 |
| 精確merged commit＋所需CI | 來源已整合；native重用仍保留原執行範圍 |
| 實際release及archive身份 | 指定版本已公開發布；Stable是發布通道 |
| 同批完整receipt、保存演練及讀回 | 指定時刻完整家族已部署 |
| 逐ID／材質／視圖／狀態的Blockbench結果 | 指定編輯器觀察通過 |
| 同候選、裝置／輸入／畫面設定及正常完整流程 | 對應真人場景已接受 |

T184有255份BP item定義，但source mapping、方塊物品、動態內容、別名與各視圖不是同一分母。每列至少記item ID、版本／SHA、Java原資產、Bedrock路由、視圖／動作、編輯器結果、遊戲結果及修補入口。舊T／G／W局部檢查保留原範圍，不改成當前全量PASS。

性能已有來源層改善：[T168空snapshot](../docs/evidence/performance-20261015.md)在100 idle ticks由11包減至1包；[T181相同失敗櫃子查詢](../docs/FOUNDATION-PHASE1.md)在60次callback由30次減至2次。這些不是現服TPS、FPS或操作延遲。完整家族應在相同存檔、玩家數、設備及操作負載比較tick／script時間、watchdog、記憶體與輸入延遲，不能把不同負載的CPU差異歸因於修補。

[驗收證據工具](../docs/ACCEPTANCE-EVIDENCE.md)是offline preflight，沒有接入每個release／deployment入口。既有穩定通道發布授權保持；發布、部署與真人接受各自依證據判斷。

## 4. 接續及文件責任

1. 先固定同一條來源線並核對作者契約，保留並行修補。T185／W163等其他未整合候選不得僅因版本較新便取代本輪配對。
2. 模組自有功能可平行處理；共同HUD、展示generator、family lock與保存流程指定單一整合者。同一行為只有一個責任入口，不整支套用舊工作樹。
3. 已修來源但缺真人結果的項目標「待驗收」，不重新宣稱舊bug仍重現。純工具／文件修正不升包、不建立runtime候選、不重啟LIVE。
4. 發布請求只維護發布身份；version、tag與title由既有 `release_publication.py`共同檢查，publication關閉時也必須一致。Family版本／runtime雜湊由既有lock負責，精確peer checkout由既有CI來源檢查負責。
5. 本頁管現況與次序；各庫PARITY-MATRIX管行為差距，BUGS管回報，Issue管未閉合工作，release notes／evidence保存原版本結果。新場景結果更新原入口，不再增加平行現況報告。

### 歷史來源與原證據

- [收斂前完整索引（79ac1fb8）](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/blob/79ac1fb82e06ddd07993cf7b9140dfbf1cfd09fc/family/BASELINE-STATUS.md)：10/24 T179、10/19 T177、10/17 T175／T173等各時點來源、候選、失敗、部署與PR處置。
- [較早完整索引（115942e5）](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/blob/115942e55e9946cfd257fbcdc41c849f75b77509/family/BASELINE-STATUS.md)：T166／T167／T169等原部署、收據及上游查核時間。
- [歷史PR處置](../docs/audit/PR-DISPOSITIONS.md)、[工具依賴盤點](TOOLS-INVENTORY.md)：先核對已吸收差異與仍在使用的責任，再退役舊入口；不能直接以「保留六個核心」刪除仍可達的相依模組。

歷史頁的「當前／未合併／已部署」只指原紀錄時點；本次不改寫原成功、失敗或授權，也不把舊證據移到新候選。
