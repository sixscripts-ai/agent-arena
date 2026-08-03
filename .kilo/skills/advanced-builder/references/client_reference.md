# Client Reference

From backend/agent_arena/sandbox/client.py

- Transport protocol post(path, json)
- HttpTransport(base_url, internal_key, timeout 180): retries 3, headers X-Internal-Key, handles 5xx retry
- FakeTransport for tests: calls list, model_replies dict, judge_result, rounds list; post handles /internal/model, /internal/judge, /internal/round
- InternalClient(transport): model(battle_id, model_id, messages, phase="") -> content, judge(battle_id, rubric, artifacts, weights), round(battle_id, phase, model_id, artifact, event_type="artifact")
