# 家族現行基線與差距

**最後部署：2026-10-14 21:41:21 HKT**，managed-server **T166／G142／W144／private-integration／Ribbits1.0.10037**，42包，BDS1.26.52.3正常啟動。來源PR／完整CI、家族static、一次停服存檔副本first／restart、准入及逐檔／順序讀回通過。`client=false`、`production_ready=false`、`pending_client_acceptance`。

| 已部署公開來源 | 提交 | 已合併修復PR／完整來源CI | 正式版 |
| --- | --- | --- | --- |
| Tavern 0.6.166 | `d2d7ef987ab9839643241e960b8ba941b8d0d240` | [PR369](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/369)／[38571836792](https://github.com/casama233/kaleidoscope-tavern-unofficial/actions/runs/38571836792) | [v0.6.166](https://github.com/casama233/kaleidoscope-tavern-unofficial/releases/tag/v0.6.166) |
| Grilling 2.8.142 | `3f63bb32890d67004352e66386d8eaf890daafea` | [PR209](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/209)／[38570580331](https://github.com/casama233/kaleidoscope-grilling-unofficial/actions/runs/38570580331)（含Windows匯出） | [A2.8.142](https://github.com/casama233/kaleidoscope-grilling-unofficial/releases/tag/A2.8.142) |
| World Liquor 0.1.144 | `b6ba608178a6dc944fe4b081bd3615bfddd8b0d6` | [PR127](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/pull/127)／[38570678514](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/actions/runs/38570678514) | [v0.1.144](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/releases/tag/v0.1.144) |

private-integration已完成其PR27／來源CI，僅同步本次provider相依，沒有公開第三方私有內容。以上是收據中的部署來源；之後只更新文件的Git提交不改寫本次部署來源或重啟LIVE。

T165恢復Java中央相對座標；G141按原生剩餘use ticks計算並立即發首幀；T166加入128筆上限的閒置預覽快取，T/G裁剪固定封包中未使用圖形。全部[客戶端回饋及修補狀態](../docs/BUGS.md)保留：圖形／資料碼失敗未改成成功，後續圖形可見也不代表位置、進食與延遲全部驗收。

本次raw收據SHA256為`ca11c98cd173114f1c512b7fcc2cdb4be56508546fec0b5b3e0bb0ba99a0ce83`，reviewed為`fca0008bef68b99b4dfd5e0f3f8e3a0e24807ad1840fc2a6378b828c8b44d0e8`；政策installed／deferred綁相同reviewed SHA。三次真正手動發布T38574091380／G38574057674／W38574143687均成功，六個公開包9349檔與收據及LIVE一致、prerelease=false。酒館首次核對誤用server原生包路徑，保留失敗後針對性重試；匿名下載數如實為2／1／1，未改遊戲包。private-integration未公開。

存檔首次／重啟均保留18份玩家紀錄及2個受檢容器。Poststart214 warnings／0 errors，watchdog187（9 Spike／178 Slowdown）；不能由此推算FPS或延遲改善。真人最新延遲、完整輸入／AMW29通道／飽和度／普通提示／UI比例與聲畫仍未驗收；[既有驗收邊界](../docs/HUD-COMPAT-CLIENT-HANDOFF-20261012.md)不要求使用者再跑探針。調酒游標partial-tick插值與完整Java一比一未完成。

[T155歷史部署與公開核對](PUBLIC-DOWNLOAD-LIVE-PERSISTENT-HUD-20261013.md)保留原收據、失敗與觀察範圍，不作現行成功證據。

## 作者與維護

本次狀態同步讀到的BSM Java唯讀查核時間為 **2026-10-15 06:23:03 HKT**；`all_reference_release_metadata_current=false`、`full_java_parity_verified=false`仍保持，不能標成全分支最新或完整一比一。

依[java-upstream.json](java-upstream.json)分開追蹤Tavern1.2.0（Forge1.20.1／Neo1.21.1）、Grilling1.1.1兩分支、World Liquor Forge1.1.12／Neo1.21.1的1.1.11；未發布T26來源與W26／1.1.6仍另列。W共享obsidian1000／1800→1、milk識別與高度已承接，magma3僅legacy；customLuck／BlockDrops／註冊等26差異仍待適配，見[原審查與重估](world-liquor-26.1.2-1.1.6-review.json)。

本次部署的Bedrock作者鎖為Cookery1.6.0、ChineseFood1.0.4、ImmersiveEating1.1.0、Nether1.0.1、End1.0.1；國味1.0.10432及renderer32由reviewed integration原樣保留。AMW2.6.28、JavaSaturation1.5.5及UIQueue1.6.10034為登記HUD相容變體，並非宣稱作者正式新版。[沉浸進食適配](IMMERSIVE-EATING-110-ADAPTATION.md)。

[private deployment time]查到Cookery1.6.1（CF9123386）、ChineseFood1.0.5（CF9123382）、Nether1.0.2（CF9123379）、End1.0.2（CF9123371）；10/12已取得四份官方原包並驗SHA1／MD5，八個BP／RP UUID均更新；Script API仍2.7.0／UI2.0.0，但Cookery新增湯底API／修locale與26個blockstate schema，宿主掛鉤多处preimage失效。仍待資料所有權／blockstate與API適配，尚未安裝或改鎖。已部署版本與作者最新查核分開記錄，不能標成全數最新。

依使用者[private deployment time]要求，開發部署改為一次停服備份、一次保存世界first／restart及正常部署讀回；清理僅保留最新完整可回退備份，尚在使用或失敗／不完整的現場保留。原CI失敗、舊收據、歷史發版與獨立觀察保持原身份。詳[MAINTENANCE.md](MAINTENANCE.md)及[UPDATE-WORKFLOW.md](UPDATE-WORKFLOW.md)。文件整理不改runtime、包身份或重啟LIVE。
