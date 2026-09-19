# V3 Deployment

## Topology
Flutter/Web → HTTPS/WSS Gateway → Python gRPC/FastAPI internal → PostgreSQL/Redis/MinIO/Celery workers → external model providers。

## Rules
- API/model secrets server-only；
- FastAPI 8000 不公网裸露；
- environment config 不编译进 App；
- staging/prod data 分离；
- TLS + origin/cors/WS ticket；
- Agent run 持久化在服务端。

## Remote test
至少一套公网 staging：fresh device 不接开发机 localhost 即可完成 GJ01/GJ06/GJ08。

## Demo stability
演示机保留本地 fallback deployment，但不能用假模型假数据；预热只优化缓存/连接，不预生成用户要看的结果。
