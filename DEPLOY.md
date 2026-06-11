# PDF 自动整理知识库 Web App

这是一个可以部署到网上的 PDF 自动整理网站。用户打开链接后可以上传 PDF，系统会提取内容、整理正文，并生成带出处的知识库条目。

## 文件

- `pdf_extract_server.py`：网站和后端接口，部署时运行这个文件
- `requirements.txt`：Python 依赖
- `apt.txt`：OCR 需要的 Tesseract 系统依赖
- `Procfile`：Heroku/Railway 等平台可用
- `render.yaml`：Render 部署配置

## 最简单部署方式：Render

1. 打开 Render，选择 `New` -> `Web Service`。
2. 连接这个 GitHub 仓库。
3. Build Command 填：

```bash
pip install -r requirements.txt
```

4. Start Command 填：

```bash
python pdf_extract_server.py
```

5. 部署完成后，Render 会给你一个公开链接。别人打开这个链接就能使用。

## OCR

现在支持扫描版 PDF。系统会先尝试直接读取 PDF 文字；如果某一页没有可提取文字，就会自动使用 OCR。

默认 OCR 语言：

```text
eng+chi_sim+kor
```

意思是英文、简体中文、韩文。如果只需要中文和英文，可以在部署平台环境变量里设置：

```text
OCR_LANGUAGES=eng+chi_sim
```

## 接口

网页首页：

```text
/
```

上传 PDF：

```text
POST /api/extract-pdf
```

查询知识库：

```text
GET /api/knowledge-base?search=关键词
```

## 注意

免费云平台的本地文件存储通常不是永久数据库。当前版本的知识库会写入服务器本地的 `knowledge_base.jsonl`，适合演示和轻量使用。如果要长期保存所有用户上传后的知识库，需要接数据库，例如 SQLite 挂载磁盘、PostgreSQL、Supabase 或 Firebase。
