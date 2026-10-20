"""Experiment 6: Cascade vs. Batch Cost Simulation."""

def simulate_cascade_economics(
    doc_sizes: list[int] = [1000, 3000, 6000, 10000],
    p_rates: list[float] = [0.01, 0.05, 0.10, 0.20, 0.40],
    q_gated_tokens: int = 80,
    detail_surcharge: int = 0,
) -> list[dict]:
    """
    Simulates token cost differences between batching vs cascading
    across document lengths and gating pass rates.
    """
    rows = []
    for s in doc_sizes:
        for p in p_rates:
            cost_batch = q_gated_tokens + detail_surcharge
            cost_cascade = p * (s + q_gated_tokens)
            verdict = "cascade" if cost_cascade < cost_batch else "batch"
            savings = abs(cost_batch - cost_cascade)
            rows.append({
                "doc_size": s,
                "p_gate": p,
                "cost_batch": cost_batch,
                "cost_cascade": round(cost_cascade, 2),
                "recommended": verdict,
                "savings": round(savings, 2),
            })
    return rows

if __name__ == "__main__":
    results = simulate_cascade_economics()
    print(f"Computed {len(results)} simulation points.")
    print("Sample point:", results[0])
