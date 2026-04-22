# Rule AY - LLM Safety Wrapper

> Status: locked for Stage 37 finalization
> Scope: all `backend/app` LLM call sites outside tests and `_deprecated`

## 1. One-Sentence Definition

Raw vendor LLM clients and raw completion calls are forbidden outside approved wrappers.

Approved wrappers for Stage 37:

1. `LLMService`
2. `llm_client`
3. `SecureLLMClient.get(...)`
4. provider internals under `backend/app/services/llm/providers.py`

## 2. Forbidden Patterns

1. `openai.OpenAI(...)` or `AsyncOpenAI(...)` outside approved wrappers
2. `anthropic.Anthropic(...)` outside approved wrappers
3. direct `chat.completions.create(...)`
4. direct `.completion(...)` / `.acompletion(...)`

## 3. Exception Form

Single-line exception:

`# rule-ay: ignore <reason>`

Every exception must be registered in `docs/aurora/rule_ay_exceptions.md`.

## 4. Enforcement

Rule AY is fail-closed:

1. baseline target is `0`
2. any unregistered violation fails CI immediately
3. exceptions are temporary and auditable

## 5. Entry Point

- `scripts/guards/check_rule_ay_llm_safety.py`
