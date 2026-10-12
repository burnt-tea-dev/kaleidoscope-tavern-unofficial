# 家族現行基線與差距

**2026-10-12 21:21:24 香港時間**：luosen 已部署 **酒館0.6.148／燒烤2.8.129／世界名酒0.1.125／私有料理1.0.33**；Cookery1.6.0、沉浸進食1.1.0、AMW2.6.27。引擎1.26.52.3，完整 **42包（22BP／20RP）**。完整家族static、停服存檔副本first／restart、准入、逐檔／順序及啟動讀回通過，當次狀態RUNNING；`client=false`、`production_ready=false`、`pending_client_acceptance`。

[三個公開下載與LIVE逐檔核對](PUBLIC-DOWNLOAD-LIVE-UI-20261012.md)已完成；完整自有六包9339檔相等，私有整合及第三方host變體的範圍分開列明。舊[公開核對](PUBLIC-DOWNLOAD-LIVE-20261012.md)保留原收據與版本身份。

## 本輪修補與真實剩餘範圍

| 包 | 已修與保留 | 剩餘差距 |
|---|---|---|
| Tavern T148 | HUD移入獨立註冊命名空間，與G共用相同最小可選掛載及內部封包過濾，保留原factory／效果、HUD200及50ms游標。保留受限metadata、黑板signature62逆轉換、單一輸入框、手持辨識、指南與存檔修補。 | 現服黑板位置／焦點、投料／搖晃／進度與聲音仍待真人確認；正式多行、任意裝飾原料、純roll／穿牆輪廓與完整Java聲畫仍有差距。 |
| Grilling G129 | HUD移入獨立註冊命名空間及共用掛載，保留原102像素黃綠Atlas、動畫、進食時間與退出流程。保留取消／拆機守恆、滿背包出料、站點／調料API0.2.10、Uses唯一行與Ingredients／custom／RawMessage lore、Numb修補。 | 快速重開短空條、任意秘製串背包圖示／進食HUD、完整原作姿勢、原生流體／碰撞、宿主操作與真人聲畫仍待完成／實測。 |
| World Liquor W125 | BP／RP精確配對T148，其他runtime保持，包含W120斬首／肘擊LivingEntity判定、84類含魚、67頁、配方／作者資源及確認錨。 | Incoming取消／重入／fallback／marker／causal drops、SkullOwner、Luck loot、Elbow原力合成、CaptainGift碰撞、automation與26.1.2整分支。 |
| 私有料理1.0.33 | 唯一新元件是Cookery1.6.0配方快取按需重建；其餘料理／renderer32與ChineseFood1.0.10432保留。來源模組Node差分在六批次／11類作者註冊下，鍋類重建75→7，讀取／ACK／覆寫語義相等。 | Node診斷不是BDS watchdog或客戶端效能驗收；LIVE仍有慢速警告，新作者Cookery1.6.1另待UUID／API／保存適配。 |
| Immersive Eating1.1.0 | 保留已適配的作者原包、新UUID／API／相依及四種新增食物；原指南、手部動畫與音效保留。 | 真玩家進食、第一人稱、音效啟停與設定保存待接受；載入成功不等於渲染驗收。 |

