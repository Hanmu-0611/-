# PDF 自动整理知识库 Web App

这是一个可以部署到网上的 PDF 自动整理网站。用户打开链接后可以上传 PDF，系统会提取内容、整理正文，并生成带出处的知识库条目。

## 最省事的使用方式

直接打开 `index.html`。这是纯前端版本，用户不需要安装 Python，也不需要启动服务器。

如果把这个仓库开启 GitHub Pages，别人打开网页链接就能直接使用。

纯前端版现在支持：

- 多个 PDF 批量整理
- 拖拽 PDF 上传
- 普通文字提取和扫描件 OCR
- 跨文件知识库出处索引
- 关键词查询出处
- 复制当前结果
- 下载 Markdown 整理稿
- 下载 JSON 知识库数据
- 多语言翻译：中文、英文、韩文、日文、法文、德文、西班牙文
- 下载翻译稿
- 一键清空当前知识库

翻译功能需要浏览器能访问网络翻译接口。如果网页完全离线打开，PDF 整理和知识库可以继续使用，但翻译可能不可用。

## 文件

- `index.html`：纯前端一键打开版本，适合分享网页链接或下载后双击打开
- `pdf_extract_server.py`：网站和后端接口，部署时运行这个文件
- `requirements.txt`：Python 依赖
- `apt.txt`：OCR 需要的 Tesseract 系统依赖
- `Procfile`：Heroku/Railway 等平台可用
- `render.yaml`：Render 部署配置
- `run_local.command`：macOS 本地一键运行
- `run_local.sh`：Linux/macOS 终端一键运行
- `run_local.bat`：Windows 本地一键运行

## 本地一键运行

最简单：

```text
双击 index.html
```

这个方式不需要安装 Python。浏览器会在本地处理 PDF，PDF 不会上传到服务器。

### macOS

双击：

```text
run_local.command
```

如果 macOS 提示没有权限，先在终端运行一次：

```bash
chmod +x run_local.command
```

然后再双击。

### Windows

双击：

```text
run_local.bat
```

### Linux 或终端运行

```bash
bash run_local.sh
```

启动后打开：

```text
http://127.0.0.1:8000
```

## 最简单部署方式：Render

1. 打开 Render，选择 `New` -> `Blueprint`。
2. 连接这个 GitHub 仓库。
3. Render 会读取 `render.yaml` 自动配置。
4. 部署完成后，Render 会给你一个公开链接。别人打开这个链接就能使用。

如果用 `New` -> `Web Service` 手动部署，Build Command 填：

```bash
pip install -r requirements.txt
```

Start Command 填：

```bash
python pdf_extract_server.py
```

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
