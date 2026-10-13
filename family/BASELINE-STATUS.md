# 家族現行基線與差距

**[private deployment time]**：managed-server **T154／G132／W131／private-integration／Ribbits1.0.10037**，42包，BDS1.26.52.3 RUNNING。Canonical PR／必要CI、static、一次停服存檔副本first／restart、完整准入及逐檔／順序讀回通過。`client=false`、`production_ready=false`、`pending_client_acceptance`。

[本次Ribbits修補與證據](RIBBITS-FP-DECODE-LIVE-20261013.md)。六個公開自有BP／RP共9346檔與前次已匿名核對的輸出逐檔相等，本次完整LIVE讀回亦通過；沿用[15:03:22公開下載證據](PUBLIC-DOWNLOAD-LIVE-TRANSPORT-CPU-20261013.md)，本輪没有重新下載或發行T／G／W。

## 本輪修補與界限

Ribbits1.0.10037只替換FP存檔載入的一處同步Base64解壓呼叫，六位元緩衝解碼保留原UTF16字典結果；異常／非標準輸入交回原方法。保存格式、序列化、property keys、回呼、既有connection修補及其餘資產保留；配對manifest由canonical compiler生成。T154／G132／W131及reviewed integration輸出不變。

本次poststart **172 warnings／0 errors**；watchdog **145（8 Spike／137 Slowdown／0 High Memory）**，其中Ribbits啟動Spike **253ms**。存檔first／restart的Ribbits為261／267ms。這些是不同啟動窗口的觀察，不作整體效能百分比或完整watchdog驗收。

真人食用／取消／快開、調酒、AMW29通道、飽和度／普通提示及UI profile／scale仍待[回歸](../docs/HUD-COMPAT-CLIENT-HANDOFF-20261012.md)。任意第三方whole HUD／title與完整Java一比一未保證。

## 來源與當次證據

私有canonical [PR21](https://github.com/casama233/senluo-family-integration-private/pull/21)及CI38364423686已完成，merge `be7cf5287be8d6982052e409de6f9efc28d5cc0c`；准入工具[PR351](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/351)與CI38364584448通過，merge `831c9dfa`。來源CI核對UTF16全域、原作者roundtrip與異常輸入；必要baseline成功，私有付費pre-commit不可用沒有冒充通過。T154功能來源PR348、G132 PR199、W131 PR115保持。

紀錄 `private-operation-record`；reviewed SHA `0181b52f8fd0f948502517c664a633ee62914064163de3a0dffe852d2c9d1938`，raw SHA `36f86ac26f9394010a2d9618dcd7a13e06c351a510f494cc0697a3e733a0cd61`。政策installed／deferred_client_acceptance綁同reviewed SHA。玩家記錄（數量未公開）及容器（數量未公開）保留；冰櫃樣本（數量未公開），不當非空投料驗收。首次錯誤CI引用設定在停服前被拒，原失敗紀錄保留；修正設定後使用同一不可變包內容，未改寫失敗或原收據。

## 作者與維護

本輪讀取的BSM Java唯讀查核時間為 **2026-10-13 12:23:03 HKT**；`all_reference_release_metadata_current=false`、`full_java_parity_verified=false`仍保持，不能標成全分支最新或完整一比一。

依[java-upstream.json](java-upstream.json)分開追蹤Tavern1.2.0（Forge1.20.1／Neo1.21.1）、Grilling1.1.1兩分支、World Liquor Forge1.1.12／Neo1.21.1的1.1.11；未發布T26來源與W26／1.1.6仍另列。W共享obsidian1000／1800→1、milk識別與高度已承接，magma3僅legacy；customLuck／BlockDrops／註冊等26差異仍待適配，見[原審查與重估](world-liquor-26.1.2-1.1.6-review.json)。

本次部署的Bedrock作者鎖為Cookery1.6.0、ChineseFood1.0.4、ImmersiveEating1.1.0、Nether1.0.1、End1.0.1；國味1.0.10432及renderer32由reviewed integration原樣保留。AMW2.6.28、JavaSaturation1.5.5及UIQueue1.6.10034為登記HUD相容變體，並非宣稱作者正式新版。[沉浸進食適配](IMMERSIVE-EATING-110-ADAPTATION.md)。

[private deployment time]查到Cookery1.6.1（CF9123386）、ChineseFood1.0.5（CF9123382）、Nether1.0.2（CF9123379）、End1.0.2（CF9123371）；10/12已取得四份官方原包並驗SHA1／MD5，八個BP／RP UUID均更新；Script API仍2.7.0／UI2.0.0，但Cookery新增湯底API／修locale與26個blockstate schema，宿主掛鉤多处preimage失效。仍待資料所有權／blockstate與API適配，尚未安裝或改鎖。已部署版本與作者最新查核分開記錄，不能標成全數最新。

依使用者[private deployment time]要求，開發部署改為一次停服備份、一次保存世界first／restart及正常部署讀回；清理僅保留最新完整可回退備份，尚在使用或失敗／不完整的現場保留。原CI失敗、舊收據、歷史發版與獨立觀察保持原身份。詳[MAINTENANCE.md](MAINTENANCE.md)及[UPDATE-WORKFLOW.md](UPDATE-WORKFLOW.md)。文件整理不改runtime、包身份或重啟LIVE。
