# 家族現行基線與差距

## 現行公開版本與倉庫記錄的部署（2026-10-15核對）

倉庫維護摘要記錄最後部署為 **2026-10-15 14:47:03 HKT（06:47:03 UTC）**：**T167／G143／W145／private-integration／Ribbits1.0.10037**。摘要記錄42包、0 errors／164 warnings，家族static、停服存檔副本first／restart、准入及精確逐檔／順序讀回通過；18份玩家紀錄與2個受檢容器保留。這是**倉庫回報的部署證據**，本次文件核對沒有直接檢查服務器、讀取世界或重新掃描LIVE。私有整合仍保持私有，不公開其內容或收據路徑。

| 現行公開版本 | 發布來源提交 | 已合併修復PR | 正式版／發布時間（UTC） |
| --- | --- | --- | --- |
| Tavern 0.6.167 | `7c34f8f33276927af73cd0748bc533d15b1ec849` | [PR373](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/373)；文件承接[PR374](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/374) | [v0.6.167](https://github.com/casama233/kaleidoscope-tavern-unofficial/releases/tag/v0.6.167)／2026-10-15 06:50:43 |
| Grilling 2.8.143 | `b66f9655ccdedbb78f0fa306973501299f3578a7` | [PR215](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/215) | [A2.8.143](https://github.com/casama233/kaleidoscope-grilling-unofficial/releases/tag/A2.8.143)／2026-10-15 06:51:38 |
| World Liquor 0.1.145 | `cc8ec7b202230185a62c2786affcf7acb85a5ebe` | [PR130](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/pull/130) | [v0.1.145](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/releases/tag/v0.1.145)／2026-10-15 06:50:25 |

三個正式版API均為 `draft=false`、`prerelease=false`。後續倉庫下載核對摘要記錄6個公開包／9352檔與同一reviewed receipt相符，綁定06:47:03的poststart讀回；`live_rescanned=false`，不能改稱發布後又直接掃描LIVE。本次只核對既有來源及發布記錄，沒有重新下載、驗包或部署。

T167承接Java整數游標插值及桶／壓榨盆液面動畫；G143承接attachable owning-entity讀取、副手時計、秘製串末段邊界及調料瓶rawLore窄修補；W145承接冰櫃液面動畫。來源修補、啟動／保存與公開包核對都不是真人畫面或完整玩法驗收：`client=false`、`production_ready=false`、`pending_client_acceptance`保持。後續尚未凍結的動畫候選不屬於這三個正式版，不把其結果回填到G143或舊fixtures。

## 前輪T166／G142／W144／private-integration歷史來源

以下保留前輪來源與原證據身份，不作現行版本或本輪成功證據。

**前輪部署：2026-10-14 21:41:21 HKT**，managed-server **T166／G142／W144／private-integration／Ribbits1.0.10037**，42包，BDS1.26.52.3正常啟動。來源PR／完整CI、家族static、一次停服存檔副本first／restart、准入及逐檔／順序讀回通過。`client=false`、`production_ready=false`、`pending_client_acceptance`。

| 已部署公開來源 | 提交 | 已合併修復PR／完整來源CI | 正式版 |
| --- | --- | --- | --- |
| Tavern 0.6.166 | `d2d7ef987ab9839643241e960b8ba941b8d0d240` | [PR369](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/369)／[38571836792](https://github.com/casama233/kaleidoscope-tavern-unofficial/actions/runs/38571836792) | [v0.6.166](https://github.com/casama233/kaleidoscope-tavern-unofficial/releases/tag/v0.6.166) |
| Grilling 2.8.142 | `3f63bb32890d67004352e66386d8eaf890daafea` | [PR209](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/209)／[38570580331](https://github.com/casama233/kaleidoscope-grilling-unofficial/actions/runs/38570580331)（含Windows匯出） | [A2.8.142](https://github.com/casama233/kaleidoscope-grilling-unofficial/releases/tag/A2.8.142) |
| World Liquor 0.1.144 | `b6ba608178a6dc944fe4b081bd3615bfddd8b0d6` | [PR127](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/pull/127)／[38570678514](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/actions/runs/38570678514) | [v0.1.144](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/releases/tag/v0.1.144) |

前輪private-integration已完成其PR27／來源CI，僅同步本次provider相依，沒有公開第三方私有內容。以上是前輪收據中的部署來源；之後只更新文件的Git提交不改寫本次部署來源或重啟LIVE。

T165恢復Java中央相對座標；G141按原生剩餘use ticks計算並立即發首幀；T166加入128筆上限的閒置預覽快取，T/G裁剪固定封包中未使用圖形。全部[客戶端回饋及修補狀態](../docs/BUGS.md)保留：圖形／資料碼失敗未改成成功，後續圖形可見也不代表位置、進食與延遲全部驗收。

## 修復線與接續順序（2026-10-15整理）

同一問題按行為接續，不按舊候選或工作樹數量另開修復線。下表是工作順序；具體差距仍維護在各庫原有矩陣，歷史收據與失敗不改標。本索引的已發布批次為上列T167/G143/W145；另行開發中的候選須保留自己的身份及未完成範圍。

| 順序 | 修復線 | 現況與下一步 |
| --- | --- | --- |
| P0 | 進食／調酒HUD及延遲 | T167/G143承接位置、首幀和快取，並加入上述游標／進食修補，最新延遲／FPS及快開仍待確認。沿用自然操作回饋與既有場景，不重啟探針或重寫已修路由。[客戶端範圍](../docs/HUD-COMPAT-CLIENT-HANDOFF-20261012.md) |
| P1 | 調料瓶／物品資料比較 | Grilling [PR200](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/200)已關閉、未合併，由已合併的[PR215](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/215)整合窄差異並隨G143發布；[PR213](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/213)亦已關閉、未合併。原draft失敗保持歷史身份，不能改標成功。同瓶搖勻／撒料／取消／換槽／雙手／重登仍待完整真人結果。 |
| P1 | Bedrock作者新版整套適配 | Cookery1.6.1／ChineseFood1.0.5／Nether及End1.0.2尚未安裝；新UUID、API／blockstate、掛鉤、指南與資料遷移須一起適配。 |
| P1 | 煙火／Grilling生存料理全流程 | 現行實作與限制見[Grilling矩陣](https://github.com/casama233/kaleidoscope-grilling-unofficial/blob/main/docs/PARITY-MATRIX.md)；固定牛肉串從取得、油／四翻、同瓶搖勻撒料到取出食用保存仍缺當前完整真人結果。 |
| P2 | 已部署互動／模型效果 | T156杯架、T159香薰、T160動態物品側邊修補已承接；實際選取／多視角畫面待確認，沒有新失敗不另開重寫。秘製串背包動態icon仍是真正未實作項，與手持模型分開。 |
| P2 | 當前Java分支剩餘玩法差距 | 先處理World Liquor掉落因果／重入及移動差距，再按各庫矩陣處理Tavern儲存／板面／效果平台缺口；[World Liquor矩陣](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/blob/main/docs/PARITY-MATRIX.md)。來源反例、平台限制與未驗收分開，不概稱效果一比一完成。 |
| P3 | World Liquor26.1.2獨立適配 | custom Luck／BlockDrops／註冊仍待完成；現行1.21.1已承接obsidian配方、milk及高度，不能重開為未修。見[重估](world-liquor-26.1.2-1.1.6-review.json)。 |

Dot舊錄影保留其原候選不明／有限觀察範圍，不挪作T167/G143驗收。料理／projectile／seasoning舊工作只保留唯一差異供審查；部分runtime已在main或比main舊，禁止整份覆蓋。舊工具、hold及部署草稿不列為遊戲候選。

10/15較早已合併的T371離線驗收預檢、G212 Windows錯誤碼、W129文件影響分類與private-integration回歸整合都只改工具／測試，這些PR本身沒有新遊戲版本或LIVE部署；離線預檢也不是已接入全部發佈入口的強制門檻。依[現行精簡流程](UPDATE-WORKFLOW.md)，本次整理不升包、不重跑成功遊戲證據、不重啟LIVE。

## 前輪部署與發布證據（歷史保留）

以下段落只屬T166/G142/W144/private-integration；不以其9349檔、收據或warnings代替現行批次。

前輪raw收據SHA256為`ca11c98cd173114f1c512b7fcc2cdb4be56508546fec0b5b3e0bb0ba99a0ce83`，reviewed為`fca0008bef68b99b4dfd5e0f3f8e3a0e24807ad1840fc2a6378b828c8b44d0e8`；政策installed／deferred綁相同reviewed SHA。三次真正手動發布T38574091380／G38574057674／W38574143687均成功，六個公開包9349檔與收據及LIVE一致、prerelease=false。酒館首次核對誤用server原生包路徑，保留失敗後針對性重試；匿名下載數如實為2／1／1，未改遊戲包。private-integration未公開。

存檔首次／重啟均保留18份玩家紀錄及2個受檢容器。Poststart214 warnings／0 errors，watchdog187（9 Spike／178 Slowdown）；不能由此推算FPS或延遲改善。真人最新延遲、完整輸入／AMW29通道／飽和度／普通提示／UI比例與聲畫仍未驗收；[既有驗收邊界](../docs/HUD-COMPAT-CLIENT-HANDOFF-20261012.md)不要求使用者再跑探針。前輪調酒游標partial-tick插值尚未完成；T167的來源修補見上文，完整Java一比一與真人效果仍未驗收。

[T155歷史部署與公開核對](PUBLIC-DOWNLOAD-LIVE-PERSISTENT-HUD-20261013.md)保留原收據、失敗與觀察範圍，不作現行成功證據。

## 作者與維護

既有摘要保留的BSM Java唯讀查核時間為 **2026-10-15 12:23:03 HKT**，Bedrock為 **12:17:04 HKT**；`all_reference_release_metadata_current=false`、`full_java_parity_verified=false`仍保持，不能標成全分支最新或完整一比一。歷史五分鐘漂移巡檢於 **13:00:04 HKT** 為ok；這是該時刻檔案／政策一致證據，不代表新一次真人或服務啟動驗收。

依[java-upstream.json](java-upstream.json)分開追蹤Tavern1.2.0（Forge1.20.1／Neo1.21.1）、Grilling1.1.1兩分支、World Liquor Forge1.1.12／Neo1.21.1的1.1.11；未發布T26來源與W26／1.1.6仍另列。W共享obsidian1000／1800→1、milk識別與高度已承接，magma3僅legacy；customLuck／BlockDrops／註冊等26差異仍待適配，見[原審查與重估](world-liquor-26.1.2-1.1.6-review.json)。

現行摘要保留的Bedrock作者鎖為Cookery1.6.0、ChineseFood1.0.4、ImmersiveEating1.1.0、Nether1.0.1、End1.0.1；國味1.0.10432及renderer32由reviewed integration原樣保留。AMW2.6.28、JavaSaturation1.5.5及UIQueue1.6.10034為登記HUD相容變體，並非宣稱作者正式新版。[沉浸進食適配](IMMERSIVE-EATING-110-ADAPTATION.md)。

[private deployment time]查到Cookery1.6.1（CF9123386）、ChineseFood1.0.5（CF9123382）、Nether1.0.2（CF9123379）、End1.0.2（CF9123371）；10/12已取得四份官方原包並驗SHA1／MD5，八個BP／RP UUID均更新；Script API仍2.7.0／UI2.0.0，但Cookery新增湯底API／修locale與26個blockstate schema，宿主掛鉤多处preimage失效。仍待資料所有權／blockstate與API適配，尚未安裝或改鎖。已部署版本與作者最新查核分開記錄，不能標成全數最新。

依使用者[private deployment time]要求，開發部署改為一次停服備份、一次保存世界first／restart及正常部署讀回；清理僅保留最新完整可回退備份，尚在使用或失敗／不完整的現場保留。原CI失敗、舊收據、歷史發版與獨立觀察保持原身份。詳[MAINTENANCE.md](MAINTENANCE.md)及[UPDATE-WORKFLOW.md](UPDATE-WORKFLOW.md)。文件整理不改runtime、包身份或重啟LIVE。
