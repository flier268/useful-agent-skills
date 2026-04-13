# useful-agents-skills

一個整理代理工作流程提示詞的輕量倉庫，用來集中管理可重用的 skills，現在同時支援 Codex 與 Claude。

## 安裝教學

### 1) 下載專案

```bash
git clone https://github.com/flier268/useful-agent-skills
```

### 2) 進入專案目錄

```bash
cd useful-agents-skills
```

### 3) 安裝到 Codex（可選）

Linux / macOS:

```bash
mkdir -p ~/.codex/skills
cp -R skills/* ~/.codex/skills/
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.codex\skills" | Out-Null
Copy-Item -Recurse -Force .\skills\* "$HOME\.codex\skills\"
```

### 4) 安裝到 Claude（可選）

Linux / macOS:

```bash
mkdir -p ~/.claude/skills
cp -R skills/* ~/.claude/skills/
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force .\skills\* "$HOME\.claude\skills\"
```

### 5) 確認安裝結果

Linux / macOS:

```bash
ls -la ~/.codex/skills
ls -la ~/.claude/skills
```

Windows PowerShell:

```powershell
Get-ChildItem "$HOME\.codex\skills"
Get-ChildItem "$HOME\.claude\skills"
```

你應該會看到：

- Codex: `commit-staged`、`fix-issues`、`review-uncommitted`、`security-review` 等 skill 目錄
- Claude: `commit-staged`、`fix-issues`、`review-uncommitted`、`security-review` 等 skill 目錄

### 更新已安裝技能

當此 repo 有更新時，在專案目錄重新執行。

Linux / macOS:

```bash
cp -R skills/* ~/.codex/skills/
cp -R skills/* ~/.claude/skills/
```

Windows PowerShell:

```powershell
Copy-Item -Recurse -Force .\skills\* "$HOME\.codex\skills\"
Copy-Item -Recurse -Force .\skills\* "$HOME\.claude\skills\"
```

## 目前包含的 Skills

- `commit-staged`
  - 針對「已 staged 變更」產生符合規範的 commit 訊息，並建立 commit。
- `fix-issues`
  - 以 root cause 為核心處理 bug/故障，並補上回歸驗證。
- `review-uncommitted`
  - 用可延續的 cache session 審查 staged、unstaged 與 untracked 變更。
- `security-review`
  - 以結構化文件方式進行安全審查，區分摘要與詳細 findings。

## 平台對應

- Codex 使用 `skills/<name>/SKILL.md` 與 `skills/<name>/agents/openai.yaml`
- Claude 使用 `skills/<name>/SKILL.md`
- 兩者共用同一份 skill 內容，只是安裝位置不同
- Linux / macOS 預設路徑通常是 `~/.codex/skills` 與 `~/.claude/skills`
- Windows 預設路徑通常是 `$HOME\.codex\skills` 與 `$HOME\.claude\skills`

## 使用方式

- Codex: 以 `$commit-staged`、`$fix-issues`、`$review-uncommitted`、`$security-review` 之類的 skill 名稱呼叫
- Claude: 讓 Claude 依照 skill 描述自動套用，或在對話中明確要求使用對應 skill

## 授權

本專案採用 [MIT License](LICENSE)。
