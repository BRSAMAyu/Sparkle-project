## Lane B Handoff
启用 inferred memory、Stage18 aggregator、Stage33 social 默认 live；统一 idiographic/SRL/social/aggregator 三态，shadow 只算不写不发。扩展 stage23-31/33 Admin，补 drill 与 env。

验证：33 pytest、ruff、Rule Y/AV/BE、drill 通过；全量 guards 仅剩 Rule K/AX 既有失败。
