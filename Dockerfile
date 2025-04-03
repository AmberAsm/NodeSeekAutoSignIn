# 使用 Python 3.10 作为基础镜像
FROM python:3.10-slim-bullseye

# 增加维护者信息
LABEL maintainer="NodeSeek Auto Signin"

# 设置工作目录
WORKDIR /app

# 设置时区为亚洲/上海
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 使用非交互式前端
ENV DEBIAN_FRONTEND=noninteractive

# 安装Chrome所需的依赖和中文字体
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    curl \
    unzip \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    procps \
    ca-certificates \
    apt-transport-https \
    # 添加中文字体支持
    fonts-noto-cjk \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    locales \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 配置中文locale
RUN echo "zh_CN.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen && \
    update-locale LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8

# 设置语言环境变量
ENV LANG=zh_CN.UTF-8
ENV LC_ALL=zh_CN.UTF-8

# 安装Google Chrome (使用官方仓库而不是特定版本)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 验证Chrome安装
RUN echo "验证Chrome版本:" && google-chrome --version

# 创建必要的目录
RUN mkdir -p logs screenshots

# 复制项目依赖文件
COPY requirements.txt .

# 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 确保在Docker环境中运行时Chrome始终使用无头模式
RUN if [ -f config.py ]; then \
    sed -i "s/'headless': False/'headless': True/g" config.py || echo "无法修改headless配置"; \
    fi

# 设置环境变量
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1
ENV BROWSER_BINARY=/usr/bin/google-chrome
ENV PAGE_LOAD_TIMEOUT=30
ENV SCRIPT_TIMEOUT=30

# 添加Chrome启动参数环境变量，配置字体渲染和超时设置
ENV CHROME_ARGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --start-maximized --disable-features=VizDisplayCompositor --font-render-hinting=none --disable-backgrounding-occluded-windows --disable-renderer-backgrounding --disable-background-timer-throttling --memory-pressure-off --disable-hang-monitor --renderer-process-limit=1 --disable-background-networking"

# 容器启动命令
CMD ["python", "auto_signin.py"]

# 如果只需要设置定时任务，可以使用: 
# CMD ["python", "main.py", "--schedule-only"]