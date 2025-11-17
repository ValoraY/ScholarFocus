# 📘 Google Scholar自动爬取与汇总

本项目用于自动化抓取多个学者的 Google Scholar 论文列表，并自动生成 Markdown 格式的数据文件存储在 `data/` 目录下。

它支持：

✅ 自动抓取最新论文
✅ 增量更新（只抓取新增论文）
✅ 按年份过滤
✅ 每位学者生成独立 Markdown
✅ 全部学者生成汇总 Markdown
✅ 支持 GitHub Actions 自动定时运行
✅ 支持从 GitHub 配置学者与年份范围

本项目特别适合用于课题组、个人研究资料库、文献自动更新站点等。

---

# 📂 项目目录结构

```
.
├── fetch_papers.py           # 主程序（爬虫 + 生成 Markdown）
├── config.json               # 本地默认配置（极简）
├── data/
│   ├── json/                 # 每位学者的完整 JSON 数据缓存
│   ├── authors/              # 每位学者的 Markdown 文件
│   │   ├── zhangsan.md
│   │   ├── lisi.md
│   │   └── wangwu.md
│   └── all_papers.md         # 全部学者的汇总数据（Markdown）
├── .github/
│   └── workflows/
│       └── update.yml        # GitHub Actions 自动任务
└── README.md                 # 项目使用文档
```

---

# 🚀 功能介绍

## 🔄 1. 自动抓取学者论文

本程序通过 `scholarly` 库访问 Google Scholar 获取：

* 论文标题
* 发表年份
* 摘要（如 Google Scholar 摘要被截断，会尝试从 arXiv 获取完整摘要，因反爬限制，目前仅支持 arXiv 完整摘要）
* 论文链接

程序会：

* 按年份过滤
* 自动跳过已存在的论文（增量模式）
* 保存到 JSON & Markdown

---

## 📁 2. 数据存放在 data/ 下

### ✔ 全部数据（Markdown）

```
data/all_papers.md
```

### ✔ 各个学者

```
data/authors/zhangsan.md
data/authors/lisi.md
…
```

### ✔ JSON 缓存（不建议手动编辑）

```
data/json/zhangsan_zhangsanID.json
```

这些 JSON 文件用于增量更新。

---

# ⚙️ 配置方式

系统支持两种配置方式：

---

# 🟦 **方式 1（推荐）：GitHub Actions 动态配置**

进入：

```
GitHub → Settings → Secrets and variables → Actions → Variables
```

把以下变量创建进去：

| 变量名              | 示例值                                       | 说明                       |
| ------------------- | -------------------------------------------- | -------------------------- |
| `SCHOLAR_AUTHORS`   | `[{"name": "zhangsan", "id": "UxxxxAAAAJ"}]` | 学者列表（JSON）           |
| `YEAR_START`        | `2023`                                       | 抓取起始年份               |
| `YEAR_END`          | `2025`                                       | 抓取结束年份               |
| `INCREMENTAL_LIMIT` | `20`                                         | 每次抓取最新多少篇（增量） |

### 📌 示例（SCHOLAR_AUTHORS）

```json
[
  {"name": "zhangsan", "id": "UxxxxAAAAJ"},
  {"name": "lisi", "id": "UxxxxAAAAJ"},
  {"name": "wangwu", "id": "UxxxxAAAAJ"}
]
```

---

# 🟩 **方式 2：本地 config.json（默认值）**

不经过 GitHub Actions 时，程序会读取本地 configuration。

这是 **默认 config.json（简化版）**：

```json
{
  "year_start": 2023,
  "year_end": 2025,
  "authors": [],
  "incremental_limit": 20
}
```

⚠️ 注意：
如果使用 GitHub Actions，会自动生成一个 `config_override.json` 覆盖上述配置。

---

# 🤖 GitHub Actions 自动运行

本项目已经配置了 GitHub Actions（`.github/workflows/update.yml`）：

### ✔ 每周自动爬取一次

### ✔ 支持手动触发

### ✔ 自动提交更新到仓库

你可以在 GitHub → Actions 中点击 **Run workflow** 手动执行。

---

# 🖥️ 本地运行方法

确保安装依赖：

```
pip install scholarly requests beautifulsoup4 httpx[socks]
```

运行：

```
python fetch_papers.py
```

数据将在：

```
data/all_papers.md
data/authors/*.md
```

自动生成。

---

# 🆕 增量更新逻辑说明

系统会：

### ✔ 首次运行：抓取全部论文（最多 200 篇）

### ✔ 后续运行：只抓最新的 N 篇（默认 N=20，支持 GitHub 配置）

程序会自动比较 JSON 中已有的标题，避免重复抓取。

---

# 📜 摘要策略说明

* Google Scholar 摘要若被截断（以 `...` 结尾）
* 程序会自动调用 arXiv API 拉取完整摘要
* 若不是 arXiv 或无完整摘要 → 使用 Google Scholar 摘要

---

# 📌 注意事项

* Google Scholar 抓取速度较慢，请耐心等待
* 若学者页面访问频率过高可能触发验证码（scholarly 会重试）
* JSON 文件不要手动编辑
* 修改学者列表需更新 GitHub Actions Variables

---

# 🎉 总结

本项目提供了一套：

* 自动化
* 稳定可靠
* 易扩展
* 功能完整
* GitHub 原生支持

的学者论文定时抓取系统。
