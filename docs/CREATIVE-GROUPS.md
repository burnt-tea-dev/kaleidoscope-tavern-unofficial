# 共用創造分類

以下分類自酒館 0.6.46／世界名酒 0.1.9 起採用。

依照廚房本體慣例，自訂物品集中在「裝備」頁，以原生可展開的分類呈現。酒館本體和附屬共用分類名稱、代表圖標及順序。

| 順序 | 分類 | 內容 |
|---|---|---|
| 1 | 作物 | 葡萄、葡萄藤、野生葡萄藤與藤架 |
| 2 | 原料與調酒材料 | 果汁桶、蜂蜜瓶、龍息瓶、可樂、通寧水 |
| 3 | 釀造與調酒設備 | 果盆、酒嘴、酒桶、雪克杯、空瓶杯、冰櫃 |
| 4 | 酒飲 | 酒瓶與其他瓶裝飲料；品質分級品保留原來的創造代表品質 |
| 5 | 雞尾酒 | 可供飲用的杯裝成品 |
| 6 | 收納 | 酒櫃、酒窖櫃、酒架及杯架 |
| 7 | 家具 | 桌子、吧檯、沙發、高腳凳及附屬圓凳 |
| 8 | 燈飾 | 燈串與吊燈 |
| 9 | 裝飾 | 告示牌、黑板、掛畫、香薰及唱片 |
| 10 | 工具 | 梯具、莫洛托夫燃燒瓶 |

附屬食物繼續接入廚房的食物分類。顏色和木種保持各自連續的順序；兩個包合併後仍是同一分類。

分類由 `tools/creative/groups.json` 及各包 `data/creative-decoration-groups.json` 生成。附屬不能為同名分類換另一個圖標。現行可見物品為酒館 161（含獨立指南）、世界名酒 66；此次修正不改變物品 ID、配方、隱藏實作方塊及可見物品集合。

分類資料測試不模擬玩家或創造介面。

## 0.6.186 來源候選：相容標籤與 Java 酒飲順序

沿用既有 legacy 分類修正：五個語言檔提供 `wines_spirits`、`cultivation`、`barware_bottles`、`decorations_lighting`，分別重用該語言現有的 `wines`、`tavern_cultivation`、`empty_bottles`、`tavern_decor` 標籤。日文／俄文的現有英文 fallback 用詞維持原樣；沒有第二套翻譯生成 owner。相同標籤不代表 group ID 合併，也不變更其他附屬的分類、圖示、成員或順序。舊 `cultivation` 組亦可能包含果汁桶；此相容補丁保留既有用詞，未重新設計其語意分類。

本體 `wines` 組內 25 個既有可見飲品依 Java `ModCreativeTabs` 的相對順序排列：西瓜汁、醋，接著依普通葡萄、冰葡萄、黃金葡萄、青提、發光漿果、甜漿果、水的原料系列排列。品質酒仍使用既有 `_q6` 代表品，可見集合、圖示及其餘組內順序保持。

原始來源：[Java 1.21.1](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/a1afba34981a00e89d57130d3dc8f1e64f1820a2/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/init/ModCreativeTabs.java#L41-L80)。這個 25 項序列也與本輪檢查的 [main](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/c4ec1880bd44cf3139d3ba744ab30bb379cf1416/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/init/ModCreativeTabs.java) 及 [26.1.2](https://github.com/KaleidoscopeMods/KaleidoscopeTavern/blob/9b8f165a4641e738e694641dd81240a0206573e1/src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/init/ModCreativeTabs.java) 一致。

Catalog 由既有生成器的 current contract 管理。過時的 catalog 歷史 postimage 與 launch aggregate 項目已移除，未新增反向差異或改寫其他歷史雜湊。`catalog.py --java-source <Java checkout>` 以及 `check_launch.py --java-source <Java checkout>` 會把實際可見酒飲、reviewed plan 和 Java 的 `output.accept` 順序相互核對；缺項、重複或錯序均失敗。

完整包組的共享圖示優先序、舊酒飲分類點擊開錯組的原因、實機展開／收起仍未通過。資料檢查不代表 Java 的兩個原生分頁、聲音、畫面或互動已完整還原。
