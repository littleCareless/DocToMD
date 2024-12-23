# DocToMD - Document to Markdown Converter

DocToMD 是一个基于 Web 的文档转换工具,可以将多种格式的文档(PDF、Word、PPT 等)转换为 Markdown 格式。

## 功能特点

- 支持多种文档格式转换为 Markdown
- 实时转换进度显示
- 文件拖拽上传
- 转换历史记录
- 在线预览和下载
- 多文件批量处理
- 智能文本提取和格式化
- 缓存支持,避免重复转换

## 技术栈

### 前端

- React
- TypeScript
- Tailwind CSS
- Lucide Icons

### 后端

- Python/Flask
- Celery
- Redis
- Docker

## 快速开始

1. 克隆项目:

```bash
git clone https://github.com/yourusername/doctomd.git
cd doctomd
```

2. 配置环境变量:

```bash
cp .env.example .env
```

# 编辑 .env 文件,配置必要的环境变量

3. 使用 Docker Compose 启动:

```bash
docker-compose up -d
```

访问 http://localhost:8185 即可使用

### 支持的文件格式

- 文档: PDF, DOCX, PPTX, XLSX
- 图片: JPG, PNG
- 文本: TXT, HTML, CSV, JSON, XML
- 压缩包: ZIP

### 开发说明

## 本地开发环境设置

1. 前端开发:

```bash
cd frontend
pnpm install
pnpm dev
```

2. 后端开发:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

3. 启动 Celery Worker:

```bash
celery -A app.celery worker --loglevel=info
```

### 目录结构

```
.
├── frontend/          # 前端代码
├── backend/          # 后端代码
├── docker-compose.yml
├── .env.example
└── README.md
```

### 部署

项目使用 Docker Compose 进行部署,详细步骤:

1. 安装 Docker 和 Docker Compose
2. 配置环境变量
3. 运行 install.sh 或手动执行 Docker Compose 命令

### 贡献指南

欢迎提交 Issue 和 Pull Request

### 许可证

MIT License