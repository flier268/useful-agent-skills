# useful-agent-skills

一個整理代理工作流程提示詞的輕量倉庫，用來集中管理可重用的 skills。

Skills 採用 [Agent Skills](https://agentskills.io/) 格式，可用 [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI 安裝到支援的代理。

[![skills.sh](https://skills.sh/b/flier268/useful-agent-skills)](https://skills.sh/flier268/useful-agent-skills)

## 安裝

用 `npx skills` 從這個 repo 安裝：

```bash
npx skills add flier268/useful-agent-skills
```

等同寫法：

```bash
npx skills add https://github.com/flier268/useful-agent-skills
```

常用選項：

```bash
# 列出可用 skills，不安裝
npx skills add flier268/useful-agent-skills --list

# 只安裝指定 skill
npx skills add flier268/useful-agent-skills --skill commit-staged --skill fix

# 安裝到使用者全域目錄
npx skills add flier268/useful-agent-skills -g

# 非互動安裝（CI）
npx skills add flier268/useful-agent-skills --all -y
```

預設裝到目前專案的代理 skills 目錄。加 `-g` 則裝到使用者層級，例如 `~/.agents/skills`、`~/.claude/skills`、`~/.grok/skills`，依你選擇的代理而定。

更新已安裝技能：

```bash
npx skills update
```

或重新執行 `npx skills add flier268/useful-agent-skills`。

### 手動複製（可選）

若不想用 CLI，也可以直接複製 `skills/`：

Linux / macOS:

```bash
git clone https://github.com/flier268/useful-agent-skills
mkdir -p ~/.agents/skills
cp -R useful-agent-skills/skills/* ~/.agents/skills/
```

Windows PowerShell:

```powershell
git clone https://github.com/flier268/useful-agent-skills
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -Force .\useful-agent-skills\skills\* "$HOME\.agents\skills\"
```

## 目前包含的 Skills

- `cleanup`
  - 清理死碼，並把調適、除錯、趕工過程留下的補釘改成正確實作。
- `commit-staged`
  - 針對「已 staged 變更」產生符合規範的 commit 訊息，並建立 commit。
- `fix`
  - 以根因為核心修正已發現的問題，禁止補釘式修法；必要時重構。
- `review-with-session`
  - 用持久 session 審查變更、專案範圍與安全問題。

## 使用方式

安裝後，代理會依 skill 描述自動套用。

你也可以在對話中明確指定 `/cleanup`、`/commit-staged`、`/fix` 或 `/review-with-session`。

## 授權

本專案採用 [MIT License](LICENSE)。
