# 家族部署工具盤點（W2.1）

基準：Tavern `afae50c054487d131829bacaedd4e0ea749a26c0`，2026-10-26 HKT。範圍為 `tools/family_update/*.py` 的 46 個非測試模組（包含套件入口）。本文件只盤點，不變更政策、runtime、發布身份或 LIVE。

**狀態：盤點已有結論；「最後實際執行 commit」仍有證據缺口，W2.1 未達全部驗收。** Git 記錄只能證明最後修改；現存部署報告並非逐模組執行追蹤，無法可靠還原每個模組最後跑過的版本與 config。下表的 commit 均為最後修改，不能讀成使用證據。

S1 規劃指定保留的六個核心模組，目前沿直接、條件與動態階段調度可達 42 個模組。CLI 另用到 `cleanup_engine_inputs`、`native_capacity_wait`；`acceptance_evidence` 有獨立 CLI，`__init__` 是套件結構。因此不能直接把保留集縮成六個檔案，也沒有已證明可孤立刪除的模組。必須先讓替代實作承接現行責任、移除舊入口，再退役檔案。

配置標記 **C**＝目前 selector 的 2026-10-19 T177/G155/W154/P59 配置，**P**＝已審但尚未部署的 2026-10-25 bottle-owner 配置。兩者均選 `extension_stable_profile=current-author-retained`；C 另有 `prospective_preserved_inputs`、`normal_idle_update`、`native_capacity_wait_seconds`，P 改由 `managed_drift_recovery` 處理已觀察差異。這些是**靜態分支選擇與可達性**，不證明任何函式曾執行。

表內 importer 若未加目錄均指本套件的 `.py` 模組，長清單只列主要 caller。CONFIG 列保留可確認的字面 keys；「傳入」指由 caller 選取後作參數傳遞。以變數／列表索引讀取的配置並未完整涵蓋；未列出或未帶 C/P 不表示無使用。

