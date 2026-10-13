# 家族現行基線與差距

**[private deployment time]**：managed-server **T153／G132／W130／private-integration／Ribbits1.0.10036**，42包（22BP／20RP），BDS1.26.52.3 RUNNING。Canonical PR／必要CI、static、一次停服存檔副本first／restart、完整准入及逐檔／順序讀回通過。`client=false`、`production_ready=false`、`pending_client_acceptance`。

[本次公開核對](PUBLIC-DOWNLOAD-LIVE-JAVA-STARTUP-20261013.md)於11:52:05 HKT確認三個新匿名下載的archive、六自有BP／RP共9346檔與LIVE及reviewed receipt相同。 [T152歷史核對](PUBLIC-DOWNLOAD-LIVE-TRANSPORT-20261013.md)及其他原收據保持原身份。

## 本輪修補與界限

T153保留世界名酒註冊完成前滿且關蓋的未成批酒桶，避免先按未匹配配方開始釀醋；既有批次與酒館配方優先順序保持。字型資料改為等值JSON解析，指南重用不可變配方連結。G132移除啟動時未使用的診斷資料，先保存進度獎勵領取狀態再發XP，避免保存失敗／不確定回應造成重領；不確定結果仍可能保留待處理且尚未發放的獎勵，不能宣稱原子性的恰好一次發放。W130移除兩套啟動正弦表及縮減重生碰撞資料，原Java量化數值與查詢結果保全。

Poststart **197 warnings／0 errors**，其中 **170 watchdog（8 Spike／162 Slowdown／0 High Memory）**。初始化Spike仍有AMW328、Cookery313、Nether112、Ribbits425、Villager155、W124、T231、G316ms。First356／restart404 warnings，各exit0／errors0；保留LIVE100／10ms門檻。這些是當次觀測窗口，不能作全局效能百分比或宣稱watchdog已解決。

真人食用／取消／快開、調酒、AMW29通道、飽和度／普通提示及UI profile／scale仍待[回歸](../docs/HUD-COMPAT-CLIENT-HANDOFF-20261012.md)。任意第三方whole HUD／title與完整Java一比一未保證。

## 來源與當次證據

T[PR346](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/346)、G[PR199](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/199)、W[PR114](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/pull/114)及必要CI已完成並合併；實際來源、CI及發布commit見[公開核對](PUBLIC-DOWNLOAD-LIVE-JAVA-STARTUP-20261013.md)。private-integration／Ribbits10036內容及原source CI範圍保持，未將不可用的付費pre-commit寫成成功。

紀錄 `private-operation-record`；reviewed SHA `4af54b4cdbf7009e99bf802712f2f09b78790952c97144c0a345f867a8607244`，raw SHA `475217a0219d9e55f275a00101c42909def8822830a004ddd9503735895f0f04`。政策installed／deferred_client_acceptance綁同reviewed SHA。玩家記錄（數量未公開）及容器（數量未公開）保留，冰櫃樣本（數量未公開）不當非空投料證據；未另建新世界或使用模擬玩家。只保留最新完整回退，清理6個舊生成根，磁碟可用空間實際增加1,607,970,816 bytes。來源、失敗JSON／日誌及活動工作保留。

## 作者與維護

本輪讀取的BSM Java唯讀查核時間為 **2026-10-13 06:23:03 HKT**；`all_reference_release_metadata_current=false`、`full_java_parity_verified=false`仍保持，不能標成全分支最新或完整一比一。

依[java-upstream.json](java-upstream.json)分開追蹤Tavern1.2.0（Forge1.20.1／Neo1.21.1）、Grilling1.1.1兩分支、World Liquor Forge1.1.12／Neo1.21.1的1.1.11；未發布T26來源與W26／1.1.6仍另列。W共享obsidian1000／1800→1、milk識別與高度已承接，magma3僅legacy；customLuck／BlockDrops／註冊等26差異仍待適配，見[原審查與重估](world-liquor-26.1.2-1.1.6-review.json)。

本次部署的Bedrock作者鎖為Cookery1.6.0、ChineseFood1.0.4、ImmersiveEating1.1.0、Nether1.0.1、End1.0.1；國味1.0.10432及renderer32由reviewed integration原樣保留。AMW2.6.28、JavaSaturation1.5.5及UIQueue1.6.10034為登記HUD相容變體，並非宣稱作者正式新版。[沉浸進食適配](IMMERSIVE-EATING-110-ADAPTATION.md)。

[private deployment time]查到Cookery1.6.1（CF9123386）、ChineseFood1.0.5（CF9123382）、Nether1.0.2（CF9123379）、End1.0.2（CF9123371）；10/12已取得四份官方原包並驗SHA1／MD5，八個BP／RP UUID均更新；Script API仍2.7.0／UI2.0.0，但Cookery新增湯底API／修locale與26個blockstate schema，宿主掛鉤多处preimage失效。仍待資料所有權／blockstate與API適配，尚未安裝或改鎖。已部署版本與作者最新查核分開記錄，不能標成全數最新。

依使用者[private deployment time]要求，開發部署改為一次停服備份、一次保存世界first／restart及正常部署讀回；清理僅保留最新完整可回退備份，尚在使用或失敗／不完整的現場保留。原CI失敗、舊收據、歷史發版與獨立觀察保持原身份。詳[MAINTENANCE.md](MAINTENANCE.md)及[UPDATE-WORKFLOW.md](UPDATE-WORKFLOW.md)。文件整理不改runtime、包身份或重啟LIVE。
