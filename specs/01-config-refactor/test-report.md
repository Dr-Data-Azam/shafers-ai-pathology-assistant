# Test Report: Config Refactor
Date:       2026-05-15
Branch:     feature/config-refactor
Written by: test-writer agent

## Test Files
- `tests/test_config.py` — 25 tests (5 original + 20 added by test-writer agent)
- `tests/test_llm_provider_manager.py` — 27 tests (all new)

## Results
52 written | 52 passed | 0 failed

## Test List

### tests/test_config.py
| Test | Verifies |
|------|----------|
| test_defaults_applied_with_both_keys | All 16 default values are correct when both keys are set |
| test_missing_both_llm_keys_raises | ValidationError raised when neither LLM key is present |
| test_only_openai_key_is_sufficient | Config validates with OpenAI key alone; groq_api_key is None |
| test_only_groq_key_is_sufficient | Config validates with Groq key alone; openai_api_key is None |
| test_env_var_overrides_default | retriever_k, temperature, chat_history_path can be overridden via env |
| test_both_keys_stored_correctly | Both keys are stored on the config object when both are provided |
| test_huggingface_token_is_optional | Config loads fine without HUGGINGFACEHUB_ACCESS_TOKEN |
| test_huggingface_token_stored_when_set | HF token is stored when the env var is present |
| test_validation_error_message_mentions_at_least_one_key | Error text references the missing key requirement |
| test_db_path_override | DB_PATH env var overrides the default vector DB path |
| test_retriever_path_override | RETRIEVER_PATH env var overrides the default pickle path |
| test_data_path_override | DATA_PATH env var overrides the default data directory |
| test_openai_model_override | OPENAI_MODEL env var overrides the default model string |
| test_groq_model_override | GROQ_MODEL env var overrides the default Groq model string |
| test_embedding_model_override | EMBEDDING_MODEL env var overrides the embedding model name |
| test_max_tokens_override | MAX_TOKENS env var is parsed as int and overrides 1500 |
| test_llm_timeout_override | LLM_TIMEOUT env var is parsed as int and overrides 60 |
| test_retriever_fetch_k_override | RETRIEVER_FETCH_K env var overrides the default 25 |
| test_retriever_lambda_mult_override | RETRIEVER_LAMBDA_MULT env var is parsed as float |
| test_max_context_docs_override | MAX_CONTEXT_DOCS env var overrides the default 20 |
| test_chunk_size_override | CHUNK_SIZE env var overrides the default 500 |
| test_chunk_overlap_override | CHUNK_OVERLAP env var overrides the default 50 |
| test_get_config_is_singleton | get_config() returns the same object on repeated calls |
| test_get_config_cache_clear_returns_fresh_instance | After cache_clear(), get_config() builds a new instance |
| test_get_config_reads_updated_env_after_cache_clear | Fresh call picks up env changes made after cache_clear() |

### tests/test_llm_provider_manager.py
| Test | Verifies |
|------|----------|
| test_get_available_providers_openai_only | Only OpenAI key set returns ["openai"] |
| test_get_available_providers_groq_only | Only Groq key set returns ["groq"] |
| test_get_available_providers_both | Both keys set returns a list with both providers |
| test_get_available_providers_none | No keys returns empty list |
| test_validate_provider_openai_passes | validate_provider("openai") returns True with OpenAI key set |
| test_validate_provider_groq_passes | validate_provider("groq") returns True with Groq key set |
| test_validate_provider_no_keys_raises | No keys raises Exception with "No API keys found" |
| test_validate_provider_openai_requested_but_only_groq_set_raises | Missing OpenAI key raises with OPENAI_API_KEY hint |
| test_validate_provider_groq_requested_but_only_openai_set_raises | Missing Groq key raises with GROQ_API_KEY hint |
| test_validate_provider_case_insensitive_openai | Uppercase "OPENAI" is not in the lowercase available list — documents actual behaviour |
| test_load_llm_openai_constructs_correctly | ChatOpenAI is called with model, temperature, max_tokens, timeout from config |
| test_load_llm_groq_constructs_correctly | ChatGroq is called with model, temperature, max_tokens, timeout from config |
| test_load_llm_openai_is_cached | Second call to load_llm("openai") does not call ChatOpenAI constructor again |
| test_load_llm_groq_is_cached | Second call to load_llm("groq") does not call ChatGroq constructor again |
| test_load_llm_openai_rebuilds_after_cache_clear | After clear_llm_cache(), load_llm("openai") constructs a fresh instance |
| test_load_llm_groq_rebuilds_after_cache_clear | After clear_llm_cache(), load_llm("groq") constructs a fresh instance |
| test_load_llm_invalid_provider_raises_exception | Unknown provider "anthropic" raises Exception |
| test_load_llm_openai_construction_failure_is_wrapped | ChatOpenAI constructor error is wrapped as "Failed to load OpenAI model" |
| test_load_llm_groq_construction_failure_is_wrapped | ChatGroq constructor error is wrapped as "Failed to load Groq model" |
| test_load_llm_uses_config_temperature | Temperature passed to ChatOpenAI matches config value (0.3) |
| test_load_llm_openai_provider_case_insensitive | Uppercase "OPENAI" is rejected by validate_provider — documents real behaviour |
| test_get_provider_info_openai_returns_correct_fields | OpenAI info dict contains all expected keys and correct name |
| test_get_provider_info_groq_returns_correct_fields | Groq info dict contains all expected keys and correct name |
| test_get_provider_info_unknown_provider_returns_empty_dict | Unknown provider returns {} without raising |
| test_get_provider_info_case_insensitive | "OPENAI" resolves to the openai entry via .lower() |
| test_clear_llm_cache_resets_both_globals | After populating both caches, clear_llm_cache() sets both globals to None |
| test_clear_llm_cache_is_idempotent | Calling clear_llm_cache() when already empty does not raise |

## Coverage Notes
- `config.py`: 100% — all branches exercised
- `llm_provider_manager.py`: 98% — line 81 (`raise ValueError`) is unreachable; validate_provider() always fires first
- All other modules: 0% — outside scope of this feature
