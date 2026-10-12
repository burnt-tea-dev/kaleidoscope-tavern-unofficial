# Dot：本輪 HUD 實測入口

本輪 T148／G129／W125／私有料理1.0.33 已於 **[private deployment time]** 部署 managed-server，完整42包、BDS1.26.52.3 RUNNING；static、停服存檔副本first／restart、准入及正常啟動讀回通過。[公開下載核對](../family/PUBLIC-DOWNLOAD-LIVE-UI-20261012.md)已確認三個mcaddon的六份自有包9339檔與准入／LIVE完全相等。真人仍未驗收，請以managed-server正常提供的完整家族測以下同一流程。先前G126單包no-clear影片及T147 HUD200影片保持原範圍。

private-integration只增加Cookery1.6.0配方快取按需重建；料理／renderer32與ChineseFood1.0.10432保留。Node模組差分六批次75→7次鍋類重建不是BDS watchdog改善證據。Poststart313 warnings／0 errors，LIVE慢速警告仍存在；真人效能需另記本輪版本與現場。

## 本次要分辨的缺陷

T147 與 G128 把各自圖形及 root modifications 放在同一路徑 `ui/hud_screen.json`，managed-server 的酒館資源包在煙火之上；兩包的原生訊息過濾亦不同。即使單包成功，完整堆疊仍可能漏掉另一側的圖形工廠。本輪把兩個 renderer 移入獨立已登記命名空間，兩包共用同一個可選掛載橋接，並共同排除內部封包。靜態檢查驗了原生 29 個控制、兩個命名空間、缺包空面板及相同橋接，尚未執行客戶端 renderer。

## 先解除上游讀檔與資源包辨認阻塞

Windows SSH的DNS／networkDenied失敗不需要卡住此檔案的唯讀查核：透過GitHub connector已能取得[本輪BSM原檔快照](../family/JAVA-UPSTREAM-READONLY-20261012.md)，檢查時間2026-10-12 18:23:03 HKT，按內附SHA辨認同一份JSON，再和 `family/java-upstream.json` 一起查核。本機連線／任務執行狀態仍未知；快照不是永久最新來源，原檔的新版本／適配與parity pending狀態保持。

Dot既有回歸記錄：取消保留物品、完成後進度正常退出、調酒裝料／返瓶／產出通過，但快速重開仍見兩次短暫空條。這些觀察尚未附可核對的候選與客戶端版本；保留各場景結果，不挪作T148／G129驗收。先確認實際LIVE、客戶端BP／RP UUID／版號、完整堆疊與GUI profile／比例，優先查資源包快取及載入優先序。正常退出客戶端並重新接受已更新的伺服器資源包後，只重錄下面同一流程；沒有明確新失敗時不再轉入隔離camera／hold微調或重跑舊影片。

## 一次正常玩家流程

1. 重新加入更新完成的 managed-server，正常接受伺服器資源包。保留客戶端 content log，先確認快捷欄、準星、飢餓／血量及 AMW 現有 HUD 均存在。
2. 以正常玩家實際食用煙火食物，完整吃一份，再重吃並中途放開／換槽，接著快速重新開始。錄下102像素原圖進度條、黃轉綠、物品圖示、停止後自然消失及是否短暫空條；不可用人工封包播放代替自然食用。
3. 正常開始調酒，核對槽位、游標及進度；停止後回到煙火食用。另以正常飲用帶出酒館／世界名酒效果圖示，確認它們不使原生與 AMW 控件消失。
4. 在圖形結束後觸發一個其他 addon 的普通 Actionbar 提示，核對它仍顯示且不被結束流程清空。若同時寫入 Actionbar 才出現缺幀，記錄具體 addon、時間和封包來源，與本輪掛載／命名空間問題分开處理。

最小回報包含實際 LIVE 版本、客戶端版本／裝置、GUI 比例／輸入方式，以及一次上述流程的影片和同期 UI 錯誤原文。先確認完整堆疊下兩個圖形都能掛載，再針對真實失敗縮小來源；不反覆用隔離成功影片代替 LIVE 驗證。

## 保留的邊界

Minecraft 的 Actionbar 是共享通道。圖形掛載修復不保證兩個 addon 同一 tick 都成功覆寫該通道，也不能控制第三方完整替換 HUD 的行為。本輪未更改圖形時序、食用結算、普通訊息或第三方包。CI、BDS 與存檔通過後仍保留 `client=false`、`production_ready=false` 及 `pending_client_acceptance`，真人回報須另記原始候選／場景。
