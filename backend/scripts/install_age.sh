#!/bin/bash
# Apache AGE 安装脚本
# 适用于 Ubuntu/Debian 系统

set -e

echo "🚀 开始安装 Apache AGE..."

# 检查 PostgreSQL 版本
PG_VERSION=$(psql -V | grep -oP '\d+\.\d+' | head -1)
echo "检测到 PostgreSQL 版本: $PG_VERSION"

if (( $(echo "$PG_VERSION < 13" | bc -l) )); then
    echo "❌ 错误: Apache AGE 需要 PostgreSQL 13 或更高版本"
    echo "当前版本: $PG_VERSION"
    exit 1
fi

# 1. 安装依赖
echo "📦 安装依赖..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    postgresql-server-dev-$PG_VERSION \
    postgresql-client-$PG_VERSION \
    git \
    cmake \
    flex \
    bison

# 2. 下载 Apache AGE
echo "📥 下载 Apache AGE..."
cd /tmp
if [ ! -d "age" ]; then
    git clone https://github.com/apache/age.git
fi
cd age

# 3. 切换到稳定版本 (使用 v1.5.0)
echo "🔧 切换到稳定版本..."
git checkout tags/agev1.5.0

# 4. 编译和安装
echo "🔨 编译 Apache AGE..."
make install

# 5. 配置 PostgreSQL
echo "⚙️ 配置 PostgreSQL..."

# 查找 postgresql.conf
PG_CONF=$(psql -U postgres -t -c "SHOW config_file;" | xargs)
echo "PostgreSQL 配置文件: $PG_CONF"

# 备份配置
sudo cp "$PG_CONF" "${PG_CONF}.backup.age"

# 添加 shared_preload_libraries
if ! grep -q "shared_preload_libraries.*age" "$PG_CONF"; then
    # 如果已有配置，追加；否则添加
    if grep -q "shared_preload_libraries" "$PG_CONF"; then
        sudo sed -i "s/shared_preload_libraries = '/shared_preload_libraries = 'age,/" "$PG_CONF"
    else
        echo "shared_preload_libraries = 'age'" | sudo tee -a "$PG_CONF"
    fi
fi

# 6. 重启 PostgreSQL
echo "🔄 重启 PostgreSQL..."
sudo systemctl restart postgresql

# 7. 验证安装
echo "✅ 验证安装..."
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS age;"
sudo -u postgres psql -c "LOAD 'age';"
sudo -u postgres psql -c "SELECT * FROM ag_catalog.ag_graph;"

echo ""
echo "🎉 Apache AGE 安装完成！"
echo ""
echo "下一步:"
echo "1. 创建图谱: SELECT create_graph('sparkle_galaxy');"
echo "2. 运行迁移脚本: python scripts/migrate_to_age.py"
echo ""
