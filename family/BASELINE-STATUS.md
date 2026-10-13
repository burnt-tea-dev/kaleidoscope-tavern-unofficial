# 家族現行基線與差距

**[private deployment time]**：managed-server **T154／G132／W131／private-integration／Ribbits1.0.10036**，42包，BDS1.26.52.3 RUNNING。Canonical PR／必要CI、static、一次停服存檔副本first／restart、完整准入及逐檔／順序讀回通過。`client=false`、`production_ready=false`、`pending_client_acceptance`。

[本次公開核對](PUBLIC-DOWNLOAD-LIVE-TRANSPORT-CPU-20261013.md)：2026-10-13 15:03:22 HKT，T154／W131本次匿名下載；G132沿用前次已匿名核對的不可變archive並以同檔案系統hardlink重用，沒有重新下載。三個release metadata／digest均已重新核對；六自有BP／RP共9346檔與archive／LIVE／reviewed receipt完全相同。 [T153歷史核對](PUBLIC-DOWNLOAD-LIVE-JAVA-STARTUP-20261013.md)及其他原收據保持原身份。

## 本輪修補與界限

T154／W131讓foundation接收器先篩選三個支援事件ID，無關封包在讀取message、計算UTF-8長度與JSON解析前退出。UTF-8計數直接讀取UTF-16，避免逐codepoint建立字串；配對／孤立surrogate與非字串iterable fallback保持原值。支援通道的驗證、封包、ACK、排程與保存保持；G132、private-integration及Ribbits10036沒有內容更新。

本次poststart **208 warnings／0 errors**；watchdog **181（8 Spike／173 Slowdown／0 High Memory）**。這是本候選的觀測窗口，不作整體效能百分比或完整watchdog驗收。原profile只捕捉啟動後傳輸工作，未捕捉首次初始化尖峰。

真人食用／取消／快開、調酒、AMW29通道、飽和度／普通提示及UI profile／scale仍待[回歸](../docs/HUD-COMPAT-CLIENT-HANDOFF-20261012.md)。任意第三方whole HUD／title與完整Java一比一未保證。

## 來源與當次證據

T[PR348](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/348)、W[PR115](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/pull/115)及必要CI已完成並合併；G132沿用[PR199](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/199)。實際來源、CI及發布commit見[公開核對](PUBLIC-DOWNLOAD-LIVE-TRANSPORT-CPU-20261013.md)。private-integration／Ribbits10036內容及原source CI範圍保持，未將不可用的付費pre-commit寫成成功。

紀錄 `private-operation-record`；reviewed SHA `9df9645c0ca8d87ea4f9685196b6af11652adaace6242ee150713f4c085fbdbe`，raw SHA `71f1746a31a738199a7313eefb644eb272320d633c8f232bab9cd737e97468c5`。政策installed／deferred_client_acceptance綁同reviewed SHA。玩家記錄（數量未公開）及容器（數量未公開）保留，冰櫃樣本（數量未公開）；此投料樣本不當非空保存驗收。只保留最新完整回退；本次清理6個舊生成根，磁碟可用空間實際增加1,604,538,368 bytes。來源、失敗JSON／日誌及活動工作保留。

## 作者與維護

本輪讀取的BSM Java唯讀查核時間為 **2026-10-13 12:23:03 HKT**；`all_reference_release_metadata_current=false`、`full_java_parity_verified=false`仍保持，不能標成全分支最新或完整一比一。

依[java-upstream.json](java-upstream.json)分開追蹤Tavern1.2.0（Forge1.20.1／Neo1.21.1）、Grilling1.1.1兩分支、World Liquor Forge1.1.12／Neo1.21.1的1.1.11；未發布T26來源與W26／1.1.6仍另列。W共享obsidian1000／1800→1、milk識別與高度已承接，magma3僅legacy；customLuck／BlockDrops／註冊等26差異仍待適配，見[原審查與重估](world-liquor-26.1.2-1.1.6-review.json)。

本次部署的Bedrock作者鎖為Cookery1.6.0、ChineseFood1.0.4、ImmersiveEating1.1.0、Nether1.0.1、End1.0.1；國味1.0.10432及renderer32由reviewed integration原樣保留。AMW2.6.28、JavaSaturation1.5.5及UIQueue1.6.10034為登記HUD相容變體，並非宣稱作者正式新版。[沉浸進食適配](IMMERSIVE-EATING-110-ADAPTATION.md)。

[private deployment time]查到Cookery1.6.1（CF9123386）、ChineseFood1.0.5（CF9123382）、Nether1.0.2（CF9123379）、End1.0.2（CF9123371）；10/12已取得四份官方原包並驗SHA1／MD5，八個BP／RP UUID均更新；Script API仍2.7.0／UI2.0.0，但Cookery新增湯底API／修locale與26個blockstate schema，宿主掛鉤多处preimage失效。仍待資料所有權／blockstate與API適配，尚未安裝或改鎖。已部署版本與作者最新查核分開記錄，不能標成全數最新。

依使用者[private deployment time]要求，開發部署改為一次停服備份、一次保存世界first／restart及正常部署讀回；清理僅保留最新完整可回退備份，尚在使用或失敗／不完整的現場保留。原CI失敗、舊收據、歷史發版與獨立觀察保持原身份。詳[MAINTENANCE.md](MAINTENANCE.md)及[UPDATE-WORKFLOW.md](UPDATE-WORKFLOW.md)。文件整理不改runtime、包身份或重啟LIVE。
