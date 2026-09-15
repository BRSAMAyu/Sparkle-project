-- Post-launch: Validate all CHECK constraints added by wp18 migration
-- These were marked NOT VALID to avoid full table scans during migration.
-- Run this after launch when the database has sufficient idle time.
-- Each statement will scan the relevant table to verify existing rows satisfy the constraint.
-- If any row violates a constraint, the VALIDATE will fail with a descriptive error.

-- shop_purchases: 3 constraints
ALTER TABLE shop_purchases VALIDATE CONSTRAINT chk_shop_purchases_balance_after_non_negative;
ALTER TABLE shop_purchases VALIDATE CONSTRAINT chk_shop_purchases_balance_before_non_negative;
ALTER TABLE shop_purchases VALIDATE CONSTRAINT chk_shop_purchases_price_paid_non_negative;

-- tasks: 6 constraints
ALTER TABLE tasks VALIDATE CONSTRAINT chk_tasks_actual_minutes_non_negative;
ALTER TABLE tasks VALIDATE CONSTRAINT chk_tasks_difficulty_range;
ALTER TABLE tasks VALIDATE CONSTRAINT chk_tasks_energy_cost_range;
ALTER TABLE tasks VALIDATE CONSTRAINT chk_tasks_estimated_minutes_non_negative;
ALTER TABLE tasks VALIDATE CONSTRAINT chk_tasks_subtask_counts_non_negative;
ALTER TABLE tasks VALIDATE CONSTRAINT chk_tasks_subtasks_completed_lte_total;

-- users: 5 constraints
ALTER TABLE users VALIDATE CONSTRAINT chk_users_curiosity_preference_range;
ALTER TABLE users VALIDATE CONSTRAINT chk_users_depth_preference_range;
ALTER TABLE users VALIDATE CONSTRAINT chk_users_flame_brightness_range;
ALTER TABLE users VALIDATE CONSTRAINT chk_users_flame_level_range;
ALTER TABLE users VALIDATE CONSTRAINT chk_users_photon_balance_non_negative;