詳各canonical [Tavern matrix](../docs/PARITY-MATRIX.md)、[Grilling matrix](https://github.com/casama233/kaleidoscope-grilling-unofficial/blob/main/docs/PARITY-MATRIX.md)、[World Liquor matrix](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/blob/main/docs/PARITY-MATRIX.md)。原始HUD100失敗與HUD200有限診斷、G126/G127指定持握／FOV影片、G125 DIAG1的Uses觀察保留原版本與範圍；近嘴放大、其他視角／操作、Numb原生觸發和新家族完整真人驗收仍待完成。

共享Actionbar競爭及第三方整份HUD覆蓋仍有相容限制，不能推論任意addon已驗收。[本輪客戶端流程](../docs/HUD-COMPAT-CLIENT-HANDOFF-20261012.md)包含完整食用／取消／快開、調酒、原生HUD與外部提示。Dot既有取消保留物品、完成後退出、調酒裝料／返瓶／產出通過及兩次快開短空條，來源與客戶端版本未知，不能當新家族驗收。其缺少的[BSM上游唯讀結果](JAVA-UPSTREAM-READONLY-20261012.md)已能由GitHub讀取，時間2026-10-12 18:23:03 HKT；本機連線／執行狀態仍未知，快照不是永久最新結果。

## 來源與當次證據

- T：[HUD PR334](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/334)、[唯讀交接PR335](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/335)、[快取准入PR336](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/336)、[CI狀態分類PR337](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/337)已檢查合併；部署來源 `4698a3ab3d0ac36422e2c11d598aca6fed16ef98`。[T148修補範圍](../docs/RELEASE-NOTES-0.6.148.md)及舊T147診斷保持原發布身份。
- G：[PR197](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/197)已檢查合併，部署來源 `2a923c368a9bef490d44ba3f13c0ac1650052164`。
- W：[PR109](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/pull/109)已檢查合併，部署來源 `7278774a7eebd8f72145a22f8dc32f27514261b7`。私有料理修正經核驗私有遠端PR檢查合併，其私人來源与證據另行保留。
- 本次紀錄 `20261012-ui-t148-g129-w125-p33-r2`，reviewed SHA **`26a2e98f64f4dbe04fedc948d317f58956bb97c11b0f00bdddcfefa37415fa15`**，政策准入與延期真人登記綁同SHA。沿用成功CI，完整家族static、一次新鮮停服存檔的first／restart、family_guard／BSM准入及逐檔／順序讀回通過；未另建新世界重跑。
- 保存演練的兩次啟動均保留18筆玩家資料、2個容器及非空T原生儲存。冰櫃輸入0樣本，不能當非空投料證據。此次安裝保留LIVE原有DB與`level.dat`，沒有重新執行舊UUID遷移。
- 保留共用指南的227條目、七入口與三語投影；獨立書及可選Cookery入口共用內容。先前接收證據保留原身份，真人閱讀／排版及操作驗收仍待進行。
- 當次poststart **313 warnings／0 errors**；LIVE慢速警告及Java差距仍列明，沒有聲稱watchdog改善、客戶端效能或完整一比一接受。隔離原生演練皆0玩家／無模擬玩家。

## 作者與維護

依[java-upstream.json](java-upstream.json)分開追蹤Tavern1.2.0（Forge1.20.1／Neo1.21.1）、Grilling1.1.1兩分支、World Liquor Forge1.1.12／Neo1.21.1的1.1.11；未發布T26來源與W26／1.1.6仍另列。W共享obsidian1000／1800→1、milk識別與高度已承接，magma3僅legacy；customLuck／BlockDrops／註冊等26差異仍待適配，見[原審查與重估](world-liquor-26.1.2-1.1.6-review.json)。

本次部署的Bedrock作者鎖為Cookery1.6.0、ChineseFood1.0.4、ImmersiveEating1.1.0、Nether1.0.1、End1.0.1；國味1.0.10432及renderer32是私有整合1.0.33原樣保留的已登記相容內容，沒有隨快取修正換身份。AMW2.6.27保留已核對的外部修補，並非宣稱作者正式最新版。[沉浸進食適配](IMMERSIVE-EATING-110-ADAPTATION.md)。

2026-10-11查到Cookery1.6.1（CF9123386）、ChineseFood1.0.5（CF9123382）、Nether1.0.2（CF9123379）、End1.0.2（CF9123371）；10/12已取得四份官方原包並驗SHA1／MD5，八個BP／RP UUID均更新；Script API仍2.7.0／UI2.0.0，但Cookery新增湯底API／修locale與26個blockstate schema，宿主掛鉤多处preimage失效。仍待資料所有權／blockstate與API適配，尚未安裝或改鎖。已部署版本與作者最新查核分開記錄，不能標成全數最新。

依使用者2026-10-11要求，開發部署改為一次停服備份、一次保存世界first／restart及正常部署讀回；清理僅保留最新完整可回退備份，尚在使用或失敗／不完整的現場保留。原CI失敗、舊收據、歷史發版與獨立觀察保持原身份。詳[MAINTENANCE.md](MAINTENANCE.md)及[UPDATE-WORKFLOW.md](UPDATE-WORKFLOW.md)。文件整理不改runtime、包身份或重啟LIVE。
