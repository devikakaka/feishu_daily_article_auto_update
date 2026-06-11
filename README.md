# 📰 每日评论文章自动抓取 + AI 分析 + 飞书知识库发布

一个全自动化的内容分析系统：每天北京时间 9:00 自动从**人民网**和**南方网**抓取当日评论文章，用**通义千问**大模型生成结构化摘要，自动更新本文件并发布到**飞书知识库**。

## 🎯 当前监控源

| # | 来源 | 类型 | 说明 |
|---|------|------|------|
| 1 | [人民时评](http://opinion.people.com.cn/GB/8213/49160/49219/index.html) | HTML | 人民日报评论部「人民时评」专栏 |
| 2 | [南方日报评论员](https://search.southcn.com/?keyword=%E5%8D%97%E6%96%B9%E6%97%A5%E6%8A%A5%E8%AF%84%E8%AE%BA%E5%91%98&s=time&page=1) | API | 南方网搜索接口，按标题过滤「南方日报评论员」 |
| 3 | [壹时评](http://opinion.people.com.cn/GB/223228/index.html) | HTML | 人民网「壹时评」网络评论专栏 |

每天只抓取**当天日期**对应的文章，非当日文章自动跳过。如需添加新源，编辑 `config/config.example.yaml` 中的 `scraper.sources` 即可。

## 🚀 功能特性

- **定时抓取**: GitHub Actions 每天北京时间 9:00 自动运行
- **多源聚合**: 同时支持静态 HTML 页面和 JSON API 接口
- **日期过滤**: 自动匹配当天日期，只处理当日新文章
- **AI 分析**: 使用通义千问 (Qwen) 大模型生成结构化摘要
- **飞书发布**: 自动将分析结果发布到飞书知识库
- **本地归档**: 保存原始文章和分析结果到 `output/` 目录
- **历史记录**: 自动维护历史记录表格

## 📋 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/feishu.git
cd feishu
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置项目

```bash
cp config/config.example.yaml config/config.yaml
cp .env.example .env
```

编辑 `config/config.yaml`:
- 在 `scraper.sources` 中配置数据源（已预置三个源）
- 设置 `feishu.wiki_space_id`（需要飞书自建应用）

编辑 `.env`:
- 填入 `DASHSCOPE_API_KEY`（通义千问）
- 填入 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`

### 4. 测试运行

```bash
# 仅抓取（不分析、不上传）
python -m src.main --config config/config.yaml --dry-run

# 抓取 + 分析（不上传飞书）
python -m src.main --config config/config.yaml --skip-feishu

# 完整流程（抓取 + 分析 + 上传飞书）
python -m src.main --config config/config.yaml
```

### 5. 运行测试

```bash
python -m pytest tests/ -v
```

## 📁 项目结构

```
feishu/
├── .github/workflows/daily_scrape.yml   # GitHub Actions 定时任务
├── config/
│   ├── config.example.yaml              # 配置模板（含三个预置源）
│   └── .gitignore                       # 忽略 config.yaml（含密钥）
├── docs/
│   └── FEISHU_SETUP.md                  # 飞书配置指南（7步）
├── src/
│   ├── main.py                          # 主流程入口
│   ├── config_loader.py                 # YAML 配置加载 + 环境变量展开
│   ├── scraper.py                       # 多源爬虫（HTML + API）
│   ├── llm_analyzer.py                  # 通义千问 AI 分析模块
│   ├── feishu_client.py                 # 飞书 API 客户端（自动刷新 token）
│   ├── feishu_uploader.py              # 飞书知识库节点创建 + 文档写入
│   ├── markdown_to_blocks.py            # Markdown → 飞书 Block 格式转换
│   └── readme_generator.py              # README 自动生成器
├── output/                              # 输出目录
│   ├── latest_analysis.md               # 最新分析结果
│   └── articles/                        # 原始文章存档
├── tests/                               # 单元测试（36 个测试）
├── .gitignore
├── .env.example                         # 环境变量模板
├── README.md                            # 本文件（自动更新）
└── requirements.txt
```

## 🔑 所需密钥

| 密钥 | 说明 | 获取方式 |
|------|------|----------|
| `DASHSCOPE_API_KEY` | 通义千问 API Key | [DashScope 控制台](https://dashscope.console.aliyun.com/apiKey) |
| `FEISHU_APP_ID` | 飞书应用 ID | [飞书开放平台](https://open.feishu.cn/app) |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | 同上 |

详细配置步骤请查看 [飞书自建应用配置指南](docs/FEISHU_SETUP.md)。

### GitHub Secrets 配置

在仓库页面: **Settings → Secrets and variables → Actions → New repository secret**，添加以上三个密钥。

## 🔧 添加新的数据源

编辑 `config/config.yaml` 的 `scraper.sources` 数组：

### 添加 HTML 静态页面源

```yaml
  - name: "我的新源"
    type: "html"
    url: "https://example.com/articles"
    base_url: "https://example.com"
    selectors:
      list_items: "ul.article-list li"    # 列表项选择器
      article_link: "a"                   # 链接选择器（相对于 list_items）
      date_selector: "span.date"          # 日期选择器
    detail_selectors:
      title: "h1.article-title"           # 详情页标题选择器
      content: "div.article-content"      # 详情页正文选择器
```

### 添加 JSON API 源

```yaml
  - name: "我的 API 源"
    type: "api"
    url: "https://api.example.com/search"
    method: "post"                        # post 或 get
    params:
      keyword: "关键词"
      page: 1
    api:
      items_path: "data.list"             # JSON 中数组的路径（点分隔）
      title_field: "title"                # 标题字段
      content_field: "post.content"       # 正文字段（支持嵌套）
      date_field: "pub_time"              # 日期字段（格式 YYYY-MM-DD）
      url_field: "url"                    # URL 字段
      title_filter: "必须包含的关键词"     # 可选：标题过滤
```

## 📝 命令行参数

```bash
python -m src.main [OPTIONS]

Options:
  --config PATH        配置文件路径（默认: config/config.yaml）
  --skip-feishu        跳过飞书上传
  --dry-run            仅抓取，不分析不上传
```

## 🛠️ 技术栈

- **爬虫**: Python + requests + BeautifulSoup + lxml
- **大模型**: 通义千问 (Qwen) via DashScope OpenAI 兼容 API
- **飞书**: Open API (tenant_access_token + Wiki 节点 + Docx Block API)
- **调度**: GitHub Actions (cron `0 1 * * *` UTC = 北京时间 9:00)
- **配置**: YAML + `${ENV_VAR}` 环境变量插值
- **测试**: pytest（36 个单元测试）

## 📊 最新分析

> 首次运行后将自动生成分析结果

## 📚 历史记录

> 首次运行后将自动生成历史记录表格

## ⚠️ 注意事项

1. **静态网页**: HTML 源仅支持服务端渲染的页面，不支持 JavaScript 动态渲染（API 源无此限制）
2. **GitHub Actions**: 定时任务可能有最多 15 分钟延迟
3. **飞书权限**: 必须将应用添加为知识库管理员，否则上传会返回 `permission denied`
4. **API 费用**: 通义千问和飞书 API 可能产生少量费用（qwen-plus 约 ¥0.004/千 token）
5. **日期匹配**: HTML 源通过列表页的日期文本过滤，格式需为 `YYYY-MM-DD` 或 `YYYY-MM-DD HH:MM`

## 📖 参考文档

- [飞书自建应用配置指南](docs/FEISHU_SETUP.md)
- [飞书开放平台文档](https://open.feishu.cn/document)
- [DashScope 通义千问文档](https://help.aliyun.com/zh/dashscope/)

---
*由 GitHub Actions 自动生成 ⚡ Powered by Qwen + Feishu*