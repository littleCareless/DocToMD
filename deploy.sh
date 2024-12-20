#!/bin/bash

# 加载环境变量
set -a
source .env
set +a

# 启动主服务
docker-compose -f docker-compose.yml \
    -f docker-compose.worker.yml \
    up -d --scale celery_worker=4

# 启动监控服务
docker-compose -f docker-compose.monitoring.yml up -d

# 启动备份服务
docker-compose -f docker-compose.backup.yml up -d

# 等待服务启动
sleep 10

# 检查服务健康状态
docker-compose ps

# 显示服务日志
docker-compose logs -f 