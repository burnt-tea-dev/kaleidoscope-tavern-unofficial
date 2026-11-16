# Java 創造分頁與原序

2026-11-11 本機整合；版本固化狀態見 `baseline.json`／`release-history.json`。未發布或部署，未執行測試；畫面與「＋不展開」原因仍未確認。

權威分類輸入是本包 [data/java-creative-tabs.json](../data/java-creative-tabs.json)：每列保留 Java ID、原分頁、位置、stack 狀態與 Bedrock ID。Forge 1.20.1 `c4ec1880`、NeoForge 1.21.1 `a1afba34` 的 `ModCreativeTabs.displayItems` 均為主頁、裝飾頁兩個線性列表。生成器不根據名稱、用途或檔名分類。 另讀未選用26.1.2來源 `9b8f165a`：主頁42項、裝飾83項，與維護分支不同，完整原序另存data的source branch，未混入本次生成。

| Java 頁 | 原生投影 | 圖示 | 成員 |
|---|---|---|---|
| tavern_main | Items 內一個群組 | 既有 wine_q6 | 依原作 displayItems，58項 |
| tavern_deco | Items 內一個群組 | 既有 stepladder | 依原作 displayItems，99項 |

這是原生群組對 Java 分頁邊界的適配，不是新增兩個頂部分頁。Bedrock 只有四個既有 category，不能原樣新增 Java 頂部分頁。普通葡萄酒圖示用既有 q6 ID；未新增物品。既有 guidebook、dragon_breath_bottle、honey_bottle、wild_grapevine 不在上述 Java 列表，明列為群組外 port 額外項，不混入原作序列。隱藏品質／放置實作及 item/block 配對保持。

`tools/creative/catalog.py` 是現行 producer，讀傳入 owner 的 `data/java-creative-tabs.json`，產生 catalog、可見定義的 menu_category 與三語群組標籤。World Liquor 也用此通用轉換器，但持有自己的列表；它按真 Java caller 擴展 Tavern 裝飾群組。Tavern 不持有 World Liquor 的分類。相對其他 addon 的顯示位置不由安裝順序特例控制。

`tools/creative/groups.json`、`data/creative-decoration-groups.json` 只供舊歷史摘要 consumer 讀取；已退出現行生成。舊用途表、共享原版圖示限制和 `--peer` 用途分類入口已退役，不能作本次 Java 順序的依據。

普通重產入口：`python3 tools/creative/catalog.py --write`。本題只生成分類、定義與語系，不執行其檢查選項、測試或整包發布。

能力依據：[Microsoft crafting item catalog](https://learn.microsoft.com/en-us/minecraft/creator/documents/craftingitemcatalogdocumentation?view=minecraft-bedrock-stable)（2026-11-10 查閱）。自訂 item 可作群組圖示；同名群組會合併，新增項只能附加。乾淨 Cookery 1.6.6 作者包同樣直接使用顯式 catalog 與自有 item 圖示；它的15個食物／設備群組不是其他 addon 的分類模板。
