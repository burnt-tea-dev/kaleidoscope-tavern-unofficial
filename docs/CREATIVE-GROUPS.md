# 共用創造分類

創造清單按用途放進原生四頁。群組使用簡短名稱，不再把作物、酒飲、家具一律放到裝備頁。

| 原生頁 | 群組與內容 |
|---|---|
| 建築 | 收納、家具、燈飾、告示牌、畫作 |
| 裝備 | 真正的工具（梯具、雪克杯）、投擲物（燃燒瓶） |
| 物品 | 指南與食譜、釀造原料、釀造設備、餐飲設備、瓶罐與杯具、酒飲、雞尾酒、香薰、唱片、料理 |
| 自然 | 作物與種子（葡萄、葡萄藤、野生藤與藤架） |

果汁桶留在釀造原料；指南不混入設備；空瓶與空杯不混入釀造設備。酒飲組保持原 Java 可見代表品及其相對順序，品質分級品、所有原可見物品與原隱藏實作保持原有可見性。顏色和木種也保持各自連續順序。

資料來源仍是 `tools/creative/groups.json` 與各包 `data/creative-decoration-groups.json`，由真正的 `tools/creative/catalog.py` 產生 catalog、可見定義的 menu_category 與三語標籤。同名共享組使用同一個真原版圖示，附屬不再用另一個包內圖示覆蓋；不需要新物品、腳本選單或第二套分類介面。

這些資料檢查驗證分類、集合與生成器一致，不模擬玩家、分頁展開或實際創造畫面。

普通發布以目前的生成器檢查 menu 與 catalog。舊 menu／整檔聚合雜湊只保留為歷史；不再把舊裝備頁分類還原後才能接受新用途。遊戲行為檢查、UUID／相依、實際發布內容與 append-only 身份保護仍保留。

世界名酒原本可見的綠色、粉色吊燈漏在 catalog 之外。本次讓其原生成 owner 與分類來源一致，補回這兩個既有 ID 的目錄項；沒有新增物品或公開隱藏的品質／實作方塊。

## 0.6.186 來源候選：相容標籤與 Java 酒飲順序

沿用既有 legacy 分類修正：五個語言檔提供 `wines_spirits`、`cultivation`、`barware_bottles`、`decorations_lighting`，分別重用該語言現有的 `wines`、`tavern_cultivation`、`empty_bottles`、`tavern_decor` 標籤。日文／俄文的現有英文 fallback 用詞維持原樣；沒有第二套翻譯生成 owner。相同標籤不代表 group ID 合併，也不變更其他附屬的分類、圖示、成員或順序。舊 `cultivation` 組亦可能包含果汁桶；此相容補丁保留既有用詞，未重新設計其語意分類。

本體 `wines` 組內 25 個既有可見飲品依 Java `ModCreativeTabs` 的相對順序排列：西瓜汁、醋，接著依普通葡萄、冰葡萄、黃金葡萄、青提、發光漿果、甜漿果、水的原料系列排列。品質酒仍使用既有 `_q6` 代表品，可見集合、圖示及其餘組內順序保持。

原始來源：[Java 1.21.1](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/a1afba34981a00e89d57130d3dc8f1e64f1820a2/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/init/ModCreativeTabs.java#L41-L80)。這個 25 項序列也與本輪檢查的 [main](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/init/ModCreativeTabs.java) 及 [26.1.2](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/9b8f165a4641e738e694641dd81240a0206573e1/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/init/ModCreativeTabs.java) 一致。

Catalog 由既有生成器的 current contract 管理。過時的 catalog 歷史 postimage 與 launch aggregate 項目已移除，未新增反向差異或改寫其他歷史雜湊。`catalog.py --java-source <Java checkout>` 以及 `check_launch.py --java-source <Java checkout>` 會把實際可見酒飲、reviewed plan 和 Java 的 `output.accept` 順序相互核對；缺項、重複或錯序均失敗。

完整包組的共享圖示優先序、舊酒飲分類點擊開錯組的原因、實機展開／收起仍未通過。資料檢查不代表 Java 的兩個原生分頁、聲音、畫面或互動已完整還原。
