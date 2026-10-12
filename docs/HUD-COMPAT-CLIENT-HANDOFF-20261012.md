# Dot：本輪 HUD 實測入口

本輪 **T149／G130／W126／私有料理1.0.34** 已於 **2026-10-13 00:29:50 HKT** 部署luosen，完整42包、BDS1.26.52.3 RUNNING；canonical PR／CI、static、停服存檔first／restart、准入及逐檔／順序讀回通過。[公開下載核對](../family/PUBLIC-DOWNLOAD-LIVE-HUD-20261013.md)確認三個mcaddon的六份自有包9343檔與准入／LIVE完全相等。真人仍未驗收，請以luosen正常提供的完整家族測以下同一流程。G126單包no-clear、T147 HUD200及T148的原證據保持原範圍，不重標成當前通過。

P34新增指南有界接收，P33配方快取、料理／renderer32與ChineseFood1.0.10432保留。現場AMW2.6.28、JavaSaturation1.5.5、UIQueue1.6.10034為登記相容變體，玩法／資產由私有canonical保全。Node模組差分75→7次鍋類重建不是BDS watchdog改善證據。

Poststart **292 warnings／0 errors**、**265 watchdog（9 Spike／254 Slowdown／2 High Memory）**；T仍2／75、G1／39、W1／81、Cookery1／20筆Spike／Slowdown。W最大Spike1479→284ms但54.892／75.552秒採樣窗口不同，不能宣稱全局效能改善。QA工具PR340保留LIVE明確100／10ms门檻；舊QA未設定值會關閉對應告警，其載入／保存通過不等於效能通過。

## 本次要分辨的缺陷

T148／G129已把renderer移到獨立命名空間及共用可選掛載，解開原同路徑factory覆蓋。本輪T149／G130进一步把圖形移出共享Actionbar，使用命名空間封包／已觀測可選UI Queue或title路由、獨立最新快照及明確END。原圖、游標、時間與食物結算保持；新來源CI及BDS不等於已執行客戶端renderer，任意未協調title寫入與第三方完整HUD覆蓋仍待確認。

## 先解除上游讀檔與資源包辨認阻塞

Windows SSH的DNS／networkDenied失敗不需要卡住此檔案的唯讀查核：透過GitHub connector已能取得[本輪BSM原檔快照](../family/JAVA-UPSTREAM-READONLY-20261012.md)，檢查時間2026-10-12 18:23:03 HKT，按內附SHA辨認同一份JSON，再和 `family/java-upstream.json` 一起查核。本機連線／任務執行狀態仍未知；快照不是永久最新來源，原檔的新版本／適配與parity pending狀態保持。

Dot既有回歸記錄：取消保留物品、完成後進度正常退出、調酒裝料／返瓶／產出通過，但快速重開仍見兩次短暫空條。這些觀察尚未附可核對的候選與客戶端版本；保留各場景結果，不挪作T149／G130驗收。先確認實際LIVE、客戶端BP／RP UUID／版號、完整堆疊與GUI profile／比例，優先查資源包快取及載入優先序。正常退出客戶端並重新接受已更新的伺服器資源包後，只重錄下面同一流程；沒有明確新失敗時不再轉入隔離camera／hold微調或重跑舊影片。

## 一次正常玩家流程

1. 重新加入更新完成的luosen，正常接受伺服器資源包。保留客戶端content log，先確認快捷欄、準星、飢餓／血量、JavaSaturation及AMW現有29通道HUD均存在。
2. 以正常玩家實際食用煙火食物，完整吃一份，再重吃並中途放開／換槽，接著快速重新開始。錄下102像素原圖進度條、黃轉綠、物品圖示、停止後自然消失及是否短暫空條；不可用人工封包播放代替自然食用。
3. 正常開始調酒，核對槽位、游標及進度；停止後回到煙火食用。另以正常飲用帶出酒館／世界名酒效果圖示，確認它們不使原生與 AMW 控件消失。
4. 在圖形活動與結束後觸發其他addon的普通Actionbar提示，核對它仍顯示且不被END清空；同時檢查AMW與飽和度。若只在另一addon寫title時缺幀，記錄具體addon、時間和來源，與資源包掛載／快取問題分開處理。

最小回報包含實際 LIVE 版本、客戶端版本／裝置、GUI 比例／輸入方式，以及一次上述流程的影片和同期 UI 錯誤原文。先確認完整堆疊下兩個圖形都能掛載，再針對真實失敗縮小來源；不反覆用隔離成功影片代替 LIVE 驗證。

## 保留的邊界

Minecraft的Actionbar／title各有共享邊界；本輪自有圖形不覆寫Actionbar，但任意title寫入與第三方完整替換HUD仍不能保證相容。登記第三方HUD變體的來源CI／保全與fresh native不算客户端聲畫驗收。圖形時序、食用結算與普通訊息保持；`client=false`、`production_ready=false`及`pending_client_acceptance`保留，真人回報須另記原始候選／場景。作者料理快取／指南回饋尚待送達，不能當作者已接收修正。
