# 家族現行基線與差距

**2026-10-13 03:44:43 HKT**：luosen **T152／G130／W129／P34／Ribbits1.0.10036**，42包（22BP／20RP），BDS1.26.52.3 RUNNING。Canonical PR／必要CI、static、一次停服存檔副本first／restart、完整准入及逐檔／順序讀回通過。`client=false`、`production_ready=false`、`pending_client_acceptance`。

[本次公開核對](PUBLIC-DOWNLOAD-LIVE-TRANSPORT-20261013.md)確認六包9344檔相同。T152／W129新匿名下載，G130重用R151已核驗匿名archive的同FS硬連結，fresh REST metadata／digest重驗，不稱新G下載。 [151歷史proof](PUBLIC-DOWNLOAD-LIVE-NATIVE-ITEM-20261013.md)與其他原收據保持原身份。

## 本輪修補與界限

T152在收到chunk時累積digest及bytes，以邊界校正核對UTF8總長；ordered COMMIT避免兩次整串integrity掃描，JSON parse／registry install／ACK仍同步。W129只更新三份identity／dependency檔配對T152；SDK／storage／玩法／指南／圖形保持。G130／P34／Ribbits10036／原五份HUD變體不變。

Poststart **245 warnings／0 errors**，其中 **218 watchdog（8 Spike／209 Slowdown／1 High Memory）**。本次窗口沒有再錄到原指南COMMIT約282ms Spike；初始化Spike仍有AMW309、Cookery306、Nether110、Ribbits424、Villager150、W256、T255、G444ms。不同窗口不作百分比或全面效能接受；partial reverse仍有整串FNV fallback。First401／restart361 warnings，各exit0／errors0，保留LIVE100／10ms門檻。

真人食用／取消／快開、調酒、AMW29通道、飽和度／普通提示及UI profile／scale仍待[回歸](../docs/HUD-COMPAT-CLIENT-HANDOFF-20261012.md)。任意第三方whole HUD／title與完整Java一比一未保證。

## 來源與當次證據

T[PR344](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/344)13項必要CI／pre-commit通過（38298429025），發布来源 `f929cd4fcc7a588d6ff8fb23e7ec5af0409dc79d`；W[PR113](https://github.com/casama233/kaleidoscope-world-liquor-unofficial/pull/113)4項必要CI／pre-commit通過（38298439399），來源 `7edcb3589b849ac54533cd78b8c17d9e1d6a4b1b`。T發布38299743225／W38299753605成功；G130沿用[PR198](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/198)／來源 `a567e17c0316f7f2175dfef07004bb944634ca90`。私有34／Ribbits10036內容及原source CI範圍保持，付費pre-commit unavailable不偽寫成功。

紀錄 `20261013-transport-integrity-t152-g130-w129-p34-ribbits10036`；reviewed SHA `34a50a536dff22ca4e202b35f93fd68457b26464833c086057a57efcf1cb2415`，raw SHA `17b31fc666a57ae3bf3efafd509726554dfb2870bc4792acc24c5e97bc2883f3`。政策installed／deferred_client_acceptance綁同reviewedSHA。18筆玩家記錄及2容器保留，freezer0不當非空投料證據；未另建新世界或使用模擬玩家。只保留最新完整回退，清理6個舊生成根，磁碟可用空間增加1,608,294,400 bytes。來源、失敗JSON／日誌及活動工作保留。

## 作者與維護

依[java-upstream.json](java-upstream.json)分開追蹤Tavern1.2.0（Forge1.20.1／Neo1.21.1）、Grilling1.1.1兩分支、World Liquor Forge1.1.12／Neo1.21.1的1.1.11；未發布T26來源與W26／1.1.6仍另列。W共享obsidian1000／1800→1、milk識別與高度已承接，magma3僅legacy；customLuck／BlockDrops／註冊等26差異仍待適配，見[原審查與重估](world-liquor-26.1.2-1.1.6-review.json)。

本次部署的Bedrock作者鎖為Cookery1.6.0、ChineseFood1.0.4、ImmersiveEating1.1.0、Nether1.0.1、End1.0.1；國味1.0.10432及renderer32由P34原樣保留。AMW2.6.28、JavaSaturation1.5.5及UIQueue1.6.10034為登記HUD相容變體，並非宣稱作者正式新版。[沉浸進食適配](IMMERSIVE-EATING-110-ADAPTATION.md)。

2026-10-11查到Cookery1.6.1（CF9123386）、ChineseFood1.0.5（CF9123382）、Nether1.0.2（CF9123379）、End1.0.2（CF9123371）；10/12已取得四份官方原包並驗SHA1／MD5，八個BP／RP UUID均更新；Script API仍2.7.0／UI2.0.0，但Cookery新增湯底API／修locale與26個blockstate schema，宿主掛鉤多处preimage失效。仍待資料所有權／blockstate與API適配，尚未安裝或改鎖。已部署版本與作者最新查核分開記錄，不能標成全數最新。

依使用者2026-10-11要求，開發部署改為一次停服備份、一次保存世界first／restart及正常部署讀回；清理僅保留最新完整可回退備份，尚在使用或失敗／不完整的現場保留。原CI失敗、舊收據、歷史發版與獨立觀察保持原身份。詳[MAINTENANCE.md](MAINTENANCE.md)及[UPDATE-WORKFLOW.md](UPDATE-WORKFLOW.md)。文件整理不改runtime、包身份或重啟LIVE。
