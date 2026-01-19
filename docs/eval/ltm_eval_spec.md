# LTM Evaluation Dataset Spec

This document defines the JSONL schema for deterministic LTM evaluation. Each line is a JSON object.

## Required fields
- case_id: string
- user_id: uuid string
- intent: "chat" | "learning" | "planning"
- expected_pref_keys: list of preference keys
- expected_goal_titles: list of goal title strings (exact or substring match)
- expected_episodic_contains: list of substrings to match in episodic summaries
- forbidden_contains: list of substrings that must not appear in returned items

## Optional fields
- max_episodic_age_days: integer
- notes: string

## Example
{"case_id":"case_1","user_id":"00000000-0000-0000-0000-000000000001","intent":"chat","expected_pref_keys":["depth_preference"],"expected_goal_titles":["finish algebra"],"expected_episodic_contains":["tutoring session"],"forbidden_contains":["private"],"max_episodic_age_days":30}
