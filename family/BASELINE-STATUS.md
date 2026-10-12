# 家族現行基線與差距

**[private deployment time]**：managed-server 已部署 **酒館0.6.149／燒烤2.8.130／世界名酒0.1.126／私有料理1.0.34**；Cookery1.6.0、沉浸進食1.1.0、登記AMW相容變體2.6.28。引擎1.26.52.3，完整 **42包（22BP／20RP）**。Canonical PR／CI、完整家族static、停服存檔副本first／restart、准入、逐檔／順序及啟動讀回通過，當次狀態RUNNING；`client=false`、`production_ready=false`、`pending_client_acceptance`。

[三個公開下載與LIVE逐檔核對](PUBLIC-DOWNLOAD-LIVE-HUD-20261013.md)已完成；完整自有六包9343檔相等，私有整合及第三方host變體另有canonical來源。舊[T148核對](PUBLIC-DOWNLOAD-LIVE-UI-20261012.md)及[T147核對](PUBLIC-DOWNLOAD-LIVE-20261012.md)保留原收據與版本身份。

## 本輪修補與真實剩餘範圍

| 包 | 已修與保留 | 剩餘差距 |
|---|---|---|
| Tavern T149 | 指南／擴充編碼與傳送前準備分批讓出；成功的原生item tag讀取於本次boot重用，擴充替換仍更新。雪克杯圖形經已觀測可選UI Queue／title路由，保留原圖、HUD200、50ms游標、配方與結算。 | 啟動仍有Spike／Slowdown；現服黑板位置／焦點、投料／搖晃／進度／聲音與快速重開待真人；正式多行、任意裝飾原料、純roll／穿牆輪廓與完整Java聲畫仍有差距。 |
| Grilling G130 | 食用圖形改用命名空間封包／可選路由，保留獨立最新快照及明確END；原102像素黃綠Atlas、動畫、物品守恆、Uses／Numb與API0.2.10保持。 | 啟動仍有Spike／Slowdown；快速重開短空條、任意秘製串圖示／進食HUD、完整原作姿勢、原生流體／碰撞與真人聲畫仍待實測。 |
| World Liquor W126 | BP／RP精確配對T149，指南註冊分批準備；原配方／內容、84類含魚、67頁及效果判定保持。 | 啟動仍有Spike／Slowdown；Incoming取消／重入／fallback／marker／causal drops、SkullOwner、Luck loot、Elbow合成、CaptainGift碰撞、automation與26.1.2整分支。 |
| 私有料理1.0.34及HUD變體 | 新增指南有界接收，reviewed integration快取與renderer32、ChineseFood1.0.10432保留；五份AMW2.6.28／JavaSaturation1.5.5／UIQueue1.6.10034登記變體共3817檔經實際來源CI及本輪fresh saved-world native，原玩法／資產保全。 | Cookery仍有Spike／Slowdown，Node差分75→7次鍋類重建不算引擎效能驗收；新作者Cookery1.6.1另待UUID／API／保存適配。 |
| Immersive Eating1.1.0 | 保留已適配的作者原包、新UUID／API／相依及四種新增食物；原指南、手部動畫與音效保留。 | 真玩家進食、第一人稱、音效啟停與設定保存待接受；載入成功不等於渲染驗收。 |

