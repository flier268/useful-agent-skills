# useful-agents-skills

一個整理代理工作流程提示詞的輕量倉庫，用來集中管理可重用的 skills。安裝到共用的 `~/.agents/skills`，供支援 skills 的代理讀取。

## 安裝教學

### 1) 下載專案

```bash
git clone https://github.com/flier268/useful-agent-skills
```

### 2) 進入專案目錄

```bash
cd useful-agents-skills
```

### 3) 安裝到 `.agents`

Linux / macOS:

```bash
mkdir -p ~/.agents/skills
cp -R skills/* ~/.agents/skills/
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -Force .\skills\* "$HOME\.agents\skills\"
```

### 4) 確認安裝結果

Linux / macOS:

```bash
ls -la ~/.agents/skills
```

Windows PowerShell:

```powershell
Get-ChildItem "$HOME\.agents\skills"
```

你應該會看到 `commit-staged`、`fix-issues`、`review-with-session` 等 skill 目錄。

### 更新已安裝技能

當此 repo 有更新時，在專案目錄重新執行。

Linux / macOS:

```bash
cp -R skills/* ~/.agents/skills/
```

Windows PowerShell:

```powershell
Copy-Item -Recurse -Force .\skills\* "$HOME\.agents\skills\"
```

## 目前包含的 Skills

- `commit-staged`
  - 針對「已 staged 變更」產生符合規範的 commit 訊息，並建立 commit。
- `fix-issues`
  - 以 root cause 為核心處理 bug/故障，並補上回歸驗證。
- `review-with-session`
  - 用持久 session 審查變更、專案範圍與安全問題。

## 使用方式

代理可依照 skill 描述自動套用。

你也可以在對話中明確指定 `$commit-staged`、`$fix-issues` 或 `$review-with-session`。

## 授權

本專案採用 [MIT License](LICENSE)。
