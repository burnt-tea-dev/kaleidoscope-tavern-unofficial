# 家族現行基線與差距

**2026-10-13 01:54:30 香港時間**：luosen **T150／G130／W127／private1.0.34／Ribbits1.0.10036**，42包（22BP／20RP）、BDS1.26.52.3、RUNNING。Canonical PR／CI、static、一次停服存檔first／restart、完整准入及逐檔／順序讀回通過；`client=false`、`production_ready=false`、`pending_client_acceptance`。

[公開下載核對](PUBLIC-DOWNLOAD-LIVE-STARTUP-20261013.md)確認六自有包9344檔與LIVE／reviewed receipt相同；G130維持原release。私有料理／Ribbits及第三方host變體另有來源。舊[149](PUBLIC-DOWNLOAD-LIVE-HUD-20261013.md)、[148](PUBLIC-DOWNLOAD-LIVE-UI-20261012.md)、[147](PUBLIC-DOWNLOAD-LIVE-20261012.md)及其他歷史proof／parity保持原版本與範圍。

## 本輪來源修補與界限

| 範圍 | 已改／保持 | 未完成／證據界限 |
|---|---|---|
| T150 | legacy21個product投影移到建置，28個page逐字節保全；native字串quote分批、保留原序列化輸出，指南內容／配方保持。 | page／wire來源回歸不是整包bytes相同、BDS效能或真人完整操作；原黑板、聲畫及Java差距仍在。 |
| G130 | 玩法／圖形／配方／結算保持，來源及原公開release不變；不製造G131。 | 快速重開短空條及新家族聲畫／操作仍待真人；旧影片版本未知不當本輪通過。 |
| W127 | 精確配對T150与同SDK，fixture指定原W125 production的175註冊封包逐字相同，內容／配方保持。 | 175是來源fixture範圍，不是LIVE投遞／ACK、任意輸入或完整原生玩法接受。 |
| Ribbits1.0.10036 | 54個來源structure場景29635→158呼叫；158個connection／順序保持；未知ID／size／table／metadata保守fallback，原13BP／4RP差異保留。 | 綁final10036實際source CI及本輪fresh saved-world native，不重用10035歷史CI；真人正常生成／connection／互動待驗。 |
| P34／原五份HUD變體 | 私有自有內容、P33快取／P32 renderer、ChineseFood1.0.10432及五份HUD變體全部不變，不宣稱P35或新HUD修補。 | Source-operation counts、載入及保存不等於client或全局效能接受。 |

## 啟動watchdog尚未全解決

Poststart **257 warnings／0 errors**，其中 **230 watchdog（9 Spike、220 Slowdown、1 High Memory）**。當次T初始化249ms／指南COMMIT288ms、Ribbits431ms、W265ms、G447ms、Cookery310ms Spike仍在；不同窗口不作百分比或全局效能比較，不抬門檻／隱藏告警。後續未凍結原型不屬本次已部署候選。

本輪native QA已含[工具PR340](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/340)，保留LIVE明確Spike100／Slowdown10ms門檻。First410／restart365 warnings，各exit0／errors0；旧R149 native未設定值而關閉對應告警，不能混比性能，也不把旧保存成功改成效能通過。

真人完整食用／取消／快開、調酒、AMW29通道、飽和度／普通提示及UI profile／scale仍待[回歸](../docs/HUD-COMPAT-CLIENT-HANDOFF-20261012.md)。自有圖形不覆寫Actionbar，但未協調title寫入或第三方整份HUD不能保證相容；完整Java一比一、作者新版UUID／API／保存適配仍未完成。Dot原兩次短空條來源／client版本未知，不重標成本輪通過。

## 來源與當次證據

- T：[PR342](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/342)，部署／發布來源 `3f59f984e55fca1ad7ff0a1ee4b7281ecd654daa`。
- G：不變[PR198](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/198)，來源 `a567e17c0316f7f2175dfef07004bb944634ca90`。
- W：[PR111](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/pull/111)，來源 `eaf1fa03a182f32b98fc04727c399f19b982423c`。私有Ribbits來源经核驗私有遠端／實際必要功能CI合併；付費pre-commit服務unavailable／原error保留，未偽寫成功。
- 紀錄 `20261013-startup-t150-g130-w127-p34-ribbits10036`，reviewed SHA **`c0d1f1d1c47da8fb53b7c2e6d8ab9c85ad85f73dd0d1e5c5bed0a26b491c92fa`**，政策installed／deferred_client_acceptance綁同SHA；original SHA `285838cbfc8ff22b55b72d312ad3f8bec3bab7721a09a27543804ce9759fa6bb` 分開保留。
- First／restart保留18筆玩家記錄、2容器及原生儲存；freezer0，不當非空投料證據。正式DB／level.dat在安裝保持，未另建新世界／使用模擬玩家。只保留最新完整回退，6個舊生成根已清理，磁碟可用空間增加1,657,528,320 bytes；unknown／partial及仍引用資料受保護，原失敗JSON／日誌／observer／來源保持。
- 作者料理快取／指南回饋仍prepared/pending，不宣稱已送達。指南七入口及旧修補／錄影身份保持；完整差距見各canonical PARITY-MATRIX。

## 作者與維護

依[java-upstream.json](java-upstream.json)分開追蹤Tavern1.2.0（Forge1.20.1／Neo1.21.1）、Grilling1.1.1兩分支、World Liquor Forge1.1.12／Neo1.21.1的1.1.11；未發布T26來源與W26／1.1.6仍另列。W共享obsidian1000／1800→1、milk識別與高度已承接，magma3僅legacy；customLuck／BlockDrops／註冊等26差異仍待適配，見[原審查與重估](world-liquor-26.1.2-1.1.6-review.json)。

本次部署的Bedrock作者鎖為Cookery1.6.0、ChineseFood1.0.4、ImmersiveEating1.1.0、Nether1.0.1、End1.0.1；國味1.0.10432及renderer32由P34原樣保留。AMW2.6.28、JavaSaturation1.5.5及UIQueue1.6.10034為登記HUD相容變體，並非宣稱作者正式新版。[沉浸進食適配](IMMERSIVE-EATING-110-ADAPTATION.md)。

2026-10-11查到Cookery1.6.1（CF9123386）、ChineseFood1.0.5（CF9123382）、Nether1.0.2（CF9123379）、End1.0.2（CF9123371）；10/12已取得四份官方原包並驗SHA1／MD5，八個BP／RP UUID均更新；Script API仍2.7.0／UI2.0.0，但Cookery新增湯底API／修locale與26個blockstate schema，宿主掛鉤多处preimage失效。仍待資料所有權／blockstate與API適配，尚未安裝或改鎖。已部署版本與作者最新查核分開記錄，不能標成全數最新。

依使用者2026-10-11要求，開發部署改為一次停服備份、一次保存世界first／restart及正常部署讀回；清理僅保留最新完整可回退備份，尚在使用或失敗／不完整的現場保留。原CI失敗、舊收據、歷史發版與獨立觀察保持原身份。詳[MAINTENANCE.md](MAINTENANCE.md)及[UPDATE-WORKFLOW.md](UPDATE-WORKFLOW.md)。文件整理不改runtime、包身份或重啟LIVE。
