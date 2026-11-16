# 在 Codex 使用 pstack

[senluo marketplace](../.agents/plugins/marketplace.json) 直接安裝 [upstream pstack](https://github.com/cursor/plugins/tree/2eaf46574b25cdf7ef8c849837099b866b7438ce/pstack)。來源固定為 `2eaf46574b25cdf7ef8c849837099b866b7438ce`，版本為 `0.15.36`。
技能、playbook 與 agent 指示保留上游原文。本文件只映射 Codex 的工具與路徑，並非上游官方 Codex adapter。

## 安裝

使用支援 [portable plugins](https://developers.openai.com/plugins/build/plugins.md) 的 Codex CLI。從已發布的本庫 ref 註冊 marketplace，再安裝 pstack。

```sh
codex plugin marketplace add burnt-tea-dev/kaleidoscope-tavern-unofficial --ref refactor/pstack-workflow-20261112
codex plugin add pstack@senluo
```

`refactor/pstack-workflow-20261112` 是此次 PR 分支。合併後可改用 `main`。這個 ref 選擇 marketplace，pstack 來源仍由其中的 `sha` 固定。
若從本庫 checkout 測試，請在倉庫根目錄改用本地註冊命令。

```sh
codex plugin marketplace add .
codex plugin add pstack@senluo
codex plugin list --json
```

安裝後開啟新的 Codex session。在技能選單選取 `poteto-mode`，或明確要求使用 pstack 處理任務。

## 載入適配

本庫 AGENTS 要求在使用任何 pstack 技能前讀取本文件，每個 session 一次。在其他倉庫使用時，將這條讀取指示加入適用的 AGENTS。

1. 從已載入的 `skills/<name>/SKILL.md` 路徑，或 `codex plugin list --json` 找到安裝的 pstack。下文以 `<pstack>` 表示包含 `skills/`、`agents/` 與 `docs/` 的目錄。
2. 讀取 `<pstack>/skills/poteto-mode/SKILL.md`，依上游選擇 playbook。其他技能直接讀取同一包中的 `skills/<name>/SKILL.md`，保留其相對路徑。
3. 每個子代理 brief 都提供本 adapter 與 `<pstack>/skills/poteto-mode/SKILL.md` 的絕對路徑，並要求先讀取。使用上游 `agents/poteto-agent.md` 或指定角色的原文。

## 工具映射

只傳目前工具 schema 接受的欄位。host 沒有某欄位時省略它，並說明有影響的能力差異。

| pstack 使用的 Cursor 名稱 | Codex 中的操作 |
| --- | --- |
| `Task` | 使用 session 提供的子代理工具，例如 `spawn_agent`。ChatGPT host 可使用 `collaboration.spawn_agent`。依可用併發容量安排工作。 |
| `poteto-agent`、`comment-sicko` | 讀取 `<pstack>/agents/<name>.md`，將角色指示交給代理。不假定 host 已註冊同名角色。 |
| `readonly` | 使用可用的唯讀模式，並在 brief 限定範圍。沒有唯讀工具欄位時，不將文字指示描述為沙盒隔離。 |
| `environment: "cloud"`、`cloud_base_branch` | 使用獨立 git worktree，指定基底與工作目錄。需要獨立雲端 VM 的功能依可用能力處理。 |
| `run_in_background`、`resume`、`file_attachments` | 使用原生非同步代理。按上游規則選擇新代理或延續既有狀態，並在 brief 提供檔案路徑。 |
| `AskQuestion` | 使用可用的人類輸入工具，例如 `request_user_input`。沒有該工具時以文字詢問。保留上游對可自行觀察事項的處理方式。 |
| todolist | 使用 host 的計畫工具。沒有時，在回覆中維護上游要求的階段清單。 |
| `Read`、`Grep`、`Glob`、`Bash` | 使用檔案與命令工具，搜尋優先使用 `rg`。同包文件已存在時讀本機來源。 |
| Cursor 模型 slug | 只使用 host 證實可用的模型。無對應時採 `inherit-parent`，省略 model 欄位並說明。同模型評審不稱為跨模型評審。 |
| `pstack-models.mdc` | Codex 不因此自動載入 Cursor 規則。若使用既有角色設定，明確讀取它；未設定時沿用上述模型映射。 |
| built-in PR tool | 優先使用 session 的 PR 工具。其餘操作依上游選擇可用的 forge CLI。遵循 ready PR 規則。 |
| `control-ui`、`control-cli` | 使用已提供的對應技能及實際瀏覽器、桌面或終端工具。按上游要求操作真正的應用。 |

## 能力差異

上游 [Claude Code adapter](https://github.com/cursor/plugins/blob/2eaf46574b25cdf7ef8c849837099b866b7438ce/pstack/docs/harness/claude-code.md) 採用相同的主機映射方法。
遇到缺少的 Cursor Automations、cloud dashboard、Bugbot 啟動或 `/loop`，用一行說明缺少的能力，再繼續可完成的步驟。
已存在的 Bugbot 留言仍是可處理的 PR review。不要為缺少的 host 功能建立另一套排程或輪詢流程。

`deslop`、`control-ui` 與 `control-cli` 屬於另行提供的 `cursor-team-kit`，並未包含在 pstack。使用可取得的技能；缺少時如實說明。
GitHub `watch-pr` 直接使用上游腳本，需要 Bun 與可用的 `gh` 認證，並由上游 bootstrap 安裝鎖定依賴。
安裝 pstack 不會自動提供這些工具或認證，也不保證 host 採用 Cursor 的所有 frontmatter 欄位。

工作方法、驗證與 PR 交付依上游 playbook。使用者對當前任務的有效授權繼續適用。
