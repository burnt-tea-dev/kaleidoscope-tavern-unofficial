# 黑板 raw multiline：單人正常 wire 契約

這是 QA-only observer，不是另一個遊戲包，也不自行開 BDS。共同持有者在既有同 copy 的 functional phase，將 `observer.js` 複製到 **Tavern BP 的 scripts 根目錄**，在原 `main.js` 最後 import 它；正式包、LIVE 與正式 DB 不加入此檔。使用固定單一 `qaNetPlain`，原 driver 身份／限額不變。等固定來源與 root 的正常 form wire 接線 ready 才排槽，不使用舊 v12 的無表單能力路徑。

observer 只在共同的單次 prepare 事件後，在 QA 區域建立小黑板與平台，使用 owner 的 `normalizeBoardData`／`boardRuntimeKey` 準備一次 seed，移動玩家至八格範圍內。不因 `getAllPlayers` 已看見 actor 就開始；登入中的 actor 也會被列出。它不呼叫 `editBoard`、不呼叫 `ModalFormData.show`、不攔截或偽造 form reply。**READY 後沒有保存鍵、方塊或玩家寫入；只觀察正常點擊與 owner 保存結果。** 開始時手上必須為空，否則明確 fail。

0. 等 `TAVERN_QA_BOARD_LOGIN_READY`，沿既有 driver 正常登入。**共同必須先拿到真 driver spawn 與 `initial_loading_end`，才由原 BDS console 送一次 `scriptevent kt_qa:board_prepare`。** 保留這兩個 wire 時點與 console prepare 記錄。observer 收事件後才 teleport，20tick 延遲只用來載入新位置的 QA chunk，不用來猜登入完成；收到 `PREPARING`／`READY` 後 driver 已在正常 ReadPacket 路徑觀察場景更新。沒送 prepare 就不建場景；缺 wire/loading 證據不能判功能陰性。

1. 等 `TAVERN_QA_BOARD_READY`。使用其中的 `rotation`／`lookAt`，按正常 `look`、`use_block` 點 `targetBlock` 的 North 面。板面薄片的 North 表面在 block-local z=.9375，READY 的目標取板內 z=.95；位置／角度都由 log 記錄。不要用腳本事件開表單。
2. driver 必須真正收到 **ModalFormRequest**，解析 JSON 並逐項核對：黑板專屬 `custom_form`、完整 title 的 `§r§0§r` 前綴、恰好 input／dropdown／dropdown、第一欄 default 逐字等於 READY 的 `form.defaultText`，另外兩欄 default 為 `[1,1]`。保留真 packet id／type／shape 與完整 default 比對成功的記錄即可；不要求把 text／body 寫進 driver log。預設文字含真正 newline、字面反斜線+n 與路徑 `C:\new\log`；JSON 解碼後比較原文字，不能拿 log 中的轉義外觀判斷。
3. 經 root 的正常 wire **ModalFormResponse** 回覆收到的 form id **一次**，值直接取 READY 的 `form.response`：`[rawText,4,2]`。`rawText` 第一行改為 `edit`；另外兩個值是 distributed、bottom。不能在 observer 寫保存鍵、呼叫內部 edit 函式或使用 fixture response。
4. 收 `TAVERN_QA_BOARD_RESULT`。`owner_save_observed` 表示真點擊已被觀察，原 owner 恰好保存一次，原文、對齊、blue／glowing／waxed 及兩半方塊狀態正確。**共同只有在 driver 的真 request/default/response 證據也吻合時，才可判 wire＋保存通過**。結果本身不是 Native PASS。缺少表單或沒有保存時是 inconclusive；不能略過表單，把 timeout 判成 T 功能陰性。

seed 與提交原文分別為（程式的實際字串以 READY 為準）：

```text
seed                    edit
literal \n      →       literal \n
C:\new\log              C:\new\log
```

原存檔的 `text` 一直是 raw string，沒有遷移或重解碼。既有實作在提交後仍重查玩家互動資格、方塊／root identity、八格 reach、原資料是否已變與 Wax，再檢查原長度／layout。`tools/board-farm-interaction.test.mjs` 走真註冊 interaction 與實際提交 callback，涵蓋 raw round trip、三種容量及 mode／reach／stale 拒絕；這些 API-double 回歸與本 wire 證據分開。這個單次 wire 場景不另宣稱已原生覆蓋全部負面控制。

不混入保存 gate 的原玩家 before/after，QA DB 不覆回 LIVE。結束沿共同原正常 leave／stop／清理流程。這輪只能證 **wire 表單與保存**；不證實體 Enter、IME、手機／手把、畫面、捲動／caret 或重新載入。它們不是新增真人完成門檻。無新 world／候選／包身份，只為既有 functional phase 提供入口。
