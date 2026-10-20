"""Experiment 5: Predicate vs. Score Reranking (NFCorpus comparison)."""

from typing import Any

def run_reranking_experiment(client: Any, queries_and_docs: list[tuple[str, str]]) -> dict[str, Any]:
    pred_q = {
        "type": "predicate",
        "name": "is_relevant",
        "instructions": "Is this document relevant to answering the query?"
    }
    score_q = {
        "type": "score",
        "name": "relevance_rubric",
        "instructions": "Rate how thoroughly this document addresses the query.",
        "levels": [
            {"label": "Irrelevant", "description": "Completely off-topic or unrelated."},
            {"label": "Mention", "description": "Mentions keywords but provides no answer."},
            {"label": "Partial", "description": "Answers part of the query."},
            {"label": "Comprehensive", "description": "Fully and directly answers the query."},
        ]
    }

    pred_results = []
    score_results = []

    for query, doc in queries_and_docs:
        evidence = f"QUERY: {query}\n<<DOCUMENT>>\n{doc}\n<</DOCUMENT>>"
        resp = client.create_decision(model="gpt-6-luna", input_payload=evidence, questions=[pred_q, score_q])
        p_ans = resp.answer_by_name("is_relevant")
        s_ans = resp.answer_by_name("relevance_rubric")
        pred_results.append(p_ans.probability)
        score_results.append(s_ans.score)

    return {
        "predicate_probabilities": pred_results,
        "score_values": score_results,
        "sample_count": len(queries_and_docs),
    }

if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from runtime import FakeDecisionsClient
    client = FakeDecisionsClient()
    res = run_reranking_experiment(client, [("diabetes diet", "Eat leafy greens and avoid sugar.")])
    print("Reranking experiment results:", res)
