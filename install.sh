#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
}

# 检查 Docker Compose 是否安装
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

# 检查环境文件
check_env() {
    if [ ! -f ".env" ]; then
        echo -e "${RED}Environment file not found!${NC}"
        echo -e "${YELLOW}Creating .env file from template...${NC}"
        cat > .env << EOL
# Port configuration
FRONTEND_PORT=8185
BACKEND_PORT=8186

# OpenAI configuration
OPENAI_API_KEY=your-api-key-here

# Redis configuration
REDIS_PORT=6379
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Flask configuration
FLASK_APP=app.py
FLASK_ENV=production
FLASK_DEBUG=0
EOL
        echo -e "${YELLOW}Please edit .env and set your configurations before continuing.${NC}"
        exit 1
    fi
    
    # 检查 OpenAI API Key 是否已设置
    if grep -q "OPENAI_API_KEY=your-api-key-here" ".env"; then
        echo -e "${RED}Please set your OpenAI API Key in .env${NC}"
        exit 1
    fi

    # 加载环境变量
    source .env
}

# 创建必要的目录
create_directories() {
    echo -e "${GREEN}Creating necessary directories...${NC}"
    mkdir -p uploads markdown_files
    touch uploads/.gitkeep markdown_files/.gitkeep
}

# 主安装流程
main() {
    echo -e "${GREEN}Starting installation...${NC}"
    
    # 检查必要条件
    check_docker
    check_docker_compose
    check_env
    
    # 创建目录
    create_directories
    
    # 构建和启动服务
    echo -e "${GREEN}Building and starting services...${NC}"
    docker-compose up -d --build
    
    # 等待服务启动
    echo -e "${YELLOW}Waiting for services to start...${NC}"
    sleep 10
    
    # 检查服务状态
    echo -e "${GREEN}Checking service status...${NC}"
    docker-compose ps
    
    # 显示访问信息
    echo -e "\n${GREEN}Installation completed!${NC}"
    echo -e "${YELLOW}You can access the services at:${NC}"
    echo "Frontend: http://localhost:${FRONTEND_PORT}"
    echo "Backend API: http://localhost:${BACKEND_PORT}"
    
    # 显示日志查看命令
    echo -e "\n${YELLOW}To view logs, run:${NC}"
    echo "docker-compose logs -f"
}

# 运行安装
main