# Dot：本輪 HUD 實測入口

**2026-10-13 16:00:25 HKT**：luosen **T154／G132／W131／P34／Ribbits1.0.10037**，42包，BDS1.26.52.3 RUNNING。Canonical PR／必要CI、static、一次停服存檔副本first／restart、完整准入及逐檔／順序讀回通過。`client=false`、`production_ready=false`、`pending_client_acceptance`。

Ribbits1.0.10037只替換FP存檔載入的一處同步Base64解壓呼叫，六位元緩衝解碼保留原UTF16字典結果；異常／非標準輸入交回原方法。保存格式、序列化、property keys、回呼、既有connection修補及其餘資產保留；配對manifest由canonical compiler生成。T154／G132／W131及P34輸出不變。

本次poststart **172 warnings／0 errors**；watchdog **145（8 Spike／137 Slowdown／0 High Memory）**，其中Ribbits啟動Spike **253ms**。存檔first／restart的Ribbits為261／267ms。這些是不同啟動窗口的觀察，不作整體效能百分比或完整watchdog驗收。

[本次部署證據](../family/RIBBITS-FP-DECODE-LIVE-20261013.md)；本輪沒有更新T／G／W或HUD輸出，既有快開短空條回報仍待候選明確的真人複驗。

## 本次要分辨的缺陷

T148／G129已把renderer移到獨立命名空間及共用可選掛載，解開原同路徑factory覆蓋。已部署的T149／G130修補进一步把圖形移出共享Actionbar，使用命名空間封包／已觀測可選UI Queue或title路由、獨立最新快照及明確END。原圖、游標、時間與食物結算保持；新來源CI及BDS不等於已執行客戶端renderer，任意未協調title寫入與第三方完整HUD覆蓋仍待確認。

## 先解除上游讀檔與資源包辨認阻塞

本輪已讀取BSM原始JSON，檢查時間 **2026-10-13 12:23:03 HKT**；`all_reference_release_metadata_current=false`、`full_java_parity_verified=false`保持。正式修補仍須讀BSM的 `addon_quality/senluo-java-upstream-status.json` 與 `family/java-upstream.json`，過期時重新查核。原[公開歷史快照](../family/JAVA-UPSTREAM-READONLY-20261012.md)只屬10/12原查核；取得伺服器端資料不代表Dot本機DNS／任務通道已修復。

Dot既有回歸記錄：取消保留物品、完成後進度正常退出、調酒裝料／返瓶／產出通過，但快速重開仍見兩次短暫空條。這些觀察尚未附可核對的候選與客戶端版本；保留各場景結果，不挪作T154／G132驗收。先確認實際LIVE、客戶端BP／RP UUID／版號、完整堆疊與GUI profile／比例，優先查資源包快取及載入優先序。正常退出客戶端並重新接受已更新的伺服器資源包後，只重錄下面同一流程；沒有明確新失敗時不再轉入隔離camera／hold微調或重跑舊影片。

## 一次正常玩家流程

1. 重新加入更新完成的luosen，正常接受伺服器資源包。保留客戶端content log，先確認快捷欄、準星、飢餓／血量、JavaSaturation及AMW現有29通道HUD均存在。
2. 以正常玩家實際食用煙火食物，完整吃一份，再重吃並中途放開／換槽，接著快速重新開始。錄下102像素原圖進度條、黃轉綠、物品圖示、停止後自然消失及是否短暫空條；不可用人工封包播放代替自然食用。
3. 正常開始調酒，核對槽位、游標及進度；停止後回到煙火食用。另以正常飲用帶出酒館／世界名酒效果圖示，確認它們不使原生與 AMW 控件消失。
4. 在圖形活動與結束後觸發其他addon的普通Actionbar提示，核對它仍顯示且不被END清空；同時檢查AMW與飽和度。若只在另一addon寫title時缺幀，記錄具體addon、時間和來源，與資源包掛載／快取問題分開處理。

另以正常玩家觀察Ribbits自然生成／connection／周邊互動，保留同期內容日誌；不可用模擬玩家／人工connection播放、另建LIVE世界或改正式實驗功能代替。

最小回報包含實際 LIVE 版本、客戶端版本／裝置、GUI 比例／輸入方式，以及一次上述流程的影片和同期 UI 錯誤原文。先確認完整堆疊下兩個圖形都能掛載，再針對真實失敗縮小來源；不反覆用隔離成功影片代替 LIVE 驗證。

## 保留的邊界

Minecraft的Actionbar／title各有共享邊界；本輪自有圖形不覆寫Actionbar，但任意title寫入與第三方完整替換HUD仍不能保證相容。登記第三方HUD變體的來源CI／保全與fresh native不算客户端聲畫驗收。圖形時序、食用結算與普通訊息保持；`client=false`、`production_ready=false`及`pending_client_acceptance`保留，真人回報須另記原始候選／場景。作者料理快取／指南回饋尚待送達，不能當作者已接收修正。
