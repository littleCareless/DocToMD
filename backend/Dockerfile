# 使用Python官方镜像作为基础镜像
FROM python:3.11

# 安装系统依赖、构建工具和中文字体
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-opencv \
    libopencv-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    curl \
    fonts-wqy-microhei \
    fonts-wqy-zenhei \
    fonts-noto-cjk \
    fontconfig \
    locales \
    swig \
    python3-dev \
    cmake \
    git \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 配置中文语言环境
RUN locale-gen zh_CN.UTF-8
ENV LANG zh_CN.UTF-8
ENV LANGUAGE zh_CN:zh
ENV LC_ALL zh_CN.UTF-8

# 更新字体缓存
RUN fc-cache -fv

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 分两步安装Python依赖
# 1. 先安装不需要编译的包
RUN grep -v "PyMuPDF" requirements.txt > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt && \
    rm requirements_filtered.txt

# 2. 单独安装PyMuPDF
RUN pip install --no-cache-dir PyMuPDF==1.23.26

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p uploads markdown_files debug cache

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "app.py"]
