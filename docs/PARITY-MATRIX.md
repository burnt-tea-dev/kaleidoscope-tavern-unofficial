## Current upstream review — 2026-10-27

Adopt the official Bedrock Tavern1.0.7 unique-reference rule. Preserve the current shared seven-section guide. Monitor official owned-port counterparts and adapted Fishing source with pinned author IDs; recognize the selected world after a completed fresh deployment. See [the source review](../family/bedrock-upstream-review-20261027.json). Historical sections below retain their original source and test scope.

# Tavern Java／Bedrock 差距矩陣

目前維護版本與 BP／RP 身分以 [baseline.json](../baseline.json) 為準；公開下載、來源配對及部署見[家族現況](../family/BASELINE-STATUS.md)。下列日期段保留各次修補及原始證據範圍，不因較新的來源版本自動取得畫面或完整家族通過結果。真人使用不是發布、部署或完成門檻，沿用[擁有者現行規則](../family/UPDATE-WORKFLOW.md#擁有者簡化規則2026-11-04)。

## 香薰先傷害再判斷治療（2026-11-05）

Forge `c4ec1880`、NeoForge `a1afba34` 的 `IncenseBlockEntity.serverTick`先選活著的亡靈，造成1點magic傷害，再按傷害後的生命判斷殭屍村民治療；沒有按`hurt`回傳值跳過後續判斷。原Bedrock在生命<=1時直接治療並return，導致1點生命及仍有效的死亡actor跳過傷害，也沒有排除死亡目標。

現在保留原有查詢範圍、開關、120tick脈衝、原生治療事件與防重入標記，只修目標存活判斷和傷害／治療順序。[真實註冊tick回歸](../tools/incense-damage-order.test.mjs)重現修前的1點生命／死亡目標失敗，並驗證2→1生命後治療及傷害拒絕後的判斷順序。這些是腳本與API double證據，不是原生完成治療證據。

[窄原生觀察器](../tools/native/incense-damage-order.js)沿同一QA場景，使用真擺放香薰、原生1／2生命目標與magic死亡事件，追蹤真正村民生成及期間生命；另以獨立目標在治療開始30ticks後受一次外來傷害，區分原生傷害與Tavern標記的早退。T202完整觀察與實際時長見下方；該輪未改原版生物定義，沒有手工生成村民取代原目標。

2026-11-06唯讀核對：兩個Java版本的原版`ZombieVillager.startConverting(UUID,int)`都直接保存傳入倒數，活著且正在轉化時每tick扣`getConversionProgress()`，到期才呼叫原版finishConversion。一般進度為1，附近鐵欄杆／床可加速；酒館兩分支都傳60。`IncenseBlockEntity`沒有按isConverting跳過hurt；這不代表每次hurt都會扣血，原版傷害冷卻仍有效。T202的curing標記則直接跳過後續香薰傷害，尚不能當作Java固有的轉化免疫。

所選BDS1.26.60.6安裝內有不同原版定義，不能只看一份舊JSON推斷實際載入：

| 原版路徑／群組 | 靜態設定 | 適用範圍 |
| --- | --- | --- |
| `behavior_packs/vanilla/entities/zombie_villager{,_v2}.json`／`to_villager` | delay.value100，strength/heal100秒 | base定義，未冒稱目前選中 |
| `behavior_packs/vanilla_1.26.20/entities/zombie_villager_v2.json`／`to_villager` | value100＋range_min80／range_max200；strength/heal300秒，drop_equipment=true | 1.26.20定義；按[官方delay單位與範圍](https://learn.microsoft.com/en-us/minecraft/creator/reference/content/entityreference/examples/entitycomponents/minecraftcomponent_transformation?view=minecraft-bedrock-stable)為180..300秒；下方真入口實測285秒在此範圍內 |

`villager_converted`只加入上述群組。官方[資料事件](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/datadrivenentitytriggerafterevent?view=minecraft-bedrock-stable)可記錄開始；[原生Transformed生成事件](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/entityinitializationcause?view=minecraft-bedrock-stable)及實際Villager類型才作完成證據。觀察器同時記錄首次shaking、60tick／後續里程碑、生命變化和QA名稱／動態資料保留；事件未報錯或原handle消失均不算完成。2.12.0-beta型別及官方experimental元件表未見轉化／timer寫入入口；這是靜態能力核對，並非所有API版本的原生否定結論，觀察器另讀選定引擎實際元件形狀。

沿原窄執行器使用`--phases first --timeout-seconds 420`，預設仍180秒。這次香薰可不傳`--liquor`、只載入凍結T202 BP/RP，避免混入仍精確依賴T201的W191；實驗設定仍由來源config及原QA metadata保留。正常stop／來源逐檔核對不變。本次只改QA／執行器／證據，不回寫T202身份或重跑其來源回歸。

**2026-11-06實測，BDS1.26.60.6／server2.7.0／T202單獨QA／零玩家**：[完整結果](../data/native-incense-conversion-20261106.json)、[裁剪原始log](evidence/native-incense-conversion-20261106.log)。public zombie_villager在tick26原生解析為v2；真香薰在tick130呼叫原生villager_converted，tick131看見shaking。1hp目標tick130死於magic；survivor受傷2→1hp，在+60、+120、+2000、+3600仍未完成，期間只有初次香薰hurt。獨立control在+30外來magic1令1→0並死亡，因此不是原生全傷害免疫。tick5830真正出現villager_v2，原生Transformed生成／entity_transformed亦同tick；**5700ticks＝285秒**，javaDelayMatches=false。首次生成讀回有名稱、沒有QA tag／DP marker；本輪沒有下一tick／保存後讀回，不據此宣稱永久遺失或所有metadata等價。

本輪normal_stop=true／引擎exit0／Quit correctly、errors空、players0、SwapPeak0、peak786837504 bytes。wrapper exit1來自已完成觀察但Java時長不符的partial，不是服務崩潰。完整log、report及實際observer留在既有主機證據；QA世界／引擎連結已清理，沒有重啟或第二世界。

能力邊界：原生timer／transformation在事件tick130讀值未暴露，但同tick的is_shaking也尚未套用、下一tick才出現；不能把這次事件階段讀值說成active狀態的API否定。現在沒有已驗證可縮至60tick且保留資料的原生入口，仍未完成。後續由下節 owned 原生 group／event 繼續，需再測真完成與資料保留；這次 API 讀值不能證明原生定義無法實現。

本輪observer輸入固定為e17b3b44。由實際log確認原生Spawn／Transformed通知晚於首次類型讀回，後續observer已補active-shaking時的元件讀取、完成後兩tick的metadata再讀，並保留首次完成tick；這些補讀尚未在BDS執行，不冒充本輪已驗欄位。等下一次確有必要的原生觀察一併補證，不重跑285秒等待來製造相同結論。

## 香薰專用原生轉換（2026-11-06）

T202真入口需285秒，Java兩分支傳60tick。腳本API沒有已驗證的轉換倒數寫入入口；現在改由Tavern擁有的原生事件處理。這是新來源行為，不回寫T202的歷史身份或上述實測結果。

Tavern BP會接管 `minecraft:zombie_villager` 及 `minecraft:zombie_villager_v2` 兩份完整定義。[所選官方來源與授權](../art/native-incense/README.md)對應BDS1.26.60.6安裝中最後版本；[生成器](../tools/build_incense_native_entities.py)保留全部原版欄位，只各新增一個香薰group及event。新group複用原生transformation，delay.value=3秒，移除該副本的隨機範圍，保留床／鐵欄杆加速、原生轉換與資料處理。原金蘋果 `to_villager`／`villager_converted` 不改；新event先移除舊／新轉換group再加入owned group，以便香薰再次要求治療時重設倒數。沒有手工spawn村民或搬運交易資料。

腳本改呼叫 `kaleidoscope_tavern:incense_cure`，同時移除curing-tag寫入與兩處早退；受後續香薰影響時，照常先傷害，再判斷存活及生命。舊存檔已有標記也不阻擋傷害，無需掃描清除或維護per-ID名冊。原生舊group仍保留，沒有被香薰再次命中的既有轉換繼續原本流程。

[腳本回歸](../tools/incense-damage-order.test.mjs)仍呼叫實際註冊onTick；新增第二香薰相隔15tick傷害curing actor，以及舊保存標記不阻擋傷害／治療的反例。修前6項有4項失敗，修後6項通過。[原生定義來源檢查](../tools/test_incense_native_entities.py)直接比較生成物，刪去owned新增必須還原整份原版；只允許新副本的delay差異。這兩類檢查未執行BDS，不把JSON的3秒寫成實測60tick。

[同一窄觀察器](../tools/native/incense-damage-order.js)已改追新事件，追蹤真香薰1hp／2hp、原生Villager與Transformed完成tick、外來傷害、轉換中重設，以及同世界正常停服／重啟後的轉換與已完成村民欄位。它保留首次完成tick，讀active元件及完成後metadata。新來源原生結果見下方；保存／交易及實際聲畫不能由來源檢查宣稱完整等價。原版strength／heal等附帶設定完整保留。

**T203實測（2026-11-06，BDS1.26.60.6／server2.7.0）**：[原始結果與範圍](../data/native-incense-203-20261106.json)、[裁剪原始log](evidence/native-incense-203-20261106.log)。真香薰要求tick135，真正villager_v2與原生Transformed於tick195，**60tick**。重設control於135／155兩次要求，tick215完成，從第二次要求再算**60tick**。1hp目標被magic殺死，2hp目標傷至1hp後完成；獨立外傷control在+30死亡。完成後strength已無；所觀察名稱、variant與skinId保留，QA tag／自訂DP marker未保留，不宣稱任意metadata／交易／裝備全部等價。

公開zombie生成、from_village及原生villager zombification三條入口均實際變成v2，因此只確認v2，不能稱兩個native類型均通過。first的partial來自bothNativeTypes=false，不代表真60tick／reset未通過。

**舊v1邊界已收斂（2026-11-06）**：[來源與窄原生結果](../data/native-incense-v1-boundary-20261106.json)／[observer](../tools/native/incense-v1-boundary.js)。v1所選原版仍宣告spawn/summon，正式owner也接受該ID；原T203 early spawn記錄其實在tick25見真v1、26即原生升v2。新場景僅在生成當tick手動呼叫canonical註冊factory的真正onTick，block／actor／time／資料都是真原生；這不證原生Block自然派發順序。tick120的owned CURE事件真命中v1，到122封閉場景已是v2新actor，因此partial立即正常停，不再量v2、reset或保存重啟。不能宣稱v1的60tick／reset／保存通過，也不能據此判v1 event/timer失效。

本次現代QA配置與已查三條入口的「穩定舊v1待驗」收斂為正常類型升級邊界，不設永久兼容待辦、不改runtime或升T。歷史template中保留v1的配置未測，本輪不引入這類世界。生成器仍保留原生差異：v1目標villager、未帶v2的keep_level/drop_equipment。實讀升級後保留名稱，QA tags／三個DP不在新actor；health／variant也改變，這些是native升級讀值，不是香薰完成或存檔後比較。裝備／交易未暴露，沒有mock補值或任意Java data等價主張。

**保存終態讀回已確認；原失敗保留。** first正常停服前，另存一個已開始原生治療的actor及已完成村民。restart observer在worldLoad+1直接按已保存的completed ID查詢，沒有等待區塊／actor載入便報missing；這個結果尚未分辨載入時序與真缺失。稍後同一原始restart log已記錄pending actor真正Transformed／villager_v2，所以它的舊pending ID不能當作仍未轉化重播。兩階段引擎均正常stop／Quit correctly、players0、errors空，wrapper exit1保留不完整觀察。

後續只沿同一停服QA驗剩餘保存讀回：[observer](../tools/native/incense-damage-order.js)先等區塊與原completed saved ID，不用名稱fallback掩蓋缺失；pending已完成時只驗穩定終態，不聲稱這次又見治療。既有runner的 `--resume --phases restart` 只替換明列QA觀察器，先確認原runtime及舊overlay未變，保留原世界／原報告／兩份log，新結果另存；不重跑已通過的first60tick／reset，也不重建世界。[PR571](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/pull/571)工具／證據已正常CI合併，T203 runtime不變。其後沿同一世界只續restart：tick262開始等，tick265在chunk／actor載入後，以原saved ID `-4294967254`找回同一完成村民，全部已記錄欄位一致；未用名稱fallback。原pending已是前次restart生成的 `-8589934591`，本次只確認名稱、variant7、skin0等穩定終態，nativeTransformationThisRun=false，沒有再跑治療。這分辨了原missing為過早讀取，不是已保存actor永久遺失。resume normal_stop=true／Quit correctly、players0、errors空、wrapper exit0；原first partial與restart failure未改寫，不能據此宣稱雙native類型或任意DP／交易／裝備等價。精確停服剩餘倒數與聲畫仍未量測。QA世界／複製引擎資料／engine links已清理，只留小型原始證據，共用槽已交還，不再重跑成功案例。

當前P131載入的32個BP按identifier核對，沒有其他包定義這兩種生物；這只適用該觀察輸入。下一個實際候選須核對同identifier的選定owner。未來採用新版BDS時要重看這兩份所選原版；沒有新增包組合特例或通用合併框架。

## 多包飲酒效果的共用容量（2026-11-05）

Java 1.2.0 Forge `c4ec1880`、NeoForge `a1afba34` 的 `DrinkBlockItem` 逐筆呼叫 `LivingEntity.addEffect`，沒有酒館自設的共用32筆門檻。T200的保存與加入入口卻把所有附加包、不同等級的效果列合計限制32筆。以現有World Liquor0.1.189酒瓶及Tavern酒瓶走真實完成入口、每瓶相隔32ticks，固定合法隨機值0，第52瓶六級螢光花釀的Vision被拒絕，但酒仍被正常結算。這是來源callback重現，不是原生玩家飲用證據。

現在移除該共用筆數門檻，仍驗證每筆效果、時間、等級及遷移欄位；保存格式／鍵不變，由原生動態屬性的容量限制最終寫入。相同飲用序列修後由32筆增為33筆，沒有效果拒絕。[正常PR回歸](../tools/custom-effect-capacity.test.mjs)另以兩個正式註冊descriptor驗證完成飲用、強弱效果、跨handle保存讀取／倒數／清除與錯誤資料拒絕，不依賴特定包組合。

[隔離保存觀察器](../tools/native/custom-effect-capacity.js)只測原生實體屬性的35筆寫入、同世界重啟及清除，結果隨共同候選另記；未宣稱已部署。SDK按單一addon接收的快照仍有既有32列組裝上限，本次未修改；此修復不等於所有自訂效果數量或客戶端顯示都不受限制。已測裝備／target API限制維持下文結論。

## 分段效果快照的組裝容量（2026-11-05）

有界核對：目前W189註冊16種timed效果，酒瓶／雞尾酒及shakerInputs共31種effect ID＋amplifier組合；調酒只取既有最高等級，不創造更高等級。因此一般catalog未找到>32列的反例。讀取LIVE載入的32個BP入口，只見T200傳送端與W188消費端使用這條快照；未執行LIVE探針。

但既有Server `effect_apply`入口對已註冊效果接受amp0..255，未限制為catalog等級。以現有W `continuous_heal`的amp0..32送33個合法申請，宿主保存33列，SDK卻把每段32列的界線誤用到整份組裝結果；原快照過期後，W行為讀者得到空白，並非只少最後一筆。[回歸](../tools/effect-snapshot-capacity.test.mjs)呼叫實際申請訂閱、publisher及SDK讀者，沒有捏造33種新效果或把普通酒品宣稱為觸發入口。

SDK現在接受已通過逐段驗證的完整快照；每段32列、最多8段、訊息大小、欄位、來源及20tick新鮮度驗證維持。傳送端仍保留後備等級，消費端沿既有規則選最高amp／相同等級較長時間，因此強效果在兩次發布之間到期時，仍可立即接替有效弱效果，不改遊戲時序。單純刪掉後備傳輸會造成延遲，不採用此路線。

此修復在Tavern SDK來源，未改T201 BP／RP及其身份，無需另造Tavern遊戲包。World Liquor內嵌SDK須由其canonical來源更新並產生新的W配對身份後才會生效；LIVE或固定候選不因SDK模板合併自動改變。超過既有分段／訊息容量仍是能力上限，本次不新增框架或無限擴容。

## 活體特殊效果入口（2026-11-05）

對照發布版 Java 1.2.0 的 Forge 1.20.1 `c4ec1880` 及 NeoForge 1.21.1 `a1afba34`：`EffectEvent.onLivingHurt` 的摸金校尉來源是 LivingEntity，`VisionEffect.applyEffectTick` 也接受 LivingEntity。先前 Bedrock 的這兩種效果入口只接受玩家；瓶裝感知酒雖已能潑濺到生物，效果仍被入口拒絕。摸金校尉的活體效果入口與傷害回呼也有同樣限制。

來源已為非玩家活體接通摸金校尉和感知的保存及執行入口；感知沿剩餘時間每 50 ticks 脈衝。啟動時一次恢復已載入活體的資料，包括原生 `mob` 家族以外的魚類；之後沿 entityLoad 與既有活體時計處理，不逐 tick 掃全世界。保存格式與資料鍵不變。

來源回歸呼叫實際效果入口、卸裝、脈衝與載入事件，驗證武器 metadata、剩 1 耐久、40 ticks 拾取延遲、掉落失敗回裝、到期及卸載時間暫停，見 [java-parity-adapter.test.mjs](../tools/java-parity-adapter.test.mjs) 與 [vision-feedback-adapter.test.mjs](../tools/vision-feedback-adapter.test.mjs)。感知仍使用現有偵測／聲音適配；穿牆輪廓沒有因此完成。摸金校尉仍是 Bedrock 傷害後事件，並非 Java 傷害前階段；實際聲畫與完整傷害時序不宣稱等價。原生檢查（2026-11-05，BDS 1.26.60.6、T200／W187、零玩家隔離世界）：魚類感知完成首次兩次脈衝、保存重啟自動恢復，重啟後計時 5832 → 5822。殭屍沒有公開的 `minecraft:equippable`，所以摸金校尉的原生卸裝仍未通過；同引擎的 SDK 2.7.0、2.11.0、2.12.0-beta 對殭屍、骷髏、盔甲座及豬，在生成當下及五 ticks 後都沒有該元件。這只描述本次版本與生物，不推論其他版本永久不支援。

隔離觀察器 [living-effects-capability.js](../tools/native/living-effects-capability.js) 會分別報告感知與摸金校尉。缺少裝備元件時仍跑完感知與重啟，總結果保持 `partial`，執行器回傳失敗；不再因裝備 fixture 的 TypeError 遮住另一項結果。正式 runtime 未改。

2026-11-06 另核有資料層裝備欄的真原版羊駝：最高內建 `vanilla_1.26.30/entities/llama.json` 的 equippable 只在原生 tamed group，slot1接受carpet；舊測試未涵蓋它。[窄原生結果](../data/native-llama-equippable-20261106.json)／[observer](../tools/native/llama-equippable-capability.js)：BDS1.26.60.6／server2.7，生成→既有on_tame→5tick後同actor，is_tamed與inventory已出現，但getComponents、enum與literal getComponent都無equippable。資料層同名元件不等於Script可讀裝備；關閉本引擎／API的這條羊駝入口，不推論其他版本。首輪observer方法名錯誤保留為失敗，不算API陰性；沒有新Player／其他mob／三API重跑／vanilla覆寫／升T。

## 龍頭完成時的來源（2026-11-05）

Java 1.2.0 Forge `c4ec1880`、NeoForge `a1afba34` 的 `TapBlock.tick` 在完成時重新讀取目前來源、重選 `TapBehaviorManager`，並由該來源決定產物。先前 Bedrock 把開啟時的來源種類保留在 session，水鍋在 30 ticks 內換成西瓜後仍按舊水鍋完成，結果只關閉龍頭、不產生西瓜汁。

現在開啟與完成共用當前來源選擇，session 只保留計時、取消及原本是否正在取液的狀態。水鍋／西瓜／酒桶間切換在完成時使用目前的交易，不扣舊酒桶存量。西瓜照原作保留；蜂巢等來源仍用各自原有耗材規則。30 ticks、原本空轉、手動取消、無效來源及交易回滾維持，保存格式與鍵不變。

[tap-regression.test.mjs](../tools/tap/tap-regression.test.mjs) 已改用真實 `tap-sources` 交易，經實際開啟／計時完成入口重現修前失敗，再驗證換來源、無效來源、空轉、取消及原有 carrier／metadata／回滾。這些回歸已接入正常 PR 的 mechanics job。引擎與保存結果由 [隔離觀察模組](../tools/native/tap-source-swap-capability.js) 記錄，不以來源測試宣稱原生或 LIVE 通過；前批 T199 的部署輸入保持固定。

## T182 指南設定導航來源（2026-10-25）

取消設定視窗會返回相同指南，既有 session 若已清除則仍退出；取消不寫入偏好，也不提前觸發返回 Cookery。首頁設定按鈕顯示實際使用的語言名稱，與既有三語選單共用字串。七大內容入口、Cookery 臨時語言優先、原玩家／世界資料鍵及 Java 玩法／音效保持。這是獨立吸收介面設計，沒有複製第三方腳本，也未新增 29 語、維度音效／粒子設定或蹲下放置選項。現有 controller／偏好定向測試通過；完整家族保存／BDS、實際畫面與操作仍待驗收，`client=false`、`production_ready=false`。詳見[本次吸收範圍](THIRD-PARTY-TAVERN-REVIEW.md)。以下保留原候選範圍。

## 2026-10-25 共用儲存穩定性修復來源

已重現並修正外部酒櫃相同失敗快照的 NACK 重送循環，以及同一原生容器暫不可用時展示維護的重讀循環。相同 payload 有界退避、正常位置繼續交接，原 actor 載入或來源 raw／ledger 改變後恢復；玩家操作與 native inventory／migration receipt／tombstone 的權威不變。來源／API 測試量得 60 次回呼中的相同失敗查詢由 30 次降至 2 次，完整 foundation 127 項通過。詳細行為及重現命令見 [共用底層](FOUNDATION-PHASE1.md)。尚未 freeze／發布／部署；不能據此稱正式存檔已恢復或 LIVE 卡頓已解決，真 carrier、保存／BDS 與 client gates 保持。

## 2026-10-24 T179 候選

普通冰在四個酒桶原料槽改用 Java 對應的半透明路由；packed／blue ice、其他原料、原圖與幾何保持。首次成功在線讀取建立效果時計，短時間登入／離線不再漏扣首個 heartbeat 前的在線時間。原生透明排序、光照與本候選完整家族／客戶端驗收仍未閉合。微醺視覺不在本輪範圍。下列日期段保留原有審查範圍。

T178完整CI曾拒絕空效果生物被重新加入時計索引，T179保留該失敗及凍結身份，僅對有剩餘entries建立新錨；既有Bloody Mary到期測試保持。

Java 的 [BarrelBlockEntityRender](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/a1afba34981a00e89d57130d3dc8f1e64f1820a2/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/BarrelBlockEntityRender.java#L130) 使用 fixed item renderer；匹配 Minecraft 1.21.1 client（SHA1 `30c73b1c5da787909b2f73340419fdf13b9def88`）的普通冰採 translucent item render，原圖全部像素 alpha=190。四槽材質選擇及 ice→sugar 切換由現行 generator 與 adapter 測試檢查，不再把這五個資源倒推成舊版本才比 hash。

時計的可見反例是：帶100 ticks效果登入，在4 ticks後離線，應保存96而不是100；重新登入不扣離線時間。情境測試從事件入口驗證持久化值、空效果recipient和後續API讀取，不綁內部Map。該效果模組的歷史逆向差異已退役；其他尚未整理的域仍有舊驗證債務，這次不宣稱全庫重構完成。發布包identity、release-history與存檔契約另行保留。

## 2026-10-17 修復狀態與後續承接

這份摘要始於 **T173**（[115942e5](https://github.com/casama233/kaleidoscope-tavern-unofficial/commit/115942e55e9946cfd257fbcdc41c849f75b77509)）；後續承接在下表明列。來源／下載／倉庫部署／驗收分別見[家族現況](../family/BASELINE-STATUS.md)。完整Java一比一與當前真人驗收未完成。

| 行為 | 已保留的來源修補 | 目前未閉合的部分 |
| --- | --- | --- |
| 動態物品側面／全物品手持 | T160側邊座標、面法線與UV；T170只正規化一條副手雪克杯算式 | [#288](https://github.com/casama233/kaleidoscope-tavern-unofficial/issues/288)：全物品逐項Blockbench FP／側面、各手與contexts；副手framing、掉落3D及實際材質／光照 |
| 特調RGB | source texel × cupRGB、六幀與10組render controllers已在目前source | [#287](https://github.com/casama233/kaleidoscope-tavern-unofficial/issues/287)：原生材質、透明、濾波／PBR與各視圖；舊flat-only說法只屬歷史 |
| 雪克杯HUD／手感 | T165座標、T166快取、T167游標插值、T169過期窗口已承接 | 最新進度條、快開／取消／換槽／取出、聲音與延遲仍需同候選正常操作結果 |
| HUD共存 | 既有三transport、自有namespace、原生root保存；T190跨維度+20／+40 tick有限refresh（來源） | [#285](https://github.com/casama233/kaleidoscope-tavern-unofficial/issues/285)：跨維度refresh的客戶端／真人驗收、長title ownership與foreign writer完整共存 |
| Tipsy／時計 | yaw只明確opt-in；T179已補首次在線讀取的效果時計並保留離線暫停 | [#286](https://github.com/casama233/kaleidoscope-tavern-unofficial/issues/286)：保留瞄準與原生手臂的純roll仍未實作；時計來源修補不代表相機視覺已完成 |
| 原生語義／儲存／板面 | 多輪item保存、dispatch、類別與source adapters保留 | [#98](https://github.com/casama233/kaleidoscope-tavern-unofficial/issues/98)：reach、清仇恨、step、XP、outline；任意三份裝飾非堆疊原料、多行editor、部分event／drop語義仍不完整 |
| 杯架／香薰／酒桶 | T156選取、T159交叉花葉／cutout、T173碰撞形狀已有來源修補 | 真實四向點選、原生接觸、透明／粒子、保存與聲畫仍按場景驗收 |

現有來源修補與「當前已經重现舊BUG」分開記錄。舊影片、失敗、native片段保持原候選；`client=false`、`production_ready=false`。調料瓶的runtime主線由Grilling [#168](https://github.com/casama233/kaleidoscope-grilling-unofficial/issues/168)持有。

## 歷史批次及詳細來源證據

下列各段保留其原版本與觀察範圍；所有「當前／本批」均指當時記錄，後續承接以本頁上方與家族索引為準。

## 歷史部署：T166／G142／W144／private-integration／Ribbits1.0.10037

2026-10-14 21:41:21 HKT完成42包家族部署。來源PR／完整CI、一次停服副本first／restart、准入與逐檔／順序讀回通過；六個公開包9349檔與本次收據及LIVE一致。正式版與精確來源見[現行基線](../family/BASELINE-STATUS.md)。`client=false`、`production_ready=false`、`pending_client_acceptance`。

| 範圍 | 已部署來源修補／現有觀察 | 尚未證實／未完成 |
| --- | --- | --- |
| 調酒與進食圖形 | 原生事件接收、共同宿主／過濾、Java錨點與圖形裁剪已承接；76251可見色塊且無內部碼。 | T163／G138／private-integration仍失敗的截圖保留；不能將後續單張可見畫面當成完整場景通過。 |
| 位置與時計 | T165恢復中央相對座標；G141依剩餘use ticks計算並立即發首幀；原有食用／調酒結算不變。 | 新版真人位置／進度同步、各GUI比例及聲畫待確認；游標partial-tick插值仍未完成。 |
| 雪克杯處理成本 | T166僅快取閒置預覽，資料／目標／手持變更即失效，上限128；活動進度與權威交易不讀快取。 | 未取得新版端到端延遲或FPS數據；Poststart214 warnings／0 errors、187 watchdog並非性能改善證明。 |
| 進食與相容 | 原生使用入口、AMW／Saturation控制保留；76212／76213可見進食姿勢與數量下降。 | 完整進食／取消／換槽、29通道與普通提示同時存在、各裝置皆正常仍待確認。 |

完整[客戶端回饋](BUGS.md)及[驗收邊界](HUD-COMPAT-CLIENT-HANDOFF-20261012.md)保留原始失敗；本次只同步Git狀態，沒有升包或重啟LIVE。

## 歷史部署：T155／G133／W132／private-integration／Ribbits1.0.10037

[private deployment time]完成42包家族部署，BDS1.26.52.3 RUNNING；來源PR／必要CI、static、一次停服存檔first／restart、准入與完整讀回通過。[本次來源、限制與公開比對](../family/PUBLIC-DOWNLOAD-LIVE-PERSISTENT-HUD-20261013.md)：三公開archive均匿名下載，六自有包9346檔與LIVE及准入收據相等。

進食／調酒已改常駐通道接收器，移除調酒progress父層舊文字條件，原圖及玩法保留；[修補範圍](RELEASE-NOTES-0.6.155.md)。來源可見條件測試不等於客戶端渲染，真人恢復與游標partial-tick插值仍待完成。`client=false`、`production_ready=false`、`pending_client_acceptance`。

Poststart165 warnings／0 errors，watchdog138（9 Spike／129 Slowdown），Ribbits252ms仍有尖峰。保存玩家記錄（數量未公開）與容器（數量未公開）通過。未宣稱整體效能或完整Java一比一；以下歷史紀錄保留原版本與範圍。

## 歷史部署：T151／G130／W128／private-integration／Ribbits1.0.10036

[private deployment time]完成42包家族部署，BDS1.26.52.3 RUNNING；canonical PR／CI、static、停服存檔first／restart、完整准入及逐檔／順序讀回通過。[新公開proof](../family/PUBLIC-DOWNLOAD-LIVE-NATIVE-ITEM-20261013.md)确认六包9344檔相同；T／W匿名新下載，G130保留R150匿名archive硬連結來源。`client=false`、`production_ready=false`、`pending_client_acceptance`。

T151僅重用native成功ItemTypes lookup，未知／throw／generic原行为保持，未見明確native收益；W128只三份dependency identity配對，G130／reviewed integration／Ribbits10036／HUD5不變。Poststart254 warnings／0 errors、227 watchdog（9 Spike／217 Slowdown／1 High Memory），T290／282、Ribbits418、W271、G517、Cookery308、AMW307ms Spike仍在；不同窗口或舊native告警disabled不能比性能百分比。

真人快開短空條、完整聲畫／操作、任意whole HUD／title与Java一比一仍待接受。下一T152／W129仅本機freeze，native／LIVE未接受；每chunk快取不消除partial reverse整串FNV fallback，不称全面有界。151 receipt／proof不能借用为152。以下舊parity正文／數字／影片与proof保持原身份。

## 歷史部署：T150／G130／W127／private-integration／Ribbits1.0.10036

[private deployment time]完成42包家族部署，BDS1.26.52.3 RUNNING；canonical PR／CI、static、停服存檔first／restart、准入及逐檔／順序讀回通過。[公開proof](../family/PUBLIC-DOWNLOAD-LIVE-STARTUP-20261013.md)確認六包9344檔完全相同；`client=false`、`production_ready=false`、`pending_client_acceptance`。

T150的21products／28pages、W fixture175registration packets及Ribbits54structures／158connections是各自來源回歸保全；不擴寫为整包bytes相同、LIVE投遞／ACK、任意資料或真人完整玩法。G130／reviewed integration／原五份HUD變體不變。

Poststart257 warnings／0 errors、230 watchdog（9 Spike／220 Slowdown／1 High Memory）；T249／288、Ribbits431、W265、G447、Cookery310ms Spike仍在。本輪native已保留100／10ms門檻，舊native未設定而關閉對應告警；不同窗口／條件不能作性能百分比。快開短空條、完整聲畫、第三方whole HUD／title、Java一比一及作者新版適配仍待完成。下列舊parity段／影片原字節与身份保持，不能借用为T150真人接受。

## 歷史部署：T149／G130／W126／private-integration

[private deployment time]已部署完整42包家族，BDS1.26.52.3 RUNNING；canonical PR／CI、static、一次新鮮停服存檔first／restart、准入及完整檔案／順序讀回通過。[現行基線](../family/BASELINE-STATUS.md)及[公開下載核對](../family/PUBLIC-DOWNLOAD-LIVE-HUD-20261013.md)記錄自有六包9343檔相等；私有／第三方變體另有来源。`client=false`、`production_ready=false`、`pending_client_acceptance`。

T149分批準備指南／擴充，T／G圖形改命名空間封包、可選UI Queue／獨立快照與明確END，保持共享Actionbar；W126配對T149且指南註冊分批準備。reviewed integration有界指南接收，reviewed integration快取／reviewed integration renderer保持；五份登記HUD變體經原玩法／資產保全、來源CI及本輪fresh saved-world native，不冒充作者新版。

Poststart292 warnings／0 errors，包含265 watchdog（9 Spike／254 Slowdown／2 High Memory）：T仍2／75、G1／39、W1／81、Cookery1／20筆Spike／Slowdown。W最大Spike1479→284ms但採樣54.892／75.552秒，不足以宣稱全局效能改善。[QA PR340](https://github.com/casama233/kaleidoscope-tavern-unofficial/pull/340)讓未來隔離引擎保留LIVE已設定100／10ms門檻；舊QA未設定值會關閉相應告警，不作效能成功。

真人快速重開短空條、完整聲畫／操作、第三方整份HUD及未協調title寫入仍待[新家族回歸](HUD-COMPAT-CLIENT-HANDOFF-20261012.md)。Dot原結果版本未知，沒有改為新版本通過；Java完整一比一及作者新版UUID／API／保存適配仍未完成。以下舊parity表與觀察保留原身份。

## 歷史部署：T148／G129／W125／private-integration

[private deployment time]已部署完整42包家族，BDS1.26.52.3 RUNNING；static、一次新鮮停服存檔副本first／restart、准入及完整檔案／順序讀回通過。[現行基線](../family/BASELINE-STATUS.md)及[公開下載核對](../family/PUBLIC-DOWNLOAD-LIVE-UI-20261012.md)記錄來源及自有六包9339檔相等。Poststart313 warnings／0 errors，LIVE仍有慢速警告；`client=false`、`production_ready=false`、`pending_client_acceptance`。

| 範圍 | 本輪來源修補／保留 | 未完成／待驗 |
| --- | --- | --- |
| T／G HUD掛載 | 兩個renderer各自註冊命名空間，共用相同最小可選掛載及內部封包過濾；原factory、Atlas、動畫、HUD200及玩法時間保持。W125精確配對T148。 | 新家族真人進食／取消／快開、調酒／效果／原生HUD待驗；共享Actionbar競爭及第三方整份HUD覆蓋仍有相容限制。 |
| Cookery快取 | private-integration唯一新元件按需重建配方快取，原renderer32與ChineseFood1.0.10432保持。來源Node差分六批次／11類作者註冊下75→7次鍋類重建，ACK／排序讀取／動態覆寫相等。 | Node來源模組診斷不是BDS watchdog或客戶端卡頓改善；真人效能與作者Cookery1.6.1的新UUID／API／state／保存適配未完成。 |

Dot既有取消保留物品、完成後退出、調酒裝料／返瓶／產出通過，仍見兩次快開短空條；候選與客戶端版本未知，不能當本輪驗收。[完整家族客戶端流程](HUD-COMPAT-CLIENT-HANDOFF-20261012.md)保留此邊界。Java完整玩法／聲畫與World Liquor26.1.2／1.1.6等差距仍未完成，來源／包／載入相等不等於一比一。

以下歷史段落及parity表保留原版本、來源與證據範圍，不代替當前新家族真人驗收。

## 歷史部署：T146／W123／G125

[private deployment time]已部署T146／W123／G125及private-integration，來源與當次准入／存檔證據見[當前基線](../family/BASELINE-STATUS.md)。一次新鮮停服存檔的首次啟動／保存／重啟同時供應完整家族BDS與資料保存證據；現服讀回成功，真人驗收仍待進行。

T146保留T145手持辨識及T144輸入框修補，追加受限事件的安全原料快照、黑板signature62逆轉換與100ms進度顯示。[原修補範圍](RELEASE-NOTES-0.6.146.md)中的五段獨立錄影仍只支持有限場景：259個活動畫面未見HUD缺失，已完成／空杯重複使用及短按保留原料有正向觀察；持續按住時切槽仍不確定，同秒快速重啟未測。這些觀察不等於現服完整家族或聲音驗收。

| 範圍 | 本輪source修補 | 未完成／待驗 |
| --- | --- | --- |
| 黑板 | root bindings保留單一匹配輸入框；正確原生座標逆轉換及signature62重建舊字形，不改保存文字、對齊或topY。 | 現服四向板面／焦點、觸控與手把待真人；正式多行、彩字距離與望遠鏡仍未完成。 |
| 雪克杯 | 原料metadata移到可寫階段，保留原clone、扣料／退瓶／回復與取消守護；進度保持100ms，游標插值仍50ms。 | 現服投料、持續搖晃、放開／切槽、聲音與快速重新開始仍待真人確認。 |

以下歷史段落保留原證據身份，不能視為現服狀態或當前真人驗收。

## 保留 canonical T141／W118 的修補與證據

精確 predecessor 為已發布主線 `79e2ad0fb9f5a59f93be41aee002ddf2a809d71b`。完整承接四頁 AMW 指南、三語七入口、共用 Cookery 入口及全部既有修補，配套 W118／G122。[T141 說明](RELEASE-NOTES-0.6.141.md)記錄相同功能檔案的來源回歸；新 paired native 首次 21／重啟 22 項與嚴格 recorder 已通過，完整 CI 由修補 PR 執行；舊分支 T140 試驗保持原身份。

| 範圍 | 本輪修補／保留 | 證據及未完成範圍 |
| --- | --- | --- |
| 板面分隔符 | 溢出的當前空格先記錄再消耗；index 0 也是有效換行點。小板容量、明確換行、Word 對齊及既有描邊／cull 不變。 | 原作 Font.split 入口與 Mojang StringSplitter bytecode、5 項 rendering 回歸及 layout 檢查。per-viewer feet／camera 16 格、第一人稱 spyglass 及 client 未完成。 |
| 雪克杯來源與新點擊 | 原生 metadata 三態比較；扣料須證明相同，只有不同可解除 owned 防重。pending authoritative true 比較 amount，native／false／itemUse 延續不重複扣料。 | 最後 10 項 station witness 與交叉審查，含 2→3 fresh click、clone／read failure、空手 echo／foreign cancel。任意 NBT、任意裝飾非堆疊原料與真正 Player pending。 |
| W118 LivingEntity | 84 個原版對應與 addon mob-family fallback，魚類進入既有效果／credit，非生物 health helper 排除；class 與 alive credit 分開。 | W 正式註冊回呼、paired projection 26 項與獨立 8 項回歸；新原生 cod API fall 對照首啟／重啟通過：control 3→2／一次 afterHurt、公開 snapshot 的 MultiJump 3→3／零 afterHurt；完整傷害階段／致命流程及 native Luck 未完成。 |

已發布 T140 guide-copy／catalog／standalone-guide／family receiver 保留主線內容；client、私人完整家族、fresh stopped-world 與 LIVE 仍 pending。純 roll、穿牆輪廓、多行 editor 及其他既有差距不因本輪而完成。以下保留各版本原始範圍。

# Java / Bedrock parity matrix

## Retained Tavern 0.6.138 / World Liquor 0.1.115

[T138](RELEASE-NOTES-0.6.138.md) combines observed native countdown persistence with the exact reload acknowledgement repair, retaining all source gameplay and visual work. The parallel source review preserves conflicting historical candidates without rewriting their identities. The frozen T138/W115 pair passed its own complete zero-player native first/save/restart and source-bound recorder. Final canonical CI is separate; isolated multiline tooling has no human-client acceptance.

## Historical T137 / W114 (scoped native restart passed)

[T137](RELEASE-NOTES-0.6.137.md) retains the Mob and confirmed-anchor repairs and corrects the native reload EffectAdd notification that revoked a valid saved aura lease. Only a genuine entityLoad, exact same-tick snapshot can consume one notification witness; foreign refresh and existing saved-duration checks remain. The frozen T137/W114 pair passed a new zero-player native first/normal-save/restart run and the complete source-bound recorder, including one reload acknowledgement followed by one foreign handoff. Final canonical CI and actual Player/client/private LIVE acceptance remain separate.


## Historical alternate T136 / W113 scope (native restart failed)

[Immutable alternate T136 scope](https://github.com/casama233/kaleidoscope-tavern-unofficial/blob/d9e7bcc6dd9d00beca0bbf76f0fff50b6eca0813/docs/RELEASE-NOTES-0.6.136.md) preserves all T135 repairs and adds
query-first alive Mob selection for Upside Down, including fish without the
Native mob family while excluding Player/ArmorStand. Target membership is
fixed before nameTag callbacks. Java name visibility and rendered inversion
remain unverified. W113 records only confirmed changed Nether anchor points,
with source yaw=0/forced=false, repeat/cancel guards and pending lifecycle cleanup.
Original resolver settlement, author assets and helper exclusions remain intact.

Source/API counterexamples and cross-review passed. Exact T136/W113 native
first/restart and CI must supply their own results; actual Player, rendering,
full private family and LIVE remain pending. G120 source/helper compatibility
is reviewed, with its complete Cookery 0.2.7 host adaptation still required.
The historical sections below retain their original evidence scope.


## Retained T135 / W112 repair scope

[T135 repair scope](RELEASE-NOTES-0.6.135.md) retains the T134 implementation
and limitations below. Actual T134 CI run `37869770416` exposed two runtime
gaps and one test-fixture gap; its failure and frozen history remain intact.

| Area | T135 correction | Evidence boundary |
| --- | --- | --- |
| Generated visual surfaces | Add the 24 ice-grape frame texture sets and one RGB opaque texture set using the existing canonical 215/170 roughness profiles; both generators reproduce them. | The full `check_visuals.py` file passes with 460 surfaces and zero audit errors. Native PBR output and rendered-client comparison remain pending. |
| Portable Adventure metadata | Validate native bare vanilla block IDs as vanilla IDs, preserving original strings, order and bidirectional reconstruction checks. | Native setter/getter format portable regression passes; the final paired native first/restart run and actual Player acceptance remain separate. |
| Ardent test fixture | Supply duration-aware `getEffect` to the test double without changing production code or weakening assertions. | All 13 existing targeted cases pass; this is test-fixture evidence. |

W111 CI succeeded for its own candidate. W112 now declares the exact T135
dependency; final T135/W112 CI is pending and does not inherit that result.
G119 is unchanged. Pure camera roll, through-wall outlines, native multiline
editing, arbitrary decorated nonstackable shaker inputs, dropped-item display
contexts, native reach/step-height/XP pickup, target clearing and remaining
effect semantics retain their documented limits. Client, private complete-family
and LIVE acceptance remain pending under the existing standing authorization.

## Retained T134 / W111 integration scope

[T134 integration scope](RELEASE-NOTES-0.6.134.md) preserves final PR297 source,
reviewed PR298 head and W110 author updates. PR298 remains open/draft at
integration; inclusion is not a claim that it has merged. Forge main `c4ec1880`
and maintained NeoForge branches remain distinct references; Grilling G119 is
unchanged. Final candidate CI, zero-player native evidence, actual Player input,
rendered-client acceptance and LIVE deployment remain separate and pending.

| Area | Current implementation | Remaining scope |
| --- | --- | --- |
| Machine ingredients | Complete counted native clones, metadata-sensitive merging, legacy adoption, original extraction and checked consumption/destruction rollback. | Exact paired native first/restart evidence and actual Player, crash/chunk/foreign-mutation scenarios remain separate. |
| Portable shaker inputs and storage | Bounded self-contained stackable metadata with bidirectional native reconstruction checks before debit; T132 hand/echo/retry and T133 finite-XYZ identity repairs retained. | Three arbitrary decorated nonstackable items/potions remain unsupported and rejected intact; native input and saved-world acceptance remain pending. |
| Machine operation | Source Creative fluid retention, direct-hand output, overflow delivery, Adventure ordinary use and doTileDrops protection. | Complete third-party FluidUtil capabilities and native input emission remain unproven. |
| Board glow | Black foreground/cream outline, dark colored outline, source 0.5-pixel offsets, separate far foreground submission and board-center 48-block cull. | Colored outline camera-vs-feet 16-block boundary, first-person spyglass and native multiline editor remain different. |
| Animated ingredients and cups | Original ice-grape tick images on four barrel/eight pressing paths; glass, atlas and RGB passes share the level clock across helper replacement. | Tick unit is supported by Mojang's cod sample; native terrain/atlas synchronization, long uptime, resource reload and actual rendering remain pending. |
| Arbitrary signature RGB | Existing 336-color atlas plus original source-texel shading in the same helper, including W111 external colors; exact geometry allocations and source coverage checks. | Material output, distance filtering, transparency, PBR/Vibrant Visuals and all display contexts need actual client comparison. |
| Status particles | Original custom colors, float32 weighting, source emission probability and spell resources; durable ownership only for provably host-created native effects. | Unknown external ambient/visibility is not inferred; mixed-source rendering remains unverified. |
| Grass / Tipsy | One-tick non-overwriting invisibility lease; explicit yaw opt-in and no default aim movement. | Whole player renderer cancellation, equipment/name hiding, target clearing and pure camera roll remain unimplemented. |
| Living policy and XP observer | Final PR297 distinguishes the observed health-less XP orb from an explicit health-bearing test helper. | It does not prove Java class reflection, Player event order or native XP pickup parity. |
| World Liquor author data | W111 retains W110 Dassai Q3–Q6 amplifiers 1/3/5/7, four source cup meshes/atlases and two inventory sprites; existing geometry IDs and API1 admission remain valid. | Native Luck loot behavior, other branch/event semantics and rendered-client acceptance remain incomplete. |

The private BSM/current quality checkpoint/LIVE world is unavailable in this
workspace. Full-family assembly, stopped-world rehearsal, guard, backup and
deployment/readback remain pending under the existing standing authorization.
Historical sections below retain their original version scope; T134 notes
record which source gaps are now repaired without upgrading old evidence.

## Retained T132 / W109 repair scope

[T132 release scope](RELEASE-NOTES-0.6.132.md) is the current source-repair entry.
Forge main `c4ec1880` remains the original comparison target. The shared instant
adapter uses its established NeoForge 1.21.1 policy; the actual Forge/Neo potion
eligibility difference is explicit below. Optional family peer G119 is unchanged.
L1 means production callbacks with API doubles or original-source/asset checks,
not an observed native Player or rendered frame.

| Area | Current implementation and remaining difference | Evidence and next acceptance |
| --- | --- | --- |
| Instant splash | Shared class/inversion/int32/float/hook dispatch; owner-only native magic mapping; per-recipient potion-policy snapshot; ArmorStand immune to the full splash loop. Neo1.21.1 living gate differs from Forge1.20.1. | Dispatcher/impact regressions and explicit old-profile compatibility. Current CI observes real native HP/events with test impact envelopes; physical collision, Java damage tags and client remain separate. |
| Shaker station and offhand placement | Native held-item block callback works; after consuming the last ingredient or placing from offhand, the same gesture cannot become empty-hand pickup. Fresh authoritative presses and failed-transaction retries remain available. | Offhand, shared echo, retention and pinning source cases. Actual touch/controller/native Player callback ordering remains pending. |
| Native item storage rollback | Every slot cleanup, created-entity removal and both persistent pointer writes are attempted independently. Unsupported internal metadata remains protected. | Injected cleanup and durable-write failures. Full portable three-arbitrary-ItemStack preservation remains unsupported; old potion-capacity evidence retains its own version. |
| Vision | Complete alive/AABB selection before effects; exclude health-bearing vehicles and include known Java living fish without Native mob family. Registry-aware 50/60-tick sound behavior remains. | Vision and Ardent scheduling cases; current native observer compares boat/cow/armor stand/cod. True through-wall outlines and Player entrance are not certified. |
| Four animated guide icons | Source-derived 10/18/80/24 tick strips and local-path/filesystem-only flipbook routing; other images retain native behavior. Original inventory/held item meshes from T131 remain. | Original interpolation-class RGBA oracle, generated-byte and foreign-route checks. Real filesystem binding, rendered UI, resource-pack order and global animation phase remain pending. |
| Board text and HUD | Literal backslashes survive escape-field round trips. Slot tail is now 0.5 s; progress remains 0.05 s. Other forms' input/focus/submit controls are unchanged. | Board form/layout and HUD native-root preservation checks. Native multiline editing and immediate stop remain unimplemented. |
| Retained T131 interactions | Direct touch, furniture/Adventure use, captured-hand metadata, source wax/axe behavior, Molotov support rules and quiet feedback remain. | See T131 notes for exact earlier repairs; new source does not relabel prior client/native observations. |
| World Liquor / G119 | W109 pairs T132 without a gameplay rewrite; L108's exact G119 helper exclusions remain. | Paired source/manifest/guide CI and real World Liquor descriptor registration. Player respawn/bed/anchor lifecycle and private full-family acceptance remain pending. |
| RGB / dropped shaker / camera | Existing 336-color atlas and flat external RGB adaptation retained. Dropped 3D with separate GUI 2D and additive free-look roll remain unresolved. | Earlier rejected experiments are not restored; current paired human scenes are required. |

The current full T/W zero-player load/restart uses complete frozen BP/RP copies
with explicit observer overlays, and records actual source/engine and no-player
proof. It is not the private full-family scene, stopped live-world migration,
physical Player input or a rendered-client test. Those gates require the actual
BSM/world connection, unavailable here. Client/live status remains pending.

## Retained earlier evidence and source gaps

Previous repair candidate: Tavern0.6.130 with World Liquor0.1.107. The
[T130 update](RELEASE-NOTES-0.6.130.md) adds active-only shaker PUT recovery,
grouped and differential rack/cabinet maintenance, per-tick Ardent completion,
native living-entity Bloody Mary, registered partial locale aliases and scoped
legacy-shaker metadata migration. The native mob equippable gap remains confirmed;
Chinese attachment tooltips, full client visuals and actual FPS remain pending.

Retained T129 scope: The current
[cocktail repair scope](RELEASE-NOTES-0.6.129.md) adds Java ingredient admission,
container-before-debit order, Creative placement, sneak-air clearing, physical
bounds, complete placed shaker carrier transactions, actual cocktail lore and
guide details, owned HUD interpolation/expiry, personal sound, native Ardent
block drops and the bounded High Heels improvements. The existing T128 carried
clone/abort behavior and T127 framing remain. Full ingredient metadata is still
unsupported; the failed three-potion nested-container route is excluded based on
[actual engine observations](../data/native-shaker-storage-capabilities-20261008.json).
Native fixture scope and current client acceptance remain separate; no full
Java or LIVE success is inferred from the current repair.

Retained T127 source scope: Tavern0.6.127. Main-hand framing now retains the bounded PR247 adapter and third-person arm Y is additive zero, preserving incoming yaw from PR167. Original mesh/half-scale/use-wave/XZ pose and all other current gameplay remain. Source/socket/selector checks pass; full current client view, hand, FOV and shake-trajectory acceptance remains pending. This supersedes the old source gap only, not the historical T106 observations.

Audited Bedrock sources: T0.6.126 ac4932b4 / W0.1.103 56314bac. This initial Phase0 matrix covers the inspected player-facing priorities; complete T1/T2/W1 recipe, timing, storage and effect coverage will be added in subsequent phases, not presumed complete. A single future slice reference awaits the owner decision. L0=source inspection, L1=executed source/oracle, L2=scoped native-engine scene, L3=paired actual-client observation. Historical partial L3 cannot certify later releases or all contexts. T/ and W/ identify the repository.

| Item | Java reference | Current implementation / gap | Source result | Affected engine scene | Client evidence |
| --- | --- | --- | --- | --- | --- |
| T-POTION-LIQUID 放置原生藥水液體色與原生瓶朝向 | Forge c4ec1880 / NeoForge a1afba34 PotionBottleColor, VanillaBottlePlaceEvent and BottleBlock.getStateForPlacement; original Minecraft 1.20.1 PotionUtils / 1.21.1 PotionContents. | Vanilla bottles face opposite the player. Colour and Creative pick share strict read-only native storage; block ticks repair the liquid helper. Default RGB follows the reviewed Neo integer policy; this review established no differing normal native input for the former blanket Forge-float gap. Arbitrary custom RGB/effect visibility is unexposed by the potion identity API, not a reproduced normal-potion conversion error. WATER/EMPTY remain stateless; Wither adaptation and unknown-ID white remain. | Existing original-JVM default vectors and actual-source placement tests retain their original scope. The 2026-11-06 review follows native stack -> effectId -> core colour -> helper properties; the resource generator does not average potion colours. Branch algorithms and API input limits are recorded once in [POTION-BOTTLE-VISUAL.md](POTION-BOTTLE-VISUAL.md). No runtime or oracle rerun. | Historical T180 BDS 1.26.52.3 first-load/restart proved potion metadata/RGB/removal in its original source scope; [original job](https://github.com/burnt-tea-dev/kaleidoscope-tavern-unofficial/actions/runs/40012443439/job/120616254143). T183 facing/read consolidation has source checks; this review adds no current-engine or rendered-client evidence. | No current rendered-client colour/rotation/lighting/resource-stack observation is established by these numeric or historical native results. Such observations are optional and are not a release gate. |
| T-GLASS-PBR 普通玻璃亮度、透明排序、PBR | refs: T/art/source-jar.lock.json; T/art/sources.lock.json; scope: Original glass textures/models and tint separation; Bedrock PBR values are conservative port tuning, not Java-authored PBR truth. | implementation_present_current_visual_pending; 普通玻璃過亮是歷史回報，尚無當前重現；曝光、透明排序、PBR硬體/資源包堆疊仍待D。 | level: L0_material_configuration; refs: T/tools/check_visuals.py:27; T/docs/VISUAL-MATERIAL-AUDIT-0.6.110.json; facts: Current empty_glassware MER=[0,0,150]. Static checks prevent excessive emission/transparent emitting texels; they do not measure brightness or transparency. | scope: Exact T126/W103 full-family load/restart and saved-world deployment gates passed per CURRENT-WORK; loading is not an affected gameplay/render scene.; affected_scene: False | current_acceptance: False; meaning: No current T126/W103 client observation located in reviewed sources; this is pending, not a reproduced current defect. |
| T-SIGNATURE-GUI 特調庫存/快捷欄圖示杯身完整、僅酒液染色 | refs: reviewed-java-checkout/java-tavern-upstream/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/misc/SignatureCocktailColor.java:27; T/data/upstream/c3/javap/item.SignatureCocktailBlockItem.txt; T/art/source-jar.lock.json; scope: Selected original source says tintIndex1 uses item color and other layers stay white; archived checkout/source locks must not be mislabeled newest branch acceptance. | implementation_present_current_gui_pending; 歷史『一小團藍色』不得當成當前已重現BUG；當前全GUI尺度、資源包堆疊及重登顏色待D。 | level: L0_texel_and_wiring; refs: T/tools/check_visuals.py:42; T/tools/check_visuals.py:51; facts: Full16x16 default/dyeable icon routes and glass/liquid alpha mask checked; texel counts are asset preconditions, not GUI acceptance. | scope: Exact T126/W103 full-family load/restart and saved-world deployment gates passed per CURRENT-WORK; loading is not an affected gameplay/render scene.; affected_scene: False | current_acceptance: False; historical: T105 real-client report confirms a completed signature and named BloodyMary; it does not explicitly certify the full signature inventory mask/all scales.; refs: T/docs/PUBLIC-TEST-VALIDATION-0.6.105.json |
| T-SIGNATURE-3D 特調放置酒液色/紋理動畫、外部RGB | refs: reviewed-java-checkout/java-tavern-upstream/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/misc/SignatureCocktailColor.java:14; reviewed-java-checkout/java-tavern-upstream/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/blockentity/mixology/SignatureCocktailBlockEntity.java:37; T/art/source-jar.lock.json; scope: Source retains per-cup RGB and tints only liquid layer. | bounded_historical_render_verified_external_rgb_shading_gap; 外部atlas外RGB已知使用平面overlay陰影，非Java像素等價；FOV、影格、所有混色與堆疊待D。 | level: L0/L1_data_and_texel; refs: T/tools/signature-rgb.test.mjs:10; T/tools/check_shaker_signature_colors.py:28; facts: Existing336-entry exact Java mean-color atlas retained. RGB arithmetic test mirrors the mean formula and is not an independent rendered oracle; source texture/frame checks only verify declared assets. | scope: Exact T126/W103 full-family load/restart and saved-world deployment gates passed per CURRENT-WORK; loading is not an affected gameplay/render scene.; affected_scene: False | current_acceptance: False; historical_render: version: T105/W66; status: bounded_pass; facts: Three actual wine inputs produced a shaded magenta signature; Java-red atlas liquid rendered red with textured shading; Out-of-domain pure-red RGB fallback rendered red with flat shading; supersedes: T102 white/gray material failure is historical and partly superseded by T105; do not claim it persists universally.; refs: T/docs/RELEASE-NOTES-0.6.105.md:17; T/docs/PUBLIC-TEST-VALIDATION-0.6.105.json; T/docs/NATIVE-T102-COLOR-RGB-20261005.json; inheritance: Current signature_tint last changed in T105 commit d0f6f480; this supports retention of the shader route, not full T126/client acceptance. |
| T-SHAKER-HELD 雪克杯第一/第三人稱rest/use/release可見與動作 | refs: T/art/interfaces/shaker-held-java-reference.json; T/art/interfaces/shaker-hand-source.json; scope: Source1.2.0 shaker_3d display transforms and source animation waveform; first-person ordinary filled shaker has no separate skin arm in examined Forge1.20.1 source, not all-branch client proof. | bounded_historical_client_pass_current_matrix_pending; 當前完整動作/波形與所有FOV/皮膚未驗收；歷史STALE_HAND/SPACE_NOT_CLEAR原因未證實；舊測試無ALSA音效設備。 | level: L0_source_transform_checks; refs: T/tools/test_shaker_native_frame.py; T/docs/SHAKER-FIRST-PERSON-0.6.106.md; facts: Source/socket transform and animation wiring checks do not certify every rendered frame. | scope: Exact T126/W103 full-family load/restart and saved-world deployment gates passed per CURRENT-WORK; loading is not an affected gameplay/render scene.; affected_scene: False | current_acceptance: False; historical_render: version: T106/W67; status: bounded_visibility_pass; facts: Empty and filled first-person resting shaker visible; Actual3900ms use/release retained cup/progress; cup survived progress expiry; Third-person front held model visible; Paired cold-load iced tea bottle name/icon/held model visible; refs: T/docs/PUBLIC-TEST-VALIDATION-0.6.106.json; T/docs/REGRESSION-STATUS-2026-09-27.md; inheritance: Current runtime_shaker animation last changed in T106 commit2b95176e. Historical owner third-person confirmation is separately recorded in Sep27 document. |
| T-INCENSE 香薰煙霧/環境粒子、開关/紅石可見效果 | refs: reviewed-java-checkout/java-tavern-upstream/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/block/deco/IncenseBlock.java:148; reviewed-java-checkout/java-tavern-upstream/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/particle/IncenseParticle.java; reviewed-java-checkout/java-tavern-upstream/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/particle/IncenseSuspendedParticle.java; T/art/source-jar.lock.json; expected: Selected source animateTick:1/3小煙，OPEN=false也存在；OPEN=true另5個環境粒子；粒子種類各有motion/size/lifetime。 | source_adaptation_present_current_visual_pending; 歷史『幾乎不可見』沒有當前客戶端重現；Sep27固定20/3/s+48/s與40格記述已不描述現行recipient-local Java sampling；混音、大小、motion/遮擋與隨機流待D。 | level: L0/L1_sampling_and_motion; refs: T/tools/check_incense_sampling.mjs; T/tools/effects/incense_motion.py; T/tools/effects/incense_large_motion.py; facts: Source sampling/motion checks exist; emitted count is recipient-local sample driven. Current pine plume uses lookat_xyz and finite instant emitters. | scope: Exact T126/W103 full-family load/restart and saved-world deployment gates passed per CURRENT-WORK; loading is not an affected gameplay/render scene.; affected_scene: False | current_acceptance: False; meaning: No current T126/W103 client observation located in reviewed sources; this is pending, not a reproduced current defect. |
| T-W-STORAGE 酒架/酒櫃格位、瓶身旋轉/莫洛托夫、材料資料保存 | refs: T/data/storage-render-source.json; reviewed-java-checkout/java-tavern-upstream/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/BarCabinetBlockEntityRender.java; reviewed-java-checkout/java-tavern-upstream/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/CellarCabinetBlockEntityRender.java; reviewed-java-checkout/java-tavern-upstream/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/TiltedRackBlockEntityRender.java; reviewed-java-checkout/java-tavern-upstream/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/client/render/block/HolderBlockEntityRender.java; scope: Pinned c4ec188 renderer PoseStack matrices and source bottle coordinates; full newest-branch equivalence remains distinct. | transaction_and_native_preservation_bounded_visual_pending; 四向外觀/玻璃/副手/觸控與實際mouse hit待D；T126未採作者Bedrock1.0.1 E/W座標改法，不能宣稱current E/W必壞；完整來源矩陣與client仍需對照。 | level: L0_geometry / L1_transaction; refs: T/tools/check_storage_rendering.py; T/tools/native-storage-pinning.test.mjs; T/tools/glassware/storage-routing.test.mjs; facts: Fixed slot/model transforms and exact item carrier proof exist. Registered storage paths have source/API cases; fake ray objects do not verify real mouse coordinates. | level: L2_bounded_helper_preservation; refs: T/data/native-storage-reanchor-capabilities-20261007.json; facts: Actual same actor/metadata/record bytes survived displaced carrier recovery/restart. Zero players; synthetic helper restoration, not actual user insert/retrieve, all loaded/unloaded/crash phases or visible bottles. | current_acceptance: False; meaning: No current T126/W103 client observation located in reviewed sources; this is pending, not a reproduced current defect. |
| T-W-FURNITURE 家具方向/含水/座位、動畫家具、方塊擺放與連接 | refs: T/art/source-jar.lock.json; T/data/storage-render-source.json; W/upstream/assets/kaleidoscope_world_liquor/blockstates; scope: Original blockstates/models plus selected Java placement/render matrices; source-specific hand/face/use ordering matters. | source_adapters_present_current_visual_pending; Current全家具、animation/facing/pose與support/多人互動待D；不得把所有家具方向當已知故障。 | level: L0_assets / L1_placement; refs: T/tools/check_visual_rules.mjs; T/tools/test_shaker_native_frame.py; W/tests/wall-record.test.mjs; facts: Source bindings/state/transform and callback cases cannot prove actual input, all-view animation or transparent order. | scope: Exact T126/W103 full-family load/restart and saved-world deployment gates passed per CURRENT-WORK; loading is not an affected gameplay/render scene.; affected_scene: False | current_acceptance: False; historical: Shaker third-person owner confirmation exists; that confirmation does not certify all furniture/animated assets.; refs: T/docs/REGRESSION-STATUS-2026-09-27.md |
| T-INSTANT-DRINK 喝瓶/普通附屬雞尾酒/特調即時治療與傷害在結算前發生 | refs: T/docs/INSTANT-HEALTH-DISPATCH-PROTOTYPE.md:8; T/data/java-parity/instant-source-reference.json; methods: CurrentNeo1.2.0 DrinkBlockItem:150,CocktailBlockItem:96,SignatureCocktailBlockItem:52 pass self/direct/indirect,target/intensity1;Minecraft1.21.1 HealOrHarmMobEffect and NeoForge heal hook. | implemented_bounded_native_synchronous_health_player_pending; IndirectMagic tags/knockback、afterHurt/death時序、任意可執行heal hooks/自訂class、Player死亡drop alias仍不等價/未證明。『所有instant要nexttick』已過時。drink-effects.js:39-40舊註解仍籠統延遲，需文件精確化。 | level: L1_source_arithmetic_and_actual_callback; refs: T/tools/java-instant-dispatch.test.mjs; T/tools/instant-drink-completion.test.mjs; facts: Existing22 arithmetic/dispatch+5 actual drink callback regressions reported in122; no new local run. Accepted API dispatch is not proof that engine damage was accepted. | level: L2_bounded_mob_health; refs: T/data/native-instant-health-capabilities-20261008.json; facts: 18 actual zero-player observations,16 source-health matches; immediate and nextTick same scoped health except totem later regeneration. Normal/undead,clamp,Resistance,absorption,cooldown,armor/Protection,toten cases recorded;0/negative hurt source phase not proven. Real Player use/client=false. | current_acceptance: False; meaning: No current T126/W103 client observation located in reviewed sources; this is pending, not a reproduced current defect. |
| T-INSTANT-SPLASH 投擲酒瓶瞬時治療／傷害 | Current T132: same shared dispatcher as drink; source ThrownPotion gate captured before each effect loop. Neo1.21.1 alive policy, Forge1.20.1 constant policy and both ArmorStand overrides were checked separately. | implemented_source_repair_with_explicit_adaptations; int32/float/hook/class policy and ownerless handling repaired; native magic_owner_only and unknown custom timed-policy fallback remain incomplete parity. | L1 production impact/dispatcher and old-profile cases passed; current native observer uses real Entity/API but test event envelopes. See T132 CI for actual current results. | Full private family and saved live-world gates pending; T/W zero-player CI is separate. | Actual Player input, physical collision, client/audio and complete Java damage-phase acceptance pending. |
| T-TIPSY-ROLL 微醺只旋轉相機roll，不改玩家瞄準方向 | refs: T/runtime/BP/scripts/core/tipsy-visual.js:1; expected: Java CameraAnglesEvent modifies roll; source raw rotation is separate from actor yaw. | unimplemented_pure_roll_reassess_platform_capability; Pureplayer-overlay roll尚未實作；新stable三軸animation是否可不接管視角/手持/瞄準，需要獨立真client評估。是否納入優先切片由擁有者決策，不自行放棄。 | level: L0/L1_yaw_adapter; refs: T/tools/check_visuals.py:68; facts: Checks guard existing yaw adapter; this is not pure-roll parity. Parent platform audit verified currentstable Camera.playAnimation and RotationKeyFrame.rotation Vector3 withz; no blanket no-three-axis-camera claim. | scope: Server setRotation/readback diagnostics only; neither confirms camera overlay nor preserves aim.; refs: T/runtime/BP/scripts/bedrock/tipsy-visual.js:58; pure_roll_engine_or_client_proof: False | current_acceptance: False; meaning: No current T126/W103 client observation located in reviewed sources; this is pending, not a reproduced current defect. |

## Other tracked mechanics

These rows default to Forge1.20.1 source c4ec1880; the XP pickup row independently reviews NeoForge1.21.1 a1afba34 as stated. Other NeoForge slices still need their own source review. Tracking [issue98](https://github.com/casama233/kaleidoscope-tavern-unofficial/issues/98).

| Item | Original expectation | Current implementation gap | Evidence / next scenario |
| --- | --- | --- | --- |
| T-LONG-REACH 長臂原生攻擊／挖掘距離 | Forge c4ec1880 `LongReachEffect.java`: BLOCK_REACH／ENTITY_REACH +3 | `bedrock/custom-effects.js:128–129`: 只擴大酒館 item-use 射線；原生攻擊／挖掘／一般實體互動未適配 | L0 inspected; 喝到長臂後，對比超過原生距離的挖方塊、攻擊生物與酒館取酒；各自記錄距離與結果。 |
| T-GRASS-STEALTH 草叢潛行已鎖定仇恨 | Forge c4ec1880 `GrassStealthEffect.java`: 成熟植物／潛行條件下清除32格內已鎖定的mob target | [updateGrassStealthVisibility](../runtime/BP/scripts/bedrock/custom-effects.js)保留短暫invisibility；未清除既有target | [2026-11-05原生結果](../data/native-grass-stealth-target-20261105.json)：BDS1.26.60.6／server2.12.0-beta的真殭屍已鎖定生存模擬玩家，undefined／null／其他Entity三種寫入均報target唯讀，原目標保留；descriptor只有getter。沒有改runtime或覆寫原版生物；不是此玩法已修復。 |
| T-HIGH-HEELS 高跟鞋原生步高 | Forge c4ec1880 HighHeelsEffect：STEP_HEIGHT_ADDITION +0.5 ADDITION；Neo a1afba34：STEP_HEIGHT +0.5 ADD_VALUE，交原生移動／碰撞。 | [pulseHighHeels](../runtime/BP/scripts/bedrock/custom-effects.js)仍是Player條件式一格tryTeleport適配。T204草稿先用ray排除passable／liquid，仍保留目的地checkForBlocks／keepVelocity；不是原生步高屬性，尚不可交付。 | [來源回歸](../tools/high-heels-adapter.test.mjs)沿正式White Lady資料，修前花誤lift失敗、修後5項過；只是介面double。[真Player結果](../data/native-high-heels-player-204.json)：server2.7原tryTeleport保速參數實際拒絕；花／水／solid因native輸入getter全0未進predicate，三案均未驗收。QA已正常停清，未部署T204；原生component仍待能力證據，未採用／未改正式Player。不重跑此已拒絕API；半磚／斜向／其他等級及非Player完整等價未成立。 |
| T-XP-PICKUP 經驗吸引與原生拾取冷卻 | Forge c4ec1880／Neo a1afba34 `XpDrainEffect.java`：每tick清takeXpDelay，每5tick掃8格，1.5格內逐球playerTouch後清冷卻 | [tickCustomEffects](../runtime/BP/scripts/bedrock/custom-effects.js)保留真球／原生拾取；沒有直接playerTouch／冷卻清除，未證完整Java時序、修補或多人歸屬一致 | [2026-11-06原生結果](../data/native-xp-pickup-20261106.json)：BDS1.26.60.6／server2.7＋GameTest1beta，真Player及每組8隻原版蠹魚死亡40XP、各24球；OFF21tick、正式Allium ON11tick，全取40／剩0。來源推導窄界為兩個Java owner pass、相隔最多5tick，未實跑Java對照、不歸因特定Bedrock內部冷卻。前3輪fixture失敗保留；未改runtime，不重複相同輸入。 |
| T-VISION-OUTLINE 感知穿牆輪廓 | Forge/Neo VisionEffect: 50-tick pulse, 60-tick Glowing, LivingEntity alive/AABB query before effects; radius6/12/18. | T132 fixes class selection including familyless vanilla fish, query-time membership and retained sound feedback. Native Glowing/through-wall rendering remains unavailable or unverified. | Source callback cases plus current native boat/cow/armor stand/cod observer; real Player behind opaque walls must still verify outline, duration and first/repeated-target sound. |

Grass Stealth的官方[experimental Entity.target](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/entity?view=minecraft-bedrock-experimental)同頁標成read-only，文字卻寫retrieves or sets（2026-11-05查閱）。採上述真引擎的唯讀結果；[reset_target](https://learn.microsoft.com/en-us/minecraft/creator/reference/content/entityreference/examples/eventactions/reset_target?view=minecraft-bedrock-stable)是資料驅動實體事件動作，不能當作任意原版mob已具備可呼叫事件。此觀察只封閉本次target setter路線，不推論其他版本永遠沒有入口；未重跑裝備元件探測，也不把測試器成功當成清除仇恨成功。
