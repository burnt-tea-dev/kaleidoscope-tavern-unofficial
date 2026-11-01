# T194 / W180 四側客戶端 checkpoint — 2026-11-01

**僅 Tavern 0.6.194 + World Liquor 0.1.180 各 BP/RP 四側；非六側、八側或全包驗收。** 原件私人封存；本公開文件僅為去識別摘要，不包含原圖、原始日誌或私人下載入口。未修改測試包，未部署。

## 固定來源與配置
- Tavern source commit: `d2905240f8590a8c9928ecf51d6c6611ff0f37ea`。
- World Liquor source commit: `56b4fc7ebde628b96948c2e5c495bf2a9685f866`。
- 安裝內容逐檔核對來源一致：T BP835/RP3232、W BP351/RP561。這是內容同一性，非公開 release archive hash 或 runtime 通過證明。
- Linux launcher / Android Bedrock **1.26.60.4**，鍵鼠，windowed1180×812（含頂20px選單），FOV60 / UI0。
- Creative 建 Classic Flat seed314159、Always Day、mobs OFF、Multiplayer OFF、Beta APIs ON；扣料測試切 Survival。Creator GUI/file ON，最高 **Verbose**。
- 正式配置兩種包優先順序均 **W > T**；早期錯序不作正式配置證據。沒有 Cookery，optional host未偵測不算章節失敗。

## 逐項限定結果
| 子項 | 結果 | 範圍與限制 |
|---|---|---|
| W布丁Survival單份完成使用 | bounded PASS | 1900ms完整使用後同slot碗1，背包無其他物。 |
| W布丁Survival疊2完成一次 | bounded PASS（最終守恆） | 布丁2→1、碗總1→2；未錄掉落瞬間，只證最終拾回+1。 |
| 布丁500ms取消及鬆手後換槽 | bounded PASS（此順序） | 布丁2碗2不變；先鬆手再換槽，不是持用中換槽競態。 |
| Creative布丁 | bounded PASS（觀察） | 完整1900ms後布丁仍2、碗總3；前態依操作記錄，後態背包直接核對。 |
| T指南英文及恢復繁中 | bounded PASS | 正常設定及Allium配方頁；不以效果detail英文直接推論翻譯BUG。 |
| 正常shaker配方／短按取消保留 | bounded PASS | shaker1、wine_q4×3、空杯1；放置三次投酒返瓶3；取起500ms取消，再4650ms完成，tooltip Allium Garden證實材料保留。正常背包挪副手後復原，未新增物。 |
| 空杯倒出及取成品 | bounded PASS | 倒入空杯，取起單份Allium；shaker無內容tooltip。 |
| 成品與材料世界重進保存 | bounded PASS | SaveQuit後重入：碗3、布丁2、guide1、瓶3、空shaker1、Allium1不變。不是完整程序重啟。 |
| Allium第一人稱完整可見 | FAIL（本視窗） | 右側及下邊界裁切；可見杯子不代表完整模型通過。 |
| 活動shaker動畫／HUD | NOT-RUN | 序列拍攝被hold阻塞，request前時間與response後elapsed不能冒充按住中段；製作成功不是動畫PASS。 |
| Allium飲用及XP Drain圖示開關 | bounded PASS | 喝1900ms返杯1；Hide後效果仍倒數且gameplay無icon，Enable後icon再現。只驗顯示開關，不是清除效果。 |
| 有效效果維度往返 | bounded PASS | Nether有icon、detail仍有效，返回Overworld仍有icon；正常間隔，不是快速tick競態或真portal流程。 |
| 牛奶取消／完成清除／再跨維度 | bounded PASS | 500ms取消仍有效，1900ms完成清除；再往返Nether/Overworld未見效果或icon復活。 |
| Tipsy自然到期顯示 | bounded PASS（圖示） | carignan_q6飲用後無輸入序列；detail最終無效果。首可見至消失約9.4–10.0秒，不稱tick精確10.000；粒子短暫殘留不等於效果有效。未驗移動/準確度等玩法。 |
| 兩唱片jukebox插入／取回／保存／破壞 | bounded PASS | 兩盤各插A/B，A取1；世界重入後B取1，空B不重複；重插B破壞實際掉唱片與jukebox，最後唱片2+jukebox1，A仍放置。 |
| 唱片牆掛及支撐破壞返還 | bounded PASS | 短300ms未生效，Shift1200ms成功；取回再掛，正常破壞背面支撐後短暫保留再掉落，回收到唱片2。未覆蓋全6種隨機牆圖。 |
| 唱片音效 | NOT-RUN | ALSA環境音訊限制，沒有聽覺PASS。 |
| 冷凍機正常配方及出料守恆 | bounded PASS | 葡萄1、slime1，原碗3布丁2；葡萄返bucket，關閉加工後開啟見白色成品；碗3→2、布丁2→3。再點是碗投入新配方而非重複產物，空手取回該碗後最終碗2布丁3。 |
| 冷凍機精確60秒／動畫時序 | 尚未核實 | 多次開啟輸入未生效，處理前景視窗後Shift600ms才開；不稱恰60秒，不推定doubletoggle根因。原圖88檔名complete-open錯，實為closed；原圖90較晚保存，RequiresBowl toast可能未被保存，僅當時操作觀察。 |
| 本輪GUI runtime錯誤檢查 | bounded PASS（無error） | entry、重進、final三次完整GUI Copy均0[error]；有未使用component等warning，不是零警告或整包保證。 |

20項中 **16 bounded PASS、1 viewport FAIL、2 NOT-RUN、1尚未核實**。只適用列出的操作與平台；不是全面PASS。

## 裁切最短重現
在上述W>T配置、FOV60、1180×812、UI0，正常完成Allium Garden配方並從空杯取得成品，第一人稱持用：杯模型被右側與下邊界裁切。保留原失敗，未藉改FOV或模型修改替換結果。此輪未做完整裁切根因驗證。

## 日誌和未測界線
- GUI Copy無時間戳，與原生filelog/stdout分開保存，沒有拼接。GUI含未使用component警告、optional Cookery未偵測、34 active recipes / 2 optional unavailable，符合四側配置。
- 原生Content Log已取得4096B、49行且末行截斷，0[error]僅限已取得內容，不稱完整會話。stdout另有大量unknown image type與JNI/ALSA環境訊息，不能稱零錯誤；正常關閉由操作確認，不補造exit尾行。
- 操作UTC換香港+8h；本次原日誌鐘面換翌日香港+15h，原時間未改。
- 原始定時截圖不是錄影，不能證明逐幀動畫/固定FPS。持用期間換槽競態、快速tick維度競態、全牆圖、完整聲音/Java配對等仍NOT-RUN或尚未核實。
- 第二真人、原生Windows、實體觸控/控制器、最低版本需另驗；六側/八側與後續Cookery測試不混入本輪。未測或環境受阻不由本輪代填通過。