| 模組 | 主要 importer／CLI | CONFIG keys／觸發入口 | 最後修改 | 處置與先決條件 |
|---|---|---|---|---|
| `__init__.py` | Python package import | 不直接讀 CONFIG；由 caller 提供資料 | `54791248 2026-10-03` | 保留必要套件入口 |
| `acceptance_evidence.py` | 獨立 CLI；`docs/ACCEPTANCE-EVIDENCE.md` | 不直接讀 CONFIG；由 caller 提供資料 | `4ec0abb8 2026-10-15` | 合併真人證據驗證；保留現有 CLI 至替代入口可用 |
| `amw25_reconciliation.py` | `common`、`preserved_reconciliation`、`amw27_reconciliation`、`startup26_reconciliation` | 不直接讀 CONFIG；由 caller 提供資料 | `5d60141a 2026-10-10` | 退役歷史 reconciliation 候選；先排除現行分支／caller並移轉所用 helper |
| `amw27_reconciliation.py` | `preserved_reconciliation` | `extension_validation` | `5d60141a 2026-10-10` | 退役歷史 reconciliation 候選；先排除現行分支／caller並移轉所用 helper |
| `approved_runtime_retention.py` | `common`、`build_candidate` | `approved_runtime_retention`（傳入） | `fe7f1ea3 2026-10-07` | 合併責任後退役舊模組；先移除現行 importer |
| `author_state_preservation.py` | `rehearse_saved_world` | `identity_migration`（傳入） | `e3f2696a 2026-10-17` | 併入原生／存檔核心驗證；須保留狀態與物品資料保存檢查 |
| `build_candidate.py` | `workflow.run_stage`（prepare） | `approved_runtime_retention`、`extension_hold`、`held_sources`、`managed_drift_recovery` [P] | `00425102 2026-10-25` | **保留核心**；先承接待合併責任 |
| `capture_predeploy.py` | `workflow.run_stage`（prepare） | `managed_drift_recovery` [P]、`preserved_additions` | `8a1d5716 2026-10-18` | **保留核心**；先承接待合併責任 |
| `casting_reconciliation.py` | `preserved_reconciliation` | 不直接讀 CONFIG；由 caller 提供資料 | `5766170f 2026-10-04` | 退役歷史 reconciliation 候選；先排除現行分支／caller並移轉所用 helper |
| `cleanup_copies.py` | `tools/family_update.py`、`deploy_live` | `retention_pid_namespace` [C,P]、`retention_root` [C,P] | `c03e5369 2026-10-15` | 合併清理責任；保留活動資料、目前引用與完整回退保護 |
| `cleanup_engine_inputs.py` | `tools/family_update.py` | `retention_root` [C,P] | `d1d7f261 2026-10-11` | 合併清理責任；保留活動資料、目前引用與完整回退保護 |
| `common.py` | `tools/family_update.py`、`build_candidate`、`deploy_live`、`workflow`；共享設定與驗證 | `api_module` [C,P]、`api_path_mappings` [C,P]、`approved_runtime_retention`、`archives` [C,P]、`extension` [C,P]、`extension_hold`、`extension_hold_source`、`extension_validation`、`held_sources`、`managed_drift_recovery` [P]、`native_port` [C,P]、`preinstall_recovery_output`、`preserve_captured_experiments` [C,P]、`preserved_additions`、`preserved_reconciliation`、`prospective_preserved_inputs` [C]、`python` [C,P]、`retention_root` [C,P]、`saved_port` [C,P]、`schema` [C,P]、`server_name` [C,P]、`sources` [C,P]、`startup_markers` [C,P]、`startup_reconciliation`、`translation_reconciliation` | `d8b4bd85 2026-10-25` | 分配至核心的設定／I/O／驗證責任；先解除共享匯入 |
| `cookery_cache_validation.py` | `extension_validation`、`current_author_validation`；保存 profile helpers | `extension_cache_validation`、`prospective_preserved_inputs` [C] | `7b4e4e07 2026-10-12` | 退役歷史 profile 候選；先抽出目前作者驗證仍匯入的 helper，移除舊入口 |
| `current_author_validation.py` | `stable_author_validation`、`tools/family_bundle.py`；目前作者 profile | `extension_stable_artifact_id` [C,P]、`extension_stable_profile` [C,P]、`extension_stable_pull_request` [C,P]、`extension_stable_run_id` [C,P]、`extension_stable_validation` [C,P] | `39d02b1f 2026-10-25` | 合併至當前來源／候選驗證；P 仍選目前作者入口，不可直接刪 |
| `deploy_live.py` | `workflow.run_stage`（deploy） | `container_recovery_plan`、`extension_cache_validation`、`extension_hud_validation`、`extension_performance_validation`、`extension_stable_validation` [C,P]、`extension_validation`、`identity_migration`、`managed_drift_failure_policy` [P]、`managed_drift_recovery` [P]、`native_actor_recovery_plan` [P]、`native_storage_reanchor_plan` [C,P]、`normal_idle_update` [C]、`preinstall_recovery_output`、`preserved_additions`、`preserved_reconciliation`、`prospective_preserved_inputs` [C]、`startup_reconciliation`、`translation_reconciliation` | `00425102 2026-10-25` | **保留核心**；先承接待合併責任 |
| `engine_pack_projection.py` | `common` | `managed_drift_recovery` [P] | `286ee082 2026-10-18` | 合併責任後退役舊模組；先移除現行 importer |
| `explicit_hud_validation.py` | `extension_validation`、`deploy_live`、`workflow` | `extension_hud_pull_request`、`extension_hud_validation`、`extension_performance_validation` | `fa3b1c1f 2026-10-15` | 退役歷史 profile 候選；先抽出目前作者驗證仍匯入的 helper，移除舊入口 |
| `extension_validation.py` | `current_author_validation`、`cookery_cache_validation`；HUD/Ribbits保存入口 | `extension_cache_validation`、`extension_hud_validation`、`extension_performance_validation`、`extension_stable_validation` [C,P]、`extension_validation` | `372e88ac 2026-10-16` | 合併責任後退役舊模組；先移除現行 importer |
| `fishing_native_observer.py` | `common`、`current_author_validation`、`rehearse_saved_world`、`workflow` | `managed_drift_recovery` [P] | `00425102 2026-10-25` | 合併責任後退役舊模組；先移除現行 importer |
| `freezer_performance_validation.py` | `extension_validation`、`deploy_live`、`workflow` | `extension_hud_pull_request`、`extension_hud_validation`、`extension_performance_validation`、`prospective_preserved_inputs` [C]、`startup_markers` [C,P] | `4baa3533 2026-10-15` | 退役歷史 profile 候選；先抽出目前作者驗證仍匯入的 helper，移除舊入口 |
| `freezer_storage_preservation.py` | `rehearse_saved_world` | 不直接讀 CONFIG；由 caller 提供資料 | `3f378611 2026-10-08` | 併入原生／存檔核心驗證；須保留狀態與物品資料保存檢查 |
| `github_reads.py` | `common`、`current_author_validation`、`workflow` | 不直接讀 CONFIG；由 caller 提供資料 | `92159728 2026-10-17` | 合併責任後退役舊模組；先移除現行 importer |
| `identity_migration.py` | `build_candidate`、`deploy_live`、`rehearse_saved_world` | `container_recovery_plan`、`identity_migration`、`managed_drift_recovery` [P] | `f87d3a49 2026-10-18` | **保留核心**；先承接待合併責任 |
| `managed_drift_recovery.py` | `common`、`build_candidate`、`deploy_live` | `managed_drift_recovery` [P]、`managed_drift_rollback_root` [P]、`preinstall_recovery_output` | `3dbcc40e 2026-10-25` | 併入部署／失敗復原；替代前保留現行擁有權與回退處理 |
| `memory_budget.py` | `tools/family_update.py`、`workflow`、`deploy_live`、`rehearse_saved_world` | `memory_budget` [C,P] | `097e0f41 2026-10-18` | **保留核心**；先承接待合併責任 |
| `native_capacity_wait.py` | `tools/family_update.py` | `native_capacity_wait_seconds` [C] | `8b3cae68 2026-10-19` | 合併至 `memory_budget`；保留有界等待與失敗狀態 |
| `native_common.py` | `rehearse_saved_world`、`tools/family_native_check.py` | `preserve_captured_experiments` [C,P] | `286ee082 2026-10-18` | 合併責任後退役舊模組；先移除現行 importer |
| `native_storage_reanchor.py` | `deploy_live`、`rehearse_saved_world` | `native_storage_reanchor_plan` [C,P]（傳入） | `4387a66f 2026-10-07` | 併入原生／存檔核心驗證；須保留狀態與物品資料保存檢查 |
| `normal_idle_update.py` | `common`、`deploy_live` | `managed_drift_recovery` [P]、`normal_idle_update` [C]、`preinstall_recovery_output` | `ee5cb218 2026-10-19` | 併入部署／失敗復原；替代前保留現行擁有權與回退處理 |
| `poststart_verify.py` | `tools/family_update.py` 的 verify-live → `workflow.run_stage` | 不直接讀 CONFIG；由 caller 提供資料 | `861ef2be 2026-10-08` | **保留核心**；先承接待合併責任 |
| `preinstall_recovery.py` | `tools/family_update.py`、`common`、`managed_drift_recovery` | `preinstall_recovery_output`、`recovery_original_config` | `d8b4bd85 2026-10-25` | 併入部署／失敗復原；替代前保留現行擁有權與回退處理 |
| `preserved_additions.py` | `common`、`managed_drift_recovery` | `preserved_additions` | `8a1d5716 2026-10-18` | 合併責任後退役舊模組；先移除現行 importer |
| `preserved_client_assets_inputs.py` | `current_author_validation`、`prospective_preserved_inputs`、`deploy_live`、`workflow` | `prospective_preserved_inputs` [C] | `df13d02c 2026-10-19` | 合併責任後退役舊模組；先移除現行 importer |
| `preserved_hud_inputs.py` | `prospective_preserved_inputs`、`deploy_live`、`workflow` | `extension_cache_validation`、`prospective_preserved_inputs` [C] | `7b4e4e07 2026-10-12` | 合併責任後退役舊模組；先移除現行 importer |
| `preserved_reconciliation.py` | `common`、`casting_reconciliation` | `preserved_reconciliation` | `5d60141a 2026-10-10` | 退役歷史 reconciliation 候選；先排除現行分支／caller並移轉所用 helper |
| `preserved_ribbits_inputs.py` | `prospective_preserved_inputs`、`deploy_live`、`workflow` | `prospective_preserved_inputs` [C] | `1827848b 2026-10-13` | 合併責任後退役舊模組；先移除現行 importer |
| `preserved_saturation_inputs.py` | `prospective_preserved_inputs`、`deploy_live`、`workflow` | `extension_performance_validation`、`prospective_preserved_inputs` [C] | `4baa3533 2026-10-15` | 合併責任後退役舊模組；先移除現行 importer |
| `prospective_preserved_inputs.py` | `common`、`build_candidate`、`deploy_live`；各保存 profile | `extension_validation`、`prospective_preserved_inputs` [C] | `8d695c73 2026-10-19` | 合併責任後退役舊模組；先移除現行 importer |
| `rehearse_saved_world.py` | CLI saved-world → `workflow.run_stage` | `container_recovery_plan`、`native_actor_recovery_plan` [P]、`native_cpu_profile` [C,P]、`native_storage_reanchor_plan` [C,P] | `00425102 2026-10-25` | 併入 staging 調度，保留同一副本首載／重啟與資料讀回 |
| `repository_identity.py` | `common`、`workflow`、`tools/family_bundle.py`、`tools/baseline_gate.py` | 不直接讀 CONFIG；由 caller 提供資料 | `1091cc82 2026-10-19` | 合併來源邊界驗證；先處理 baseline/bundle 的套件外依賴 |
| `retention.py` | `cleanup_copies` | 不直接讀 CONFIG；由 caller 提供資料 | `599d4e20 2026-10-18` | 合併清理責任；保留活動資料、目前引用與完整回退保護 |
| `source_holds.py` | `common`、`build_candidate`、`tools/family_bundle.py` | `extension_hold_source`、`held_sources`（傳入）、`extension_hold`（傳入） | `54dc6d74 2026-10-08` | 合併責任後退役舊模組；先移除現行 importer |
| `stable_author_validation.py` | `extension_validation`、`prospective_preserved_inputs`、`deploy_live`、`workflow` | `extension_stable_artifact_id` [C,P]、`extension_stable_profile` [C,P]、`extension_stable_pull_request` [C,P]、`extension_stable_run_id` [C,P]、`extension_stable_validation` [C,P] | `df13d02c 2026-10-19` | 分離目前作者 dispatch 與歷史 profile，再合併／退役 |
| `startup26_reconciliation.py` | `common` | `extension_validation`、`startup_reconciliation` | `9db59ea7 2026-10-08` | 退役歷史 reconciliation 候選；先排除現行分支／caller並移轉所用 helper |
| `storage.py` | `build_candidate`、`capture_predeploy`、`deploy_live`；離線 actor recovery | 不直接讀 CONFIG；由 caller 提供資料 | `00425102 2026-10-25` | 合併容量檢查；先處理 actor recovery 的套件外依賴 |
| `workflow.py` | `tools/family_update.py`；`common`、`deploy_live` 的 CI/原生驗證與調度 | `identity_migration`、`preserved_additions`、`preserved_reconciliation`、`prospective_preserved_inputs` [C]、`pull_requests` [C,P]、`runtime_ci_pull_requests` [C,P] | `d8b4bd85 2026-10-25` | 由新 staging/deploy 調度承接；先保留 CLI、CI 重用與階段驗證 |

建議下一個交付先僅加入本盤點。之後以單一歷史 profile 為界，先替換共享 helper、移除其選擇與 import，再刪舊模組及已失去用途的測試；目前來源驗證、備份、資料保存、正常重啟與回退仍需有可觀察行為覆蓋。歷史候選原證據由 Git／原紀錄保留，不能改寫失敗或重算 hash 消音。

CI 判定：`python tools/ci_impact.py --paths family/TOOLS-INVENTORY.md` 將此路徑分類為 `docs`，`baseline=true`、`runtime=false`。現有 workflow 仍跑 impact 與 baseline（含家族工具回歸），runtime jobs 依條件跳過；此純文件變更不需修改 CI、升包或部署。
