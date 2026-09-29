-- FIX-586 R-1 孤儿 role 热修 SQL 全文（方案 A，诊断 v4/evidence/FIX-582/diagnosis.md §4 R-1）
-- 执行时刻：2026-09-29 12:3x UTC（DB 时钟 Etc/UTC），容器 sparkle_db（PG 16.15），库 sparkle
-- 执行通道：docker exec -i sparkle_db psql -U postgres -d sparkle（trust 容器内路径）；单事务 ON_ERROR_STOP=1，全成全败
-- 前置门禁（raw/R1_gate_precheck.txt，2026-09-29 12:31Z 实测）：
--   ① pg_stat_activity 四 role 活跃连接 = 0（全库连接面仅 postgres 48 + 后台 4）
--   ② pg_shdepend deptype 汇总：四 role 仅 'a'（ACL 授权，DROP 自动撤销），零 'o'（对象归属）
--   ③ pg_auth_members 双向零成员关系
--   停手条件（有活跃连接则停）未触发 → 放行
-- 凭据纪律：:'gw_pwd' 运行时经 stdin 注入 Sparkle-project/backend/gateway/.env 的 POSTGRES_PASSWORD 值，
--   零回显零落盘（对齐后新 hash 指纹见 raw/R1_snapshot_after.txt；对齐前孤儿 hash 指纹 5faa8c266d2a）。

BEGIN;

-- [1][2][3] 三 NULL 密码 role：c17 迁移建出但从未可登录（rolpassword NULL，任何密码 28P01），
--           零消费者零归属，DROP（pg_shdepend 'a' 类授权由服务端自动撤销）
DROP ROLE sparkle_engine;
DROP ROLE sparkle_celery;
DROP ROLE sparkle_readonly;

-- [4] sparkle_gateway 孤儿密码对齐：原 hash（sha256:5faa8c266d2a）无任何现行 .env 可匹配（孤儿）；
--     对齐至 gateway 自身现行凭据文件 Sparkle-project/backend/gateway/.env POSTGRES_PASSWORD
--     （USER=brsama 指纹 e2186dbdb1bb 同族值）。对齐后 gateway 若切 POSTGRES_USER=sparkle_gateway
--     即以最小权限身份连接（c17 GRANT 面保留未动）。共用值与专用 SPARKLE_GATEWAY_DB_PASSWORD 缺位
--     登记为 c17 最小权限债（docs/engineering/KNOWN_CODE_DEBT_LEDGER.md 2026-09-30 节）。
ALTER ROLE sparkle_gateway WITH PASSWORD :'gw_pwd';

COMMIT;

-- 回滚单位（诊断 §4 R-1「单 role（SQL 可逆重建成对）」）：三 role 可经 c17 同款
-- CREATE ROLE ... LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT 原样重建（其无密码态即原状）；
-- sparkle_gateway 可以 c17 GRANT 面重建脚本+原孤儿 hash 不可逆（原密码无人持有，孤儿态本身即废）——
-- 回滚=重建后重设任意新密码并文档化，语义等价。
