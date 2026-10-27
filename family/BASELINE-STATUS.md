# 家族現行基線與修復主線

更新：**2026-10-27，香港時間**。本頁維護家族流程與證據入口。當前來源查各庫 baseline，完整家族選取查家族鎖；公開下載、准入、實際部署與真人驗收各查自己的原始記錄。本頁不另維護版本、部署狀態或檔案數量表。

## 1. 來源、公開下載與家族准入

- **來源與相依：** Tavern 的身份由 [baseline.json](../baseline.json)持有，完整家族選取由 [upstream.lock.json 的 owned／upstream／order](upstream.lock.json)持有；Grilling 與 World Liquor 各自的 [baseline](https://github.com/burnt-tea-dev/kaleidoscope-grilling-unofficial/blob/main/baseline.json)／[baseline](https://github.com/burnt-tea-dev/kaleidoscope-world-liquor-unofficial/blob/main/baseline.json)是其 runtime 身份來源。精確測試 peer commit 由各庫 CI 的來源 pin 選取，不把工具提交等同於新的遊戲包。
- **公開下載：** 實際已公開版本、下載、archive 身份及安裝邊界只在各庫 [Tavern README](../README.md#current-maintained-source)、[Grilling README](https://github.com/burnt-tea-dev/kaleidoscope-grilling-unofficial/blob/main/README.md)、[World Liquor README](https://github.com/burnt-tea-dev/kaleidoscope-world-liquor-unofficial/blob/main/README.md)維護，這裡不複製另一份下載表。發布請求的 `publication_request=false` 是該來源的請求設定；是否已發布要看實際 release，不能只看這個欄位或 workflow 綠勾。
- **完整家族：** LIVE 的實際版本與階段由宿主維護入口、政策及該次部署收據持有；公開單包發布的範圍見 [Tavern README](../README.md#current-maintained-source)。每次新的功能候選仍須同一候選的 static、正常停服一致備份、同一存檔副本 first／restart、准入、安裝及部署後讀回。一般更新沿用現行存檔；新世界初始化必須有該次明確設定與授權，不能與保存遷移互相代替。
- **作者適配：** 已合併的私有作者適配與來源證據保留在私有維護入口；實際作者版本、UUID、archive 與順序由家族鎖持有。不能只提高 manifest 相依版本就宣稱適配完成，也不公開作者完整 scripts 或私有收據。
- **`client=false`、`production_ready=false`、`pending_client_acceptance` 保持。** BDS、來源及保存檢查不證明畫面、聲音或真人玩法；純工具／文件修正不升包或重啟 LIVE。

### 部署紀錄的邊界

公開索引曾記錄於 **2026-10-15 22:40:27 HKT** 部署的 T169／G144／W147／private-integration、42包及其原收據；紀錄保留在[原始快照](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/blob/115942e55e9946cfd257fbcdc41c849f75b77509/family/BASELINE-STATUS.md)。它不是本次的 LIVE 讀回，也不能用來認定伺服器目前仍是那個版本。接續部署應核對私有入口最新原始收據與實際檔案／順序，不能從本頁、main 或 release 版本反推。

## 2. 現行修復線

下表的 **P0／P1／P2只表示修復優先次序**，不是 Grilling 重建計畫的階段。Grilling 的當前階段與出口條件以原 [REBUILD-PLAN](https://github.com/burnt-tea-dev/kaleidoscope-grilling-unofficial/blob/main/docs/REBUILD-PLAN.md)為準；本頁不再把 2026-10-26 的分支整合狀態當成現況。T1.8 的 **OWNER WAIVED 不是 PASS**，並行 T4 診斷也不是新增的 P3 前置條件。

| 工作線 | 已有來源結果 | 仍需閉合 |
| --- | --- | --- |
| **P0：家族來源及作者契約** | 三庫來源及作者適配已有 canonical 來源；當前選取查[家族鎖](upstream.lock.json)，來源證據保留各自原始範圍 | 依該候選原始收據核對 static、保存演練、准入、部署與讀回；真人另驗 |
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

2026-10-26 的 T184 item 定義數是歷史快照，不能作當前完成度分母；source mapping、方塊物品、動態內容、別名與各視圖也不是同一集合。每列至少記 item ID、版本／SHA、Java 原資產、Bedrock 路由、視圖／動作、編輯器結果、遊戲結果及修補入口。舊 T／G／W 局部檢查保留原範圍，不改成當前全量 PASS。

性能已有來源層改善：[T168空snapshot](../docs/evidence/performance-20261015.md)在100 idle ticks由11包減至1包；[T181相同失敗櫃子查詢](../docs/FOUNDATION-PHASE1.md)在60次callback由30次減至2次。這些不是現服TPS、FPS或操作延遲。完整家族應在相同存檔、玩家數、設備及操作負載比較tick／script時間、watchdog、記憶體與輸入延遲，不能把不同負載的CPU差異歸因於修補。

[驗收證據工具](../docs/ACCEPTANCE-EVIDENCE.md)是offline preflight，沒有接入每個release／deployment入口。既有穩定通道發布授權保持；發布、部署與真人接受各自依證據判斷。

## 4. 接續及文件責任

1. 依當前 canonical baseline、家族鎖與原始來源證據固定同一候選，保留並行修補。原 T184／W162 配對及 W163 候選的處置只適用其歷史觀察時點，不再作為當前選版指示。
2. 模組自有功能可平行處理；共同HUD、展示generator、family lock與保存流程指定單一整合者。同一行為只有一個責任入口，不整支套用舊工作樹。
3. 已修來源但缺真人結果的項目標「待驗收」，不重新宣稱舊bug仍重現。純工具／文件修正不升包、不建立runtime候選、不重啟LIVE。
4. 發布請求只維護發布身份；version、tag與title由既有 `release_publication.py`共同檢查，publication關閉時也必須一致。Family版本／runtime雜湊由既有lock負責，精確peer checkout由既有CI來源檢查負責。
5. 本頁管現況與次序；各庫PARITY-MATRIX管行為差距，BUGS管回報，Issue管未閉合工作，release notes／evidence保存原版本結果。新場景結果更新原入口，不再增加平行現況報告。

### 歷史來源與原證據

- [2026-10-26 T184／G157／W162 摘錄](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/blob/f26daa8eb631eef1fe40c94ad2bb17d36656ee94/family/BASELINE-STATUS.md)：保留原 PR149／T184 CI、當時跳過發布的結果與接續判斷；只適用原觀察時點，不是今天的來源或下載狀態。
- [收斂前完整索引（79ac1fb8）](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/blob/79ac1fb82e06ddd07993cf7b9140dfbf1cfd09fc/family/BASELINE-STATUS.md)：10/24 T179、10/19 T177、10/17 T175／T173等各時點來源、候選、失敗、部署與PR處置。
- [較早完整索引（115942e5）](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/blob/115942e55e9946cfd257fbcdc41c849f75b77509/family/BASELINE-STATUS.md)：T166／T167／T169等原部署、收據及上游查核時間。
- [歷史PR處置](../docs/audit/PR-DISPOSITIONS.md)、[工具依賴盤點](TOOLS-INVENTORY.md)：先核對已吸收差異與仍在使用的責任，再退役舊入口；不能直接以「保留六個核心」刪除仍可達的相依模組。

歷史頁的「當前／未合併／已部署」只指原紀錄時點；本次不改寫原成功、失敗或授權，也不把舊證據移到新候選。
