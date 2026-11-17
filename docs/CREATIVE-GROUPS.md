# Java 創造分頁與原序

本頁說明現行生成契約。版本與交付狀態見 `baseline.json`／`release-history.json`；部署與實際畫面查所屬 run。本頁不作部署或客戶端驗收記錄。

權威分類輸入是本包 [data/java-creative-tabs.json](../data/java-creative-tabs.json)：每列保留 Java ID、原分頁、位置、stack 狀態與 Bedrock ID。Forge 1.20.1 `c4ec1880`、NeoForge 1.21.1 `a1afba34` 的 `ModCreativeTabs.displayItems` 均為主頁、裝飾頁兩個線性列表。生成器不根據名稱、用途或檔名分類。 另讀未選用26.1.2來源 `9b8f165a`：主頁42項、裝飾83項，與維護分支不同，完整原序另存data的source branch，未混入本次生成。

| Java 頁 | 原生投影 | 圖示 | 成員 |
|---|---|---|---|
| tavern_main | Items 內一個群組 | 既有 wine_q6 | 依原作 displayItems，58項 |
| tavern_deco | Items 內一個群組 | 既有 stepladder | 依原作 displayItems，99項 |

這是原生群組對 Java 分頁邊界的適配，不是新增兩個頂部分頁。Bedrock 只有四個既有 category，不能原樣新增 Java 頂部分頁。普通葡萄酒圖示用既有 q6 ID；未新增物品。既有 guidebook、dragon_breath_bottle、honey_bottle、wild_grapevine 不在上述 Java 列表，明列為群組外 port 額外項，不混入原作序列。隱藏品質／放置實作及 item/block 配對保持。

`tools/creative/catalog.py` 是現行 producer，讀傳入 owner 的 `data/java-creative-tabs.json`，產生 catalog、可見定義的 menu_category 與三語群組標籤。World Liquor 也用此通用轉換器，但持有自己的列表；它按真 Java caller 擴展 Tavern 裝飾群組。Tavern 不持有 World Liquor 的分類。相對其他 addon 的顯示位置不由安裝順序特例控制。

`tools/creative/groups.json`、`data/creative-decoration-groups.json` 只供舊歷史摘要 consumer 讀取；已退出現行生成。舊用途表、共享原版圖示限制和 `--peer` 用途分類入口已退役，不能作本次 Java 順序的依據。

普通重產入口：`python3 tools/creative/catalog.py --write`。檢查另一包時使用 `--root <owner-source>`。跨包 CI 分別檢查兩個 owner，不再呼叫 `--peer`、`taxonomy()` 或 `check_pair()`。

生成器拒絕重複成員、未列入計畫的可見項，以及計畫要求卻沒有可見定義的項。缺少 catalog 登記但已有可見定義的項仍可正常補回。明列 `unavailable` 的 Java stack 保留為缺口，不冒稱可取得。

`tools/creative/test_catalog.py` 依本包計畫比對完整分頁、成員原序、作者代表 icon 和明列的 port 額外項。群組內順序與跨包群組成員分開檢查；同名擴展的標籤與 icon 須一致。舊用途分類與「只能用原版 icon」已退出現行測試。舊格式定義可不寫 menu group，catalog 仍保留該群組。隱藏或未宣告 menu 的實作半部不作可見定義。

歷史 metadata 投影只核對歷史輸入；現行定義由現行生成器核對。測試保留未審 menu、玩法變動及未受影響素材的負例，不拿舊整檔後像鎖住現行玩法。

能力依據：[Microsoft crafting item catalog](https://learn.microsoft.com/en-us/minecraft/creator/documents/craftingitemcatalogdocumentation?view=minecraft-bedrock-stable)（2026-11-10 查閱）。自訂 item 可作群組圖示；同名群組會合併，新增項只能附加。乾淨 Cookery 1.6.6 作者包同樣直接使用顯式 catalog 與自有 item 圖示；它的15個食物／設備群組不是其他 addon 的分類模板。
