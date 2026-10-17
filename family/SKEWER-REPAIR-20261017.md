# G151 串流程修補的家族配套

2026-10-17 玩家回報串配方匹配、已穿食材不顯示與空內容進食。本批由三代理修補 [Grilling PR231](https://github.com/casama233/kaleidoscope-grilling-unofficial/pull/231)，Tavern 承接完整家族組裝所需的精確 public API 准入。Grilling 的[完整來源修補](https://github.com/casama233/kaleidoscope-grilling-unofficial/blob/main/docs/evidence/skewer-repair-20261017.md)和[原料生產證據](https://github.com/casama233/kaleidoscope-grilling-unofficial/blob/main/docs/evidence/skewer-input-repair-20261017.md)持有玩法細節。

## 配套身份

| 項目 | 本批來源 |
| --- | --- |
| Grilling | G151／2.8.151，配對 BP/RP 與凍結 source trees 由家族鎖和 G baseline 精確綁定 |
| 作者 Cookery | 1.6.1，file 9123386；兩側 UUID 和 archive SHA 保持現行核對值 |
| Public family API | 0.2.12；砧板保存 schema 仍為 0.1.0 |
| Tavern／World Liquor | T173／W151；本次配套未修改兩者 runtime |
| 私有整合 | 本次沒有新的 private runtime 或准入結果；不能由公開配套推定其版本或依賴已完成更新 |

G150 對 Cookery 1.6.1 的砧板前置契約仍期待兩份單一產出；作者實際已改為牛肉內臟三份、雞肉三份肉塊加一骨頭。因此註冊成功仍選不到 Grilling 的牛肉塊／雞皮流程。G151 的 copied board modules 支援精確的多產出聲明，保留作者雞肉／骨頭、既有雞皮補充、牛肉塊替換及交易回滾。

## Tavern 的有限改動

`stable_host_profiles.json` 追加 `public-api-0.2.12`，綁定完整 declaration SHA、九個作者 pre/postimages 和十二個 copied helper hashes。舊 `public_api`、`public_api_profile` 與全部既有 private profiles 原樣保留。

四個已固定的 Cookery profiles 明列可以使用一份完整的 0.2.11 或 0.2.12 前置收據：guide startup、mooncake dough、recipe cache、reviewed integration enamel-basin lid。每項自身 declaration、作者來源及其他 private prerequisites 保持原值。混合新 ID／舊 helpers、同時存在兩份 public API 收據、缺少原有 cache 前置或未列入關係的 profile 均拒絕。

沒有修改 immutable reviewed integration source-evidence validator，也沒有放寬 exact dependency resolver。若實際 private manifest 仍指定 G150，組装應繼續拒絕，直到相应 private 來源配套完成。

## 驗證與交付邊界

使用真實 G151 descriptor／十二個 helper 執行既有 family bundle 檢查，並保留 enamel、Nether 和 immutable reviewed integration validator 的相關回歸。另以實際 `apply_host_extension` 對乾淨作者 Cookery 1.6.1 臨時副本套用，九個作者 postimages 和十二個 copied helpers 全部符合精確 hash，作者 manifest 保持原樣；舊 matcher 對同份 G151 descriptor 會拒絕為未登記來源。

這證明公開 API 的組裝接入及來源相容性。此批沒有取得實際 LIVE 連線、完整 private 配套或本次停服存檔，因此沒有新的整套 BDS／saved-world／部署讀回。公開 Git source／CI、下載包與 LIVE 各自保留身份，不將 source merge 改寫成已上服。

家族部署仍依 [UPDATE-WORKFLOW](UPDATE-WORKFLOW.md)：精確三庫與私有來源、完整組裝／靜態检查、一次停服備份的保存副本 first/restart、准入、安裝與讀回。沿用既有持續部署授權，`client=false`、`production_ready=false`，實際人工作業另記。
