# 完整家族更新流程

`tools/family_update.py` 取代每輪複製、改版號與路徑的私人部署腳本。
版本仍由各自 canonical runtime 決定；本工具不凍結版本、不修改包內容，
不替代 `family_bundle.py`、`family_guard.py` 或 BSM 准入。

2026-10-11 使用者要求刪除繁瑣部署、多餘備份，以功能穩定可玩為優先。
現行流程只做：**沿用來源 CI → 組裝與相依 → 停服備份一份 → 存檔副本載入／重啟 → 准入、更新與讀回**。
BDS 與保存驗證共用同一次演練；不另建新世界再跑相同循環。預設只留最新一份完整回退。

動畫、物品顯示及手持問題先依[家族共用修復流程](MAINTENANCE.md#動畫物品顯示與手持修復)完成官方來源／版本核對與可重現對照。僅更新這些流程文件不建立遊戲候選、不升包、不重啟 LIVE。

## 精簡工作規則（使用者 2026-10-08）

工作以玩家遇到的問題及原作行為為單位，不以增加測試數、收據數或版本數為進度。

1. **只有一個當前入口。** 本機維護固定的當前進度指標，指向現行 LIVE 收據、當前工作區、未完成差距及下一步。開始時讀這些內容和相關來源即可；不要遍歷歷史目錄、重新整理整份時間線，或逐輪複製上一輪報告。歷史原始證據保持不變，結束的舊副本交既有每小時清理。
2. **先確定要修的行為。** 每項工作寫清楚 Java 的觸發／結果、目前的具體差異、要改的模組和一個能分辨修正是否有效的場景。優先修玩法、數量、時序、互動和保存問題；不要以文件美化、更多 hash 或重複探測代替實作。
3. **本機診斷與 CI 分工。** 本機只跑受影響的既有檢查，或重現已發現的具體失敗；完整必要套件由該 PR 的 CI 執行一次。CI 已通過後，沒有新變更或新失敗就不在本機重跑。用設定中的 venv，避免因選錯解譯器缺依賴而重跑。可逆文件整理只審閱差異，不為它新增測試。
4. **新測試須回答問題。** 僅在既有檢查無法覆蓋重要行為／回歸時新增；不要照抄實作公式、測試記錄格式，或用大量排列製造通過數。BDS 用於腳本無法證明的引擎行為、保存與相容性；畫面、聲音及真人操作交 Dot，同一未變候選不反覆啟動引擎等待不同結論。
5. **相關修補先整合再凍結。** 在一個明確玩法問題內，把相依修補、配方／效果／動畫資料及適配一起完成，再凍結版本、PR／CI／合併並組裝候選。不要每改一行就發版；也不要為湊批次拖延已完成候選的 LIVE 部署。
6. **按狀態邊界核對一次。** 同一 prepare 階段已核對的 candidate receipt 傳給 static 和既有 native 證據檢查，不再次掃描所有包。實際啟動新 BDS、停服備份、安裝、重啟與部署後讀回仍各自核對；不跨變更階段永久快取，不刪除准入要求。
7. **只報告新結果。** 完成後更新當前入口、相關差距和 Dot 場景，交代修了甚麼、LIVE 版本及真正未完成的部分。測試數及 hash 留在證據中，不作為還原度或工作量的宣傳。

工具／文件變更未改輸出 runtime 時，合併 canonical Git 即完成套用；不為此新建遊戲候選、升包版本或重啟 LIVE。若出現來源漂移、真實失敗或驗證不足，針對該原因處理，不把全套檢查當成預設排錯方式。

剛完成的部署直接回傳本次lease內已通過的部署後讀回報告與驗證時間；清理結束後不再對最新Git重做同一次部署核對，避免並行來源前進被誤報為已完成部署失敗。這不是永久快取：之後另一次resume／update仍按目前來源、live和政策檢查，來源已變須建立新候選。部署後報告只證明其記錄時間的狀態，持續漂移由既有巡檢負責。

工作區布局、退役條件與部署後清理順序見 [WORKSPACE-MAINTENANCE.md](WORKSPACE-MAINTENANCE.md)。

## 有界診斷與輸出

先用現行索引和檔案清單定位，再讀相關函式／範圍；同一未變輸入不重讀整份文件。
每個診斷回答一個可區分的假設，例如 HUD 壽命是否覆蓋 heartbeat，而非只列封包與貼圖存在。
完整工具輸出保存在既有診斷目錄，對話只回傳錯誤、關鍵證據與摘要；避免全庫 Git 統計和大量搜尋結果。
連續檢查沒有新增證據時改查事件／資料／客戶端來源，不繼續重掃相同檔案。這不省略必要 CI 或部署邊界。
評估效率以已解決且完成必要驗證的問題、返工及總成本為準；工具次數和測試數不單獨代表品質。

## 一次設定，一個入口

將 `family/update-config.example.json` 複製到 **Git 外**的本機設定檔，
填入三個乾淨 canonical main、實際 BDS／世界／quality 路徑、archive 目錄，
以及一個從未用過的候選輸出目錄。各 `pull_requests` 必須填入已合併的實際 PR；
範例的 `0` 是待填值，不能通過驗證。

`api_module` 是本機既有 BSM 認證介面，提供
`req(path, body=None, method='GET')`。密碼、token、原始 BSM 設定和私人套件
不應放在這個倉庫或候選設定檔。Docker 的 API 路徑可用
`api_path_mappings` 明確映射到主機；本工具會核對 BSM servers 根目錄、
active world、summary 名稱及 `server.properties` 原始 bytes，防止停 A 服卻改 B 存檔。

使用設定中的 Python 解譯器，需預先具備 `nbtlib==2.0.4` 與現有 Bedrock
LevelDB Python adapter；`gh` 需已有正常的唯讀 GitHub 認證。缺少依賴會在停服前拒絕。
不要解析 venv Python 的符號連結改用系統 Python，也不要使用 `-O`。

已有 live 開發持續授權時，以單一命令完成：

```sh
/path/to/venv/bin/python tools/family_update.py --config /local/update.json update --execute
```

沒有 `--execute` 時只顯示計畫，不建立候選、不停服、不寫政策。`prepare` 不修改 live；
`prepare` 完成來源、組裝與 static；`deploy` 從本次停服備份完成一次 BDS／保存演練與 canonical／BSM admission。
來源必須是乾淨、與遠端相符的 main，執行中的工具 bytes 也必須與 canonical 相符。

### 明確交付新世界

擁有者選擇放棄舊世界時，在新設定加入 `fresh_world`，並保留 `world_dir` 指向
原活動世界作回退來源。例如（名稱、seed 和生成設定須填實際選擇）：

```json
"fresh_world": {
  "level_name": "New world name",
  "seed": "12345",
  "properties": {"gamemode": "survival", "difficulty": "normal", "level-type": "DEFAULT"}
}
```

新集合只從 canonical 家族鎖／owned sources／extension 組裝；舊 capture 的 retained
包與順序只作回退證據，不自動加入新世界。不得帶舊世界 recovery／migration／observer
或 retained-input profiles；普通更新仍要求原有完整存檔遷移證據。

沿用 `current-author-curated` 集合建立新世界時，可在設定以
`fresh_world_excluded_groups` 列出不再加入的可選 addon 完整名稱。
僅允許已宣告的 literal 行為／資源配對整組移除；未知名稱、單邊包及
Saturation／Fishing 適配包會拒絕。其餘包仍按原來源驗證，缺少依賴仍由
完整家族組裝檢查拒絕。選擇及排除名單記入候選證據，不修改原作者選擇檔。

作者原包已有 PBR、但 RP 最低引擎宣告過舊時，來源鎖可選擇
`manifest_compatibility_release`。同一鎖的 `upstream_manifest_releases`
保存追加的配對版本、原始／輸出完整樹及兩份 manifest 雜湊。組裝器先核對
官方 archive 和原始 UUID／版本，再重新編譯並核對該記錄；只允許兩側版本、
自身配對相依和 RP 最低引擎改動，不改腳本、地形或資產，不標作官方原版。
已發布的記錄保持不變，改動須追加新的配對版本。

同一正常停服窗口保留一份完整舊世界 snapshot、原 properties／政策／current selector 設定及 displaced global
包。隔離引擎使用指定名稱／seed／生成設定，從沒有 DB 或 level.dat 的目錄生成，
同庫只做 first／restart；不複製舊 Spawn／Creative／實驗 metadata，也不加入任何 probe、
測試 overlay、actor repair 或 Fishing observer。成功後精確審計並經既有 guard 准入，
才搬移該乾淨新世界；跨檔案系統搬移前按實際新世界大小確認額外空間及 2 GiB 餘量。

receipt 的 `fresh_world_initialization`／`world_persistence` 通過，
`saved_world_migration` 保持 false。它證明真初始化及同庫正常保存重啟，
不證明舊世界資料遷移、真人畫面或負載效能；client／production_ready 保持 false。
正常 `properties/set` 僅提交 properties，沿現有 API 預設不重啟，讀回原 response、
properties／本地 bytes／STOPPED 後才正常 start 並驗 active world。禁止使用 world/reset。
失敗保留 stopped／lease／新舊資料供恢復，不自行重啟未知舊組合。

已由擁有者正常停服的交接只在 fresh 模式接受：核對原 active world／properties、
STOPPED／零玩家／實際無該 BDS 程序、未變的 completed previous lease 與 current selector，
取得 lease 後再核同一交接，寫既有 `deployment-initial-state.json`；ERROR 或 failed owner 不放行。
若交接時仍 RUNNING，同樣必須明確為零玩家，才可進入正常停服流程。
retention 與 guard 共用 world gate，核真 first／restart 及新 active world 綁定後，
沿既有精確 cleanup plan 保留最新一套完整舊回退、退役舊 generated copies；不把初始化寫成遷移。

主機容量暫不足時，可在不可變設定指定 `native_capacity_wait_seconds`（整數
1–7200）。僅首次 `update --execute` 在 capture、候選與 lease 前有界等待；
按完整 native cap、2 GiB 餘量及既有 32 MiB accounting pad 保守投影，不抵扣
自身匿名記憶體。這不是准入，容量足夠後仍執行新鮮來源及實際 native 門檻；
超時、OOM、控制或來源變動即停止，保留單一狀態，不自動重試。

私有整合正在更新外部AMW相依而尚未完成完整驗證時，可以canonical家族鎖的
`extension_deployment_hold`和設定`extension_hold: true`明列保留目前已安裝的兩側。
`extension`路徑須使用固定私有Git提交的乾淨隔離checkout；最新main／候選保持原狀。
必須保留提交的reason_file、私有遠端身份與main祖先、version／source_trees、當前live
逐檔相等及全部准入／fresh保存門檻。不得沿用保留來安裝新private bytes或改寫收據。

## 哪些工作只做一次

| 階段 | 重用條件 | 不可省略的核對 |
| --- | --- | --- |
| live 清單快照 | 同一輸出目錄已有完整 capture | live 全檔、順序、政策、localization index、server properties、引擎仍相同 |
| 完整家族組裝 | 同候選已成功生成 | 三庫與 extension 的提交／tree／baseline、家族鎖、組裝器、設定、runner、候選全檔仍相同 |
| 功能檢查 | 已合併 PR 的真實 GitHub checks | 完整 PR Git tree 等於本機 main；必要 GitHub Actions checks 都 success；任何失敗／未完成的附加 check 也拒絕 |
| 存檔副本 BDS 首次＋重啟 | 同一部署的 BDS／保存欄位共用一份報告 | 本次停服備份、候選、引擎、原始 logs、零玩家／零錯誤、玩家與容器資料保留；不跨部署沿用舊存檔 |
| 已部署的同一候選 | 完整 live bytes、版號、顺序與政策仍匹配 | 再次呼叫不重啟；來源或 live 已改則拒絕將舊候選當目前版本 |

GitHub 檢查是實際執行的功能測試證據，不再為了填收據在本機重跑同一套。
需要本機診斷時仍可使用各倉庫的既有驗證命令；CI 與本機結果不得混稱。
Tavern 只改家族工具時 baseline lane 仍執行工具測試；runtime 改動才要求完整
runtime lanes。Grilling 與 World Liquor 保留各自必要 job 名称。

候選和 live 的完整包 bytes、版本及順序已相同時，記錄 `no_runtime_changes`，
不做無意義的新世界測試、停服、存檔複製或政策改寫。這不會把既有 pending client 改成通過。

cache 重用只適用於同一份不可變候選。不是只看版號、mtime、`ok=true` 或 README。
失敗、缺檔、hash 不符或執行工具改變時，保留現場並要求新的輸出目錄，
不清掉舊證據硬跑。來源只改文件但完整 commit/tree 已變，當前工具會保守拒絕重用
舊候選；CI 的變更分類負責避免不必要的功能套件執行。

## 每次部署仍需新的存檔證據

每次真正改 live 都取得 maintenance lock／lease，確認最初為 RUNNING，正常停服，
建立全檔一致備份，從**本次**備份建立隔離世界，載入同一個候選並重啟。
`bds` 和 `saved_world_migration` 共同引用這次保存檔演練，不因有兩個欄位再多跑一次。
取消額外新世界首次＋重啟。每次保留一份完整回退，新部署成功後退役更舊且未被引用的副本。

實際安裝前重新比對來源、存檔未被包安裝改寫、完整收據與相依，登記本候選的
`deferred_client_acceptance`，並執行 canonical 與 BSM guard。原始組裝收據不改寫；
驗收結果寫入另一份 reviewed receipt。安裝及啟動後再次比對全檔與順序。

回退失敗或原始包／政策不完整時保持停服及 active `needs_operator_recovery`；
只有核對完成的原始整套包才可重啟。新資料庫不會被舊快照自動覆蓋。

### 來源要求的實驗功能

擁有者允許 Beta APIs 與 creator experiments。必要旗標來自已審查、與 canonical
commit 及 metadata catalog 相符的 curated source selection `required_experiments`，
例如 `{"upcoming_creator_features": true}`；本機 update config 不能另行提供旗標或關閉
既有功能。QA metadata 也保留原有 experiments，不再因省略舊的
`preserve_captured_experiments` 選項而清空它們。

更新器在本次停服一致備份的 QA 副本上只開啟宣告旗標及原生 experiment history bits。
沿用 lossless Bedrock NBT codec，保留其餘全部 typed tags、opaque bytes、原 seed、玩家與
世界 DB；不改原備份。原始與轉換後的 level.dat hash 記入既有 `saved-world-report.json`，
首次載入與同副本重啟均核對必要旗標，重啟輸入 metadata 必須是首次正常保存的輸出。

完整家族 admission 通過後，仍在同一次停服窗口，從正式世界原始 metadata 重算完全相同
轉換才採用，並記入既有 `deployment-result.json`。不複製被 QA 引擎修改過的 level.dat。
若正式存檔在備份後改變、旗標或兩次驗證不符，拒絕採用。相同 pack bytes 但缺少必要
旗標仍需這些門檻，不能當作無變更跳過。

要求原生功能的候選開始採用後發生部署失敗，保留相容候選、最新資料與 maintenance lease 並停服；
即使必要旗標本來已開啟、metadata 不需改寫，候選仍可能在首次啟動遷移方塊／物品資料，
因此同樣記錄採用開始標記並保留相容 runtime。
不自動啟動舊 runtime 或回寫舊 metadata；完整原備份與回退包留供核對後恢復。
目前 `fresh_world` 無受審查的生成前旗標入口，來源要求 experiments 時會明確拒絕，
須先補完該生成路徑的正式驗證。既有世界使用上述同副本轉換，無須重建世界。

若已審查的 managed repair 必須保留目前的玩法裁減，而歷史 approved rollback
含不相容內容，設定 `managed_drift_failure_policy: "retain_stopped"`。
取得 lease 後任何失敗均正常停服、保留最新 DB、現有包和已移出的包，不自動還原或
啟動歷史 runtime；安裝中斷另保存精確移動清單及 active recovery lease。
這個較嚴格的失敗政策不批准原漂移、不替代完整回退，也不允許自動重試。

`memory_budget` 可用同一份 immutable config 加入
`phase_limits: {"light": 805306368, "native": 2684354560}`，其中 `limit_bytes`
等於 native 上限。所有階段都核對實際整個 systemd unit 的 memory/swap 上限，
並保留至少 2 GiB 主機餘量。組裝／來源檢查在 light 上限內運行；只有取得 lease
且正式服已正常停止後才提高至 native 上限。首次載入／重啟共用該上限；完成後
先有界回收測試留下的 file cache，再確認較低上限生效，才能啟動 LIVE。
缺餘量、無法安全收縮或任何身分／限制讀回不符都停止流程，不能調低餘量放行。
分階段預算只抵扣 `memory.stat anon` 中已由本 unit 佔用的 resident 記憶體，
最多抵扣 `memory.current`，並另扣除 32 MiB 計帳餘量；file cache、shmem 與
kernel 不抵扣。所需空間仍是剩餘受限預算加至少 2 GiB，不把同一匿名頁重複預留。

正常停服後，若原生記憶體准入失敗且尚未建立 snapshot、演練、安裝或遷移，
可用 `recover-preinstall --execute` 關閉這一次未改包／DB 的自有失敗交易。
恢復專用設定與原 immutable 設定只能差在 memory unit 及 `recovery_original_config`。
入口核對原始失敗、正常 stop、完整 inventory／policy／來源及缺席的後繼標記，
追加 `preinstall-abort.json` 後關閉本次 lease；不啟動或還原任何 runtime／DB。
新候選可用 `preinstall_recovery_output` 引用該交易，驗證精確 closed lease、
目前 STOPPED 狀態與未變的包／policy／停服 DB，接續正常整批流程。
原失敗與收據不改寫，原 idle-owner 的 hash 也不重設來掩蓋維護來源。

乾淨新世界的原生載入失敗、但尚未安裝時，也使用同一個
`recover-preinstall --execute` 入口。它要求原生程序已正常退出且沒有玩家、
指令或測試 overlay；正式新世界目錄與安裝／准入標記均不存在。
工具核對舊世界及一致停服備份逐檔相同、正式包／policy／設定未變，
並重用原 fresh-world 交接的 API、程序及 current selector 檢查。
追加中止證據後，僅交回 capture 與交接記錄共同綁定的原 completed lease；
失敗候選不標成 completed，原失敗、QA 與備份保持原狀。
這項操作不批准原有漂移、不啟服，也不改包或世界。

一般更新要求 UUID 不變。已提交的 Cookery 1.0.8→1.6.0 作者身份遷移可用 `identity_migration` 指向 canonical `family/identity-migrations/cookery-108-to-160.json`；工具限制原／新作者 UUID、版本、archive 與原 manifest，先在本次停服副本逐筆搬移所有權並演練，再採用未受 QA 引擎修改的資料庫。其他身份遷移仍須另行設計與審查。

遷移使用 little-endian NBT 的無損字串編解碼，保留 actor `StorageKey` 等以 TAG_String 儲存的二進位資料。每個 root 在修改前須能逐 byte 往返；重複欄位、截斷資料或無法原樣編碼的值會拒絕，不以替代字元修補。這只保護後續遷移，不會自動恢復既已損壞的 actor 或索引。
私人 extension 如果有 runtime 變動，也須補它自己的功能證據，不能用三個公開 PR 代替。

## 保持驗收誠實

成功部署狀態仍是 `pending_client_acceptance`，`client=false`、`production_ready=false`。
沒有模擬玩家；沒有把原生載入、API accepted 次數或腳本 double 當成 Windows 渲染驗收。
完成的人工作業、版本及結果應另行記錄，不修改本次未經真人測試的原始報告。

## 已審查的下一版保留包

`prospective_preserved_inputs` 可引用 Git 外的審查 JSON，將四個已安裝的保留包
換成 canonical extension recipe 的下一版輸出。它不是 live 漂移核准：目前所有
identity、逐檔內容及順序仍須先與現行准入一致，禁止新增或替换 UUID。
四個輸出須是兩組版本與相依同步的 BP/RP，保留 module UUID/type；來源目錄
不能與 live、來源 Git 或候選重疊，不能使用 symlink／hardlink。

審查記錄包含 `schema: 1`、`source_commit`、`recipe` 的相對路徑與摘要、
`native_validation` 的絕對路徑與摘要，以及按 recipe output name 對應的
`packs: {name: {path, uuid}}`。來源須為乾淨 canonical extension，recipe 必須
已提交。`extension_validation` 必須指向同一份實際原生保存／功能證據；
四個完整輸出都要與該次原生測試收據相同，缺少或不同證據時拒絕組裝。

此模式不與保留舊 source、部署 hold、preserved reconciliation 或 additions
併用。家族組裝器記錄原樣的 preserved ownership，另記 recipe／Native 來源；
cache 重驗全部輸入及證據。整套 static、BDS、fresh saved-world、備份與
family_guard 仍須完成，真人驗收狀態仍保留 pending。

原生證據的實測提交保持原樣。現行 source HEAD 不同時，僅允許它是實測提交的
後代，且**完整 Git tree 完全相同**；只看 runtime 版本或輸出 hash 相同仍拒絕。
准入記錄分別保存現行提交、實測提交及兩個 tree OID，不重寫原證據冒充新測試。

`senluo-client-assets-20261019-p58` 只接受現行准入的 AMW29／Fishing120
兩組既有 UUID，輸出配對版本分別為 2.6.10058／1.2.10058。
private reviewed integration recipe 綁定 R5 收據、四包完整輸入／輸出檔案清單及限定差異：
AMW 的舊 textures 定義、Fishing 水粒子五個呼叫來源與 helper、魚缸材質、
156 個既有 item texture set 的 normal 與 156 張新 normal、三份翻譯斷行及配對身份。
其餘保留包須與原准入完全相同；不恢復退休內容、不核准安裝漂移。

此 profile 的 `source_validation` 指向 `client_assets_source` wrapper，內含
private merged PR、完整 source tree、`differential` 和 `ci: {run_id, artifact_id}`。
工具從 canonical main 的成功 CI 下載原始 `client-assets-functional` artifact，
核對 ZIP digest、report／log 原 bytes、source recipe 與功能事實。
這份 source-only 證據先允許選取下一版輸入；隨後仍只使用本次正常停服副本的
first／restart 產生 `client-assets-native-validation.json`，才能安裝。
`current-author-p58` 同時驗證既有作者與 private reviewed integration 的完整輸出鏈；
source／native 成功均不提升真人畫面驗收或 `production_ready`。

## 驗證與維護

`python -m unittest discover -s tools/family_update -p 'test_*.py'` 使用隔離暫存目錄
及替代的 BSM／程序介面，檢查恢復、hash 漂移、必要 CI、路徑綁定、no-op 和 resume。
測試不啟動 Minecraft，也不接觸 live。

組裝器在單次 build 中只索引每份 upstream archive 一次，使用時重新核對選中 bytes，
不永久相信檔名快取。复制後已驗證的檔案清單可在同一階段重用；停服、安裝、啟動等
狀態邊界的檔案檢查仍保留。

### 合併期間來源前進

當另一個已審查 PR 在合併前進入 base，PR head 的完整 tree 可能不等於最後的
canonical merge tree。此時僅接受「該 PR 的實際 merge commit 就是目前 canonical
commit」且完整 tree 相同的情況；檢查改查該 merge commit 的實際 GitHub CI。
必要 runtime jobs 必須對此完整來源成功，不能沿用舊 head 的綠燈。收據分別記錄
reviewed PR head、checked commit 與 tree。其他後續來源仍要求自己的目前 merged PR。

### 保留並審查另一項正在進行的修復

既有 preserved pack 與旧收據不同時，仍拒絕漂移。`preserved_reconciliation` 可引用
Git 外的獨立審查證據，目前僅支援既有 AMW 2.4.18→2.4.19 的果汁桶、小麥配方／
指引及配對 manifest。必須保留完整原始與目前 bytes 於乾淨 private Git；原始 tree
逐檔等於不可變舊收據，目前 tree 逐檔等於 observed inventory，每條差異記錄原因。
還需該完整候選在原生 BDS 首次與重啟的果汁堆疊、配方、六級成品測試，且不得
以 probe 修改被審查的 AMW bytes。未找到原始編輯者時，來源記錄必須明說。

此審查只讓新候選保留已核對的變更；不改舊政策、收據或驗收結果，也不能用來
引入自有包 gameplay、別的 preserved pack、額外檔案或身份遷移。完整家族准入、
新停服備份和存檔演練仍必須完成。整合包僅允許與此已審查 pair 精確同步相依。
翻譯審查的 `canonical_preserved_commit` 只引用 separately validated integration
的精確 history preimage，保留已觀察內容；後續 canonical 功能變更另外通過
`extension_validation` 的全檔與原生功能驗證，不能偽裝成翻譯修補。
# Reviewing an unrelated pack already added to live

`preserved_additions` may name a schema-1 JSON review with `source_provenance`,
`review_reason`, the exact `observed_inventory` and a `packs` map keyed by each
new UUID. Every entry records a review `reason` and the original single-pack
`artifact` (`path`, `sha256`). This is an explicit source review for assembly,
not approval of the old stack. The tool requires the observed pack to match
every original archive file, retains all previous identities and their relative
order, and still rejects existing gameplay drift. Managed UUIDs cannot use it.
Archives and review inputs are frozen at the build boundary. The new complete
candidate must pass normal static, native, fresh stopped-world and guard gates;
the original policy and live files remain unchanged until authorized deployment.

## 其他自有包的完成門檻

來源更新與部署可分開：`upstream.lock.json`的owned保留最新已審查來源，例如Grilling2.8.73；`deployment_holds`明列使用者完成門檻文件、已合併canonical commit、舊版／tree及candidate版。需要保留時，設定`held_sources: ["grilling"]`，該sources路徑使用指定commit的乾淨隔離Git checkout，不回退canonical main。此功能不能用來安裝歷史artifact、改玩法或自動降級。

source_state核對宣告／committed門檻文件、held版本／trees／commit、正確canonical remote及main ancestry。完整家族仍由family_bundle組裝，已保留BP/RP的版本及每個檔案必須等於本次live capture，任一側缺失、內容漂移、新UUID或版本不同都拒絕。CI驗證使用該已合併held來源的真實PR；static/BDS/fresh saved-world／准入／備份／回退／readback全部保留。候選收據明列held_revision，latest來源鎖不改成較舊來源。別包完成門檻不因本輪酒館／世界名酒修復而自動撤銷。

### Reuse unchanged Tavern gameplay CI after a family-only PR

An already stopped server is deployable only with an explicit
`normal_idle_update: "/absolute/path/to/review.json"` for the
`canonical-normal-idle-v1` owner contract. This is separate from managed drift
and preinstall recovery. The review pins the fixed canonical idle implementation,
its protected configuration, the last completed deployment/config/lease/receipt,
installed policy, stopped log and normalized successful sleep task. Fresh BSM
STOPPED/zero-player status, confirmed task success, no matching BDS process and
unchanged owner inputs are checked before and after acquiring the new lease.
Routine timer timestamps are excluded from immutable build inputs; the exact
sleep identity remains pinned. Manual, unknown, stale or failed stops reject.
The update takes its consistent stopped backup directly, then runs the same
saved-world first-load/restart, admission and candidate start. It does not start
the old runtime to satisfy a preflight condition. Any transaction failure keeps
the newest database, displaced files and active lease stopped for explicit
recovery, including partial installation; it never restarts the original stack.

When a new Tavern runtime has already passed its complete CI, a later family
lock/maintenance PR legitimately skips gameplay jobs. The current full source
still needs its own merged PR and successful `impact`/`baseline`; skipped jobs
are never relabelled as success. Local config may additionally declare
`runtime_ci_pull_requests: {"tavern": <merged runtime PR>}`.

The update entry records both actual GitHub check revisions separately. The
runtime merge must be an ancestor of current canonical source. Own runtime
Git trees, baseline and the impact classifier must be identical. Every later
path must be classified as family tooling/data or prose by the unchanged
classifier; runtime, fixture, general build or unknown inputs reject reuse.
All required gameplay checks must actually succeed on the retained runtime
revision. Current metadata checks cannot be satisfied by those older results.
The conservation proof is rechecked when cached evidence is used. Other public
sources retain the existing exact-tree CI rule. Full family static/native,
fresh stopped backup/saved-world and admission/readback gates remain required.

Historical approved-runtime retention validates reused CI against the immutable
admitted rows already bound by checked receipt references, rather than the
next deployment's configuration. Conservation reads that retained source's
Git baseline. Current evidence separately records its configured runtime CI
references and refuses cached references from a different configuration.

### 固定 Ribbits 啟動來源

`senluo-ribbits-startup-20261013` 只選已准入 Ribbits1.0.10 的完整 BP/RP
原像及私有 canonical compiler 的配對1.0.10036輸出。只允許既有
`scripts/main.js` 的已審初始化修正與兩側生成 manifest；所有結構、玩法、
資產及此前私服差異保留。原混合 module version 按各自原像核對後同步。

private-integration本身輸出不變，不為 companion compiler 來源前進升其包。
新的實際私有 PR／CI、完整 Git tree、原報告／TAP與固定 recipe 全檔綁定
仍必須成功；不是重用舊cache或HUD的source報告。設定不要沿用
`extension_cache_validation`：沒有新的cache改動就不產生或偽造新的cache報告。

本候選仍經完整家族 static、停服一致備份及同一存檔副本 first／restart，
之後寫獨立 `ribbits-startup-native-validation.json` 才允許安裝。
來源計數29,635→158及序列相等不代表引擎減時；未知結構／尺寸／連接表維持
原掃描，外部同名結構替換與真人結果另列。此模式不批准安裝漂移，不放寬
既有五包HUD或四包native准入規則。

### 部署中的遠端合併

新部署開始與停服前仍要求 canonical main 等於遠端。取得本候選 maintenance lease
後，內部 saved-world／verify-live 入口核對已捕獲的精確 source、runner 與 config；
另一個遠端 PR 的合併不再使已安裝的健康候選回退。沒有本候選的 active lease、
本機來源／工具／設定變動仍拒絕；完整候選、保存、准入與實際啟動檢查保持不變。

### Ribbits FP 解壓接續修補

`senluo-ribbits-fp-decode-20261013` 從已准入1.0.10036完整輸出生成
1.0.10037配對。只改同步FP解壓呼叫與配對manifest，保留存檔格式、
原解壓fallback及所有其他內容。准入另核對上一版recipe與輸入逐檔相等、
新私有PR完整tree／實際CI、UTF16與異常輸入差分報告；舊啟動profile
繼續按原規則驗證。reviewed integration不升包，完整家族停服存檔演練與安裝門檻維持。

### reviewed integration 性能修補准入

reviewed integration→reviewed integration freezer helper 與 Saturation1.5.5→1.5.6 使用各自的精確來源
profile；設定、三個 CI artifact、作者檔案邊界及同次存檔原生綁定見
[性能來源 profiles](PERFORMANCE-SOURCE-PROFILES-20261015.md)。舊 HUD 與
Ribbits profile 規則保持；來源測試不計為真人驗收。

### reviewed integration 穩定作者與飽和度相容宣告

`extension_stable_validation` 使用 `senluo-stable-author-20261017-p46`，綁定
私有 reviewed integration 完整來源樹、已合併來源 PR 及該 main 的原始八份功能 CI 檔案。
新的 Sat `1.6.10046` 配對由 `senluo-stable-saturation-20261017-p46` recipe
核對；除了既有 HUD／程式逐檔守恆，還須保留已准入 `1.5.6` RP 的 `pbr`
capability。乾淨作者 `1.6` 沒有此宣告，不能直接當成本機 stack 的相容輸出。
准入在實際新舊 manifest 邊界核對已提交的原始 manifest、capabilities 與
兩側版本／相依；缺少宣告的 reviewed integration 靜態失敗與原證據保留，不改政策或舊輸出。
reviewed integration 仍須通過完整家族靜態門檻及同次停服副本的首次／重啟，真人驗收另記。
