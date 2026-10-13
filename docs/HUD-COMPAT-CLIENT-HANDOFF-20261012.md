# Dot：本輪 HUD 實測入口

**2026-10-13 17:05:52 HKT**：luosen **T155／G133／W132／P34／Ribbits1.0.10037**，42包正常運行。來源CI、完整家族static、停服存檔first／restart及安裝讀回均通過；[本次公開下載與LIVE證據](../family/PUBLIC-DOWNLOAD-LIVE-PERSISTENT-HUD-20261013.md)。`client=false`、`production_ready=false`。

使用者已明確回報進食與調酒圖形全無、原版與AMW正常。新版本移除調酒progress父層舊` / 111`條件，兩套圖形改常駐獨立快取，正常結束或漏更新送自己的END。進食缺失的實際引擎原因仍未由客戶端證實；不要把來源條件測試或BDS當圖形已恢復。

先重連接受新資源包，記錄T155／G133／W132與GUI profile／比例，確認首次進食及首次調酒是否顯示；之後測完成、取消、連續使用及AMW同時顯示。進食時間與材質保留；調酒游標按server tick更新，partial-tick插值待完成。Poststart165 warnings／0 errors，watchdog仍138條，不宣稱整體效能修好。

## 先解除上游讀檔與資源包辨認阻塞

本輪已讀取BSM原始JSON，檢查時間 **2026-10-13 12:23:03 HKT**；`all_reference_release_metadata_current=false`、`full_java_parity_verified=false`保持。正式修補仍須讀BSM的 `addon_quality/senluo-java-upstream-status.json` 與 `family/java-upstream.json`，過期時重新查核。原[公開歷史快照](../family/JAVA-UPSTREAM-READONLY-20261012.md)只屬10/12原查核；取得伺服器端資料不代表Dot本機DNS／任務通道已修復。

Dot既有回歸記錄：取消保留物品、完成後進度正常退出、調酒裝料／返瓶／產出通過，但快速重開仍見兩次短暫空條。這些觀察尚未附可核對的候選與客戶端版本；保留各場景結果，不挪作T155／G133驗收。先確認實際LIVE、客戶端BP／RP UUID／版號、完整堆疊與GUI profile／比例，優先查資源包快取及載入優先序。正常退出客戶端並重新接受已更新的伺服器資源包後，只重錄下面同一流程；沒有明確新失敗時不再轉入隔離camera／hold微調或重跑舊影片。

## 一次正常玩家流程

1. 重新加入更新完成的luosen，正常接受伺服器資源包。保留客戶端content log，先確認快捷欄、準星、飢餓／血量、JavaSaturation及AMW現有29通道HUD均存在。
2. 以正常玩家實際食用煙火食物，完整吃一份，再重吃並中途放開／換槽，接著快速重新開始。錄下102像素原圖進度條、黃轉綠、物品圖示、停止後自然消失及是否短暫空條；不可用人工封包播放代替自然食用。
3. 正常開始調酒，核對槽位、游標及進度；停止後回到煙火食用。另以正常飲用帶出酒館／世界名酒效果圖示，確認它們不使原生與 AMW 控件消失。
4. 在圖形活動與結束後觸發其他addon的普通Actionbar提示，核對它仍顯示且不被END清空；同時檢查AMW與飽和度。若只在另一addon寫title時缺幀，記錄具體addon、時間和來源，與資源包掛載／快取問題分開處理。

另以正常玩家觀察Ribbits自然生成／connection／周邊互動，保留同期內容日誌；不可用模擬玩家／人工connection播放、另建LIVE世界或改正式實驗功能代替。

最小回報包含實際 LIVE 版本、客戶端版本／裝置、GUI 比例／輸入方式，以及一次上述流程的影片和同期 UI 錯誤原文。先確認完整堆疊下兩個圖形都能掛載，再針對真實失敗縮小來源；不反覆用隔離成功影片代替 LIVE 驗證。

## 保留的邊界

Minecraft的Actionbar／title各有共享邊界；本輪自有圖形不覆寫Actionbar，但任意title寫入與第三方完整替換HUD仍不能保證相容。登記第三方HUD變體的來源CI／保全與fresh native不算客户端聲畫驗收。圖形時序、食用結算與普通訊息保持；`client=false`、`production_ready=false`及`pending_client_acceptance`保留，真人回報須另記原始候選／場景。作者料理快取／指南回饋尚待送達，不能當作者已接收修正。
