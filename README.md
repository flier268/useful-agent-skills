# useful-agents-prompts

一個整理 Codex skills 提示詞（`SKILL.md`）的輕量倉庫，用來集中管理可重用的工作流程。

## 安裝教學

### 1) 下載專案

```bash
git clone <你的-repo-url> useful-agents-prompts
```

### 2) 進入專案目錄

```bash
cd useful-agents-prompts
```

### 3) 建立 Codex skills 目錄（若尚未建立）

```bash
mkdir -p ~/.codex/skills
```

### 4) 安裝到 `~/.codex/skills`

```bash
cp -R skills/* ~/.codex/skills/
```

### 5) 確認安裝結果

```bash
ls -la ~/.codex/skills
```

你應該會看到 `commit-staged`、`fix-issues`、`security-review` 等 skill 目錄。

### 更新已安裝技能

當此 repo 有更新時，在專案目錄重新執行：

```bash
cp -R skills/* ~/.codex/skills/
```

## 目前包含的 Skills

- `commit-staged`
  - 針對「已 staged 變更」產生符合規範的 commit 訊息，並建立 commit。
- `fix-issues`
  - 以 root cause 為核心處理 bug/故障，並補上回歸驗證。
- `security-review`
  - 以結構化文件方式進行安全審查，區分摘要與詳細 findings。

## 授權

本專案採用 [MIT License](LICENSE)。
