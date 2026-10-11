"""The evaluation runner: the dev/test split is fixed, and tokens are counted."""
from app.llm import BedrockClassifier
from eval import run_eval


class FakeBedrock:
    """Stands in for the Bedrock client. Answers every request as one dietary need."""

    def converse(self, **kwargs):
        assert kwargs["toolConfig"]["toolChoice"] == {"tool": {"name": "route_request"}}
        return {
            "output": {"message": {"content": [{"toolUse": {"input": {
                "language": "en", "confidence": 0.9,
                "intents": [{"category": "dietary", "priority": "routine", "summary_en": "Wants water"}],
            }}}]}},
            "usage": {"inputTokens": 500, "outputTokens": 40},
        }


def test_split_is_fixed_and_covers_everything():
    everything = run_eval.load_items(run_eval.HERE / "requests.jsonl")
    dev = run_eval.load_items(run_eval.HERE / "requests.jsonl", "dev")
    test = run_eval.load_items(run_eval.HERE / "requests.jsonl", "test")
    assert len(dev) + len(test) == len(everything) == 136
    assert not {i["id"] for i in dev} & {i["id"] for i in test}
    assert [i["id"] for i in dev] == [i["id"] for i in run_eval.load_items(run_eval.HERE / "requests.jsonl", "dev")]
    for name in {i["slice"] for i in everything}:          # every slice appears in both halves
        assert any(i["slice"] == name for i in dev) and any(i["slice"] == name for i in test)


def test_tokens_are_counted_per_call():
    classifier = BedrockClassifier(model_id="fake", client=FakeBedrock())
    rows, latencies = run_eval.score(run_eval.load_items(run_eval.HERE / "requests.jsonl", "dev")[:5], classifier)
    assert len(rows) == len(latencies) == 5
    assert (classifier.calls, classifier.input_tokens, classifier.output_tokens) == (5, 2500, 200)


def test_baseline_run_prints_a_summary(capsys):
    assert run_eval.main(["--mode", "baseline", "--split", "test"]) == 0
    assert "SUMMARY | baseline | test |" in capsys.readouterr().out


def test_model_run_reports_tokens_and_cost(capsys, monkeypatch):
    monkeypatch.setattr(run_eval, "bedrock_classifier",
                        lambda model_id: BedrockClassifier(model_id=model_id, client=FakeBedrock()))
    assert run_eval.main(["--model", "fake-model", "--split", "dev", "--price-in", "1", "--price-out", "5"]) == 0
    out = capsys.readouterr().out
    assert "Tokens per request: 500 in, 40 out  (70 calls)" in out      # the warm-up call is not counted
    assert "Model cost: $0.70 per 1,000 requests" in out
    assert "SUMMARY | fake-model | dev |" in out


def test_setup_problem_stops_the_run_with_the_real_error(capsys, monkeypatch):
    def broken(model_id):
        raise RuntimeError("AccessDeniedException: not allowed to call this model")
    monkeypatch.setattr(run_eval, "bedrock_classifier", broken)
    assert run_eval.main(["--model", "blocked-model"]) == 2
    assert "AccessDeniedException" in capsys.readouterr().out
