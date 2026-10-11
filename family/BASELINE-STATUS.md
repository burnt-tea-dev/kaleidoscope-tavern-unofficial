# 家族現行基線與差距

**2026-10-11 12:57:47 香港時間**：luosen 已部署 **酒館0.6.146／燒烤2.8.125／世界名酒0.1.123／私有料理1.0.32**；Cookery1.6.0、沉浸進食1.1.0、AMW2.6.27。引擎1.26.52.3，完整 **42包（22BP／20RP）**。當次讀回 RUNNING、poststart `ok=true`／`errors=[]`、drift `ok=true`；`client=false`、`production_ready=false`、`pending_client_acceptance`。

## 本輪修補與真實剩餘範圍

| 包 | 已修與保留 | 剩餘差距 |
|---|---|---|
| Tavern T146 | 原料載入避開 before-event 的受限 metadata 讀取；黑板使用正確原生逆轉換，signature62 在普通維護時重建舊字形；進度圖保持100ms，游標仍按50ms移動。保留T144單一輸入框修補、T145手持辨識、七入口指南及存檔。 | 現服黑板位置／焦點、投料／搖晃／進度與聲音仍待真人確認；正式多行、任意裝飾原料、純roll／穿牆輪廓與完整Java聲畫仍有差距。 |
| Grilling G125 | 修正受限事件與延後站點辨識、取消／拆機守恆、滿背包出料；調整烤架亮度、油液及牆譜畫面、Numb相位與搖瓶音效。保留可保存調料映射與API0.2.10。 | 任意秘製串背包圖示／進食HUD、完整原作姿勢、原生流體／碰撞、宿主操作與真人聲畫仍待完成／實測。 |
| World Liquor W123 | BP／RP精確配對T146，保留W120斬首／肘擊LivingEntity判定、84類含魚、67頁、配方／作者資源及確認錨。 | Incoming取消／重入／fallback／marker／causal drops、SkullOwner、Luck loot、Elbow原力合成、CaptainGift碰撞、automation與26.1.2整分支。 |
| Immersive Eating1.1.0 | 保留已適配的作者原包、新UUID／API／相依及四種新增食物；原指南、手部動畫與音效保留。 | 真玩家進食、第一人稱、音效啟停與設定保存待接受；載入成功不等於渲染驗收。 |

詳各canonical [Tavern matrix](../docs/PARITY-MATRIX.md)、[Grilling matrix](https://github.com/casama233/kaleidoscope-grilling-unofficial/blob/main/docs/PARITY-MATRIX.md)、[World Liquor matrix](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/blob/main/docs/PARITY-MATRIX.md)。T146先前獨立錄影的有限觀察保留原範圍：持續按住時切槽仍不確定，同秒快速重啟未測，無音訊及完整家族真人驗收。

## 來源與當次證據

- T：[功能PR324](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/324)與[流程PR325](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/325)，部署來源`b8da0d0b770fbd3e432f88c01fe3a4d7332abd87`。見[T146範圍](../docs/RELEASE-NOTES-0.6.146.md)；流程變更沿用相同runtime的成功CI，不重跑玩法套件。
- G：[PR191](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/191)及[PR192](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/192)，部署來源`d10d3b12b6cbbf922b0e940fbf174c7b24edf223`。見[G125](https://github.com/casama233/kaleidoscope-grilling-unofficial/blob/d10d3b12b6cbbf922b0e940fbf174c7b24edf223/docs/STATUS-A2.8.125.md)。
- W：[PR105](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/pull/105)，部署來源`2280e740843b89c190645300d5b92d3b2e608807`。見[W123](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/blob/2280e740/docs/RELEASE-NOTES-0.1.123.md)。
- 本次紀錄`20261011-t146-g125-w123-p32`，reviewed SHA **`ae337f230720fa0204c06e7a9e77129784d131cf4790e1f69d53b677036d8de1`**，政策准入與延期真人登記綁同SHA。完整家族static、一次新鮮停服存檔的first／restart、family_guard／BSM准入及逐檔／順序讀回通過；該保存世界同時供應BDS與存檔證據，未另建新世界重跑。
- 保存演練的兩次啟動均保留18筆玩家資料、2個容器及非空T原生儲存。冰櫃輸入0樣本，不能當非空投料證據。此次安裝保留LIVE原有DB與`level.dat`，沒有重新執行舊UUID遷移。
- 保留共用指南的227條目、七入口與三語投影；獨立書及可選Cookery入口共用內容。先前接收證據保留原身份，真人閱讀／排版及操作驗收仍待進行。
- 當次poststart **409 warnings／0 errors**；既有警告及Java差距仍列明，沒有聲稱效能或完整一比一接受。隔離原生演練皆0玩家／無模擬玩家。

## 作者與維護

依[java-upstream.json](java-upstream.json)分開追蹤Tavern1.2.0（Forge1.20.1／Neo1.21.1）、Grilling1.1.1兩分支、World Liquor Forge1.1.12／Neo1.21.1的1.1.11；未發布T26來源與W26／1.1.6仍另列。W共享obsidian1000／1800→1、milk識別與高度已承接，magma3僅legacy；customLuck／BlockDrops／註冊等26差異仍待適配，見[原審查與重估](world-liquor-26.1.2-1.1.6-review.json)。

本次部署的Bedrock作者鎖為Cookery1.6.0、ChineseFood1.0.4、ImmersiveEating1.1.0、Nether1.0.1、End1.0.1；國味1.0.10432是私有整合1.0.32的登記相容變體。AMW2.6.27保留已核對的外部修補，並非宣稱作者正式最新版。[沉浸進食適配](IMMERSIVE-EATING-110-ADAPTATION.md)。

2026-10-11查到Cookery1.6.1（CF9123386）、ChineseFood1.0.5（CF9123382）、Nether1.0.2（CF9123379）、End1.0.2（CF9123371）；本輪原包下載回覆404，維持待審，尚未安裝或改鎖。已部署版本與作者最新查核分開記錄，不能標成全數最新。

依使用者2026-10-11要求，開發部署改為一次停服備份、一次保存世界first／restart及正常部署讀回；清理僅保留最新完整可回退備份，尚在使用或失敗／不完整的現場保留。原CI失敗、舊收據、歷史發版與獨立觀察保持原身份。詳[MAINTENANCE.md](MAINTENANCE.md)及[UPDATE-WORKFLOW.md](UPDATE-WORKFLOW.md)。文件整理不改runtime、包身份或重啟LIVE。