詳各canonical [Tavern matrix](../docs/PARITY-MATRIX.md)、[Grilling matrix](https://github.com/casama233/kaleidoscope-grilling-unofficial/blob/main/docs/PARITY-MATRIX.md)、[World Liquor matrix](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/blob/main/docs/PARITY-MATRIX.md)。原始HUD100失敗與HUD200有限診斷、G126/G127指定持握／FOV影片、G125 DIAG1的Uses觀察保留原版本與範圍；近嘴放大、其他視角／操作、Numb原生觸發和新家族完整真人驗收仍待完成。

本輪自有圖形不再覆寫共享Actionbar，但未協調的title寫入、第三方整份HUD覆蓋及真人畫面仍有相容限制，不能推論任意addon已驗收。[本輪客戶端流程](../docs/HUD-COMPAT-CLIENT-HANDOFF-20261012.md)包含完整食用／取消／快開、調酒、AMW29通道、飽和度與普通提示。Dot既有取消保留物品、完成後退出、調酒裝料／返瓶／產出通過及兩次快開短空條，來源與客戶端版本未知，不能當新家族驗收。其缺少的[BSM上游唯讀結果](JAVA-UPSTREAM-READONLY-20261012.md)已能由GitHub讀取，原時間2026-10-12 18:23:03 HKT；本機連線／執行狀態仍未知，快照不是永久最新結果。

## 啟動watchdog尚未全解決

當次poststart **292 warnings／0 errors**，其中 **265 watchdog：9 Spike、254 Slowdown、2 High Memory**。以下四包仍有警告，其他addon及全局記憶體另有紀錄，不能以載入成功當效能通過。

| 包 | Spike | Slowdown |
|---|---:|---:|
| Tavern | 2 | 75 |
| Grilling | 1 | 39 |
| World Liquor | 1 | 81 |
| Cookery | 1 | 20 |

W最大Spike由1479ms至284ms是兩次啟動的有限觀察；採樣窗口分別54.892秒與75.552秒，不能比較總告警數而宣稱全局效能改善。High Memory兩筆仍在，後續原生來源profiling尚在進行，不改寫已發布候選狀態。

[QA工具PR340](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/340)已經實際CI檢查合併：以後隔離引擎保留LIVE明確設定的watchdog值，目前Spike／Slowdown門檻為100／10ms。舊QA未設定這兩值會關閉對應警告，因此其零警告不當效能成功；原載入／保存證據保留原範圍與結果。工具不改runtime、不升包或重啟LIVE。

## 來源與當次證據

- T：[功能PR339](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/339)已檢查合併；部署／發布來源 `75acd5884fabd09ece2a02fa3384099d325f6f83`。後續純QA工具PR340合併為 `5037c9fa8beb6b68d6832a56703727ffae150e67`，不改本次遊戲輸出。[T149修補範圍](../docs/RELEASE-NOTES-0.6.149.md)及舊T148／T147診斷保持原身份。
- G：[PR198](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/198)已檢查合併，部署／發布來源 `a567e17c0316f7f2175dfef07004bb944634ca90`。
- W：[PR110](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/pull/110)已檢查合併，部署／發布來源 `57f8fef7c56b2811f198c28daed09a5e27ce6a36`。私有料理／變體修正經核驗私有遠端PR及實際必要CI合併，其私人來源與證據另行保留。
- 本次紀錄 `private-operation-record`，reviewed SHA **`4b8a4746ab253f05da7b3ed10b2b4cf8d624eda652d04b5458fb3673f6c8fefb`**，政策准入與延期真人登記綁同SHA；原組裝SHA `3e84b79a49946880128a8a09836860038775cfbcaa2756e8648f8520ae9d67e6` 分開保留。沿用成功CI，完整家族static、一次新鮮停服存檔first／restart、family_guard／BSM准入及逐檔／順序讀回通過；未另建新世界重跑。
- 保存演練的兩次啟動均保留玩家記錄（數量未公開）、容器（數量未公開）及非空T原生儲存。冰櫃樣本（數量未公開），不能當非空投料證據。此次安裝保留LIVE原有DB與`level.dat`，沒有重新執行舊UUID遷移。
- 保留共用指南的227條目、七入口與三語投影；獨立書及可選Cookery入口共用內容。先前接收證據保留原身份，真人閱讀／排版及操作驗收仍待進行。
- 隔離原生演練皆0玩家／無模擬玩家；載入／資料保存與client／效能验收分開。作者快取／指南回饋已prepared，仍待可用作者通道送達，不宣稱已送出或收到回覆。

## 作者與維護

依[java-upstream.json](java-upstream.json)分開追蹤Tavern1.2.0（Forge1.20.1／Neo1.21.1）、Grilling1.1.1兩分支、World Liquor Forge1.1.12／Neo1.21.1的1.1.11；未發布T26來源與W26／1.1.6仍另列。W共享obsidian1000／1800→1、milk識別與高度已承接，magma3僅legacy；customLuck／BlockDrops／註冊等26差異仍待適配，見[原審查與重估](world-liquor-26.1.2-1.1.6-review.json)。

本次部署的Bedrock作者鎖為Cookery1.6.0、ChineseFood1.0.4、ImmersiveEating1.1.0、Nether1.0.1、End1.0.1；國味1.0.10432及renderer32由reviewed integration原樣保留。AMW2.6.28、JavaSaturation1.5.5及UIQueue1.6.10034為登記HUD相容變體，並非宣稱作者正式新版。[沉浸進食適配](IMMERSIVE-EATING-110-ADAPTATION.md)。

[private deployment time]查到Cookery1.6.1（CF9123386）、ChineseFood1.0.5（CF9123382）、Nether1.0.2（CF9123379）、End1.0.2（CF9123371）；10/12已取得四份官方原包並驗SHA1／MD5，八個BP／RP UUID均更新；Script API仍2.7.0／UI2.0.0，但Cookery新增湯底API／修locale與26個blockstate schema，宿主掛鉤多处preimage失效。仍待資料所有權／blockstate與API適配，尚未安裝或改鎖。已部署版本與作者最新查核分開記錄，不能標成全數最新。

依使用者[private deployment time]要求，開發部署改為一次停服備份、一次保存世界first／restart及正常部署讀回；清理僅保留最新完整可回退備份，尚在使用或失敗／不完整的現場保留。原CI失敗、舊收據、歷史發版與獨立觀察保持原身份。詳[MAINTENANCE.md](MAINTENANCE.md)及[UPDATE-WORKFLOW.md](UPDATE-WORKFLOW.md)。文件整理不改runtime、包身份或重啟LIVE。
