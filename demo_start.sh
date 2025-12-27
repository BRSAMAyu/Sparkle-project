#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting Sparkle Demo Environment...${NC}"

# 1. Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker.${NC}"
    exit 1
fi

# 2. Cleanup
echo "🧹 Cleaning up old containers..."
docker-compose down --remove-orphans

# 3. Start Services
echo "🔥 Starting services (this may take a minute)..."
docker-compose up -d --build

# 4. Wait for Health
wait_for_service() {
    local url=$1
    local name=$2
    local max_retries=30
    local count=0
    
    echo -n "Waiting for $name..."
    until curl -s -f "$url" > /dev/null; do
        sleep 2
        echo -n "."
        count=$((count+1))
        if [ $count -ge $max_retries ]; then
            echo -e "\n${RED}❌ $name failed to start.${NC}"
            docker-compose logs $name
            exit 1
        fi
    done
    echo -e "\n${GREEN}✅ $name is up!${NC}"
}

# Wait for DB first (approx)
sleep 5
wait_for_service "http://localhost:8000/health" "Python Backend"
wait_for_service "http://localhost:8080/api/v1/health" "Go Gateway"

# 5. Seed Data
echo "🌱 Seeding mock data..."
# Note: Path inside container depends on COPY structure. 
# backend/seed_data -> /app/seed_data
docker-compose exec -T sparkle_backend python seed_data/load_seed_data.py || echo -e "${RED}⚠️  Seeding failed or skipped.${NC}"

echo -e "${GREEN}🎉 Sparkle System Ready!${NC}"
echo "➡️  Gateway API: http://localhost:8080"
echo "➡️  Chaos Switch: POST http://localhost:8080/admin/chaos/inject?type=latency&duration=5s"
echo "➡️  Grafana: http://localhost:3000 (if enabled)"