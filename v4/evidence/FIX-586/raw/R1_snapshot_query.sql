-- R-1 快照通用查询（前/后各跑一次；只读）
\echo '=== A. 全部非系统 role（属性 + hash 指纹 sha256 前 12 位，零 hash 原文）==='
SELECT rolname, rolcanlogin AS login, rolsuper AS super, rolcreaterole AS createrole,
       (rolpassword IS NULL) AS pwd_null,
       CASE WHEN rolpassword IS NULL THEN 'NULL'
            ELSE length(rolpassword)::text || 'c sha256:' || substr(encode(sha256(convert_to(rolpassword,'UTF8')),'hex'),1,12) END AS pwd_fp
FROM pg_authid WHERE rolname NOT LIKE 'pg\_%' ORDER BY rolname;
\echo '=== B. 目标四 role 在全簇各库的 ACL 依赖计数（pg_shdepend deptype=a）==='
SELECT d.datname, r.rolname, count(*) AS acl_refs
FROM pg_shdepend s
JOIN pg_roles r ON r.oid = s.refobjid
JOIN pg_database d ON d.oid = s.dbid
WHERE r.rolname IN ('sparkle_gateway','sparkle_engine','sparkle_celery','sparkle_readonly')
GROUP BY d.datname, r.rolname ORDER BY d.datname, r.rolname;
\echo '=== C. 目标四 role 的 pg_shdepend deptype 汇总（o=归属阻塞 / a=ACL）==='
SELECT r.rolname, s.deptype, count(*) AS n
FROM pg_shdepend s JOIN pg_roles r ON r.oid = s.refobjid
WHERE r.rolname IN ('sparkle_gateway','sparkle_engine','sparkle_celery','sparkle_readonly')
GROUP BY r.rolname, s.deptype ORDER BY r.rolname;
\echo '=== D. pg_stat_activity 按 usename ==='
SELECT COALESCE(usename,'(null)') AS usename, count(*) AS conns FROM pg_stat_activity GROUP BY usename ORDER BY 2 DESC;
\echo '=== E. 簇内数据库清单 ==='
SELECT datname, pg_get_userbyid(datdba) AS owner, datallowconn FROM pg_database ORDER BY datname;
