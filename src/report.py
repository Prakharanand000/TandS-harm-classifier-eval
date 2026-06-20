"""Render the analyst memo from a results dict, following the Part-1 structure:
TL;DR -> scope/method -> aggregate -> slice -> adversarial -> error analysis ->
recommendations -> limitations. Writes MEMO markdown and (if matplotlib is
available) a PR curve and a cost-vs-impact plot.
"""
from __future__ import annotations

import os
from typing import Dict

POP = 10_000_000  # illustrative population volume for absolute-scale translation


def _abs_gap(recall_gap: float) -> str:
    return f"~{int(recall_gap * POP):,} missed items/period at {POP:,}-item volume"


def _table(rows, cols, headers=None):
    headers = headers or cols
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join(["---"] * len(cols)) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def render_memo(results: Dict, meta: Dict) -> str:
    b = results["baseline"]
    thr = results["threshold"]
    head = results["headline"]
    ws = head["worst_slice"]
    cb = head["cheapest_break"]

    overall_recall = b["recall"]
    slice_gap = overall_recall - ws["recall"] if ws else 0.0

    L = []
    L.append(f"# Evaluation memo: {meta.get('model_name','classifier')} on {meta.get('dataset_name','dataset')}")
    L.append(f"_Author: {meta.get('author','')} | Scope: aggregate performance, "
             f"subgroup failure modes, adversarial robustness | Operating threshold: {thr}_\n")

    # 2. TL;DR
    L.append("## TL;DR")
    L.append(f"- Aggregate F1 is **{b['f1']:.2f}** (precision {b['precision']:.2f}, "
             f"recall {b['recall']:.2f}) at threshold {thr} — the headline looks healthy.")
    if ws:
        L.append(f"- That aggregate **masks a slice cliff**: `{ws['column']}={ws['value']}` "
                 f"recall is **{ws['recall']:.2f}** vs {overall_recall:.2f} overall "
                 f"(gap {slice_gap:.2f}; {_abs_gap(slice_gap)}).")
    if cb:
        L.append(f"- A **low-cost evasion** (`{cb['evasion']}`, effort {cb['effort']}, "
                 f"fluency penalty {cb['fluency_penalty']}) drops recall to "
                 f"**{cb['recall_after']:.2f}** (ESR {cb['esr']:.2f}); defensive "
                 f"normalization recovers it to {cb['recall_after_defense']:.2f}.")
    L.append(f"- Recommended: ship the normalization preprocessor, re-collect labels "
             f"for the weak slice, and monitor slice recall as a guardrail metric.\n")

    # 3. Scope, data & method
    L.append("## Scope, data & method")
    L.append(f"Model evaluated: **{meta.get('model_name','')}**. Dataset: "
             f"**{meta.get('dataset_name','')}** (n={results['n']}). "
             f"Operating threshold {thr}, chosen for the precision/recall trade-off "
             f"shown below (T&S operates at the operating point, not at AUC). "
             f"Calibration: ECE {b.get('ece', float('nan')):.3f}.")
    L.append("\n> **Data ethics.** No real egregious-harms content was used. Public "
             "proxy data was chosen deliberately: handling CSAM / NCII / violent "
             "extremism material outside a sanctioned, legally-authorized pipeline "
             "is neither lawful nor responsible. The methods transfer directly to "
             "the production setting; the data does not.\n")

    # 4. Aggregate
    L.append("## Aggregate performance")
    b_disp = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in b.items()}
    L.append(_table([b_disp], ["precision", "recall", "f1", "fpr", "support"]))
    L.append("")

    # 5. Slice analysis
    L.append("## Subgroup / slice analysis — headline finding")
    if not results["slices"]:
        L.append("\n_No slice columns were available for this dataset, so no subgroup "
                 "breakdown could be computed. Aggregate metrics above therefore carry "
                 "an unquantified subgroup risk — see limitations._\n")
    for col, tbl in results["slices"].items():
        L.append(f"\n**By `{col}`:**\n")
        L.append(_table(tbl, [col, "n", "support", "precision", "recall", "fpr"]))
    if meta.get("identity_proxy") and "identity_mention" in results["slices"]:
        L.append("\n> `identity_mention` here is a **keyword proxy** (does the comment "
                 "mention a protected-attribute term?), not a ground-truth identity "
                 "label — the public dataset carries none. It under-counts coded "
                 "references and over-counts neutral mentions, so read the gap as "
                 "indicative, not precise.")
    if ws:
        L.append(f"\nThe `{ws['column']}={ws['value']}` slice is the failure aggregate "
                 f"metrics hide: recall **{ws['recall']:.2f}** on {ws['support']} positives. "
                 f"At production volume that gap is {_abs_gap(slice_gap)} — the kind of "
                 f"nuanced, easily-missed problem that only appears once you slice.\n")

    # 6. Adversarial
    L.append("## Adversarial robustness")
    L.append("Each evasion is applied to items the model caught at baseline. "
             "ESR = share of caught items that now evade. `recall_after_defense` "
             "is recall once the normalization pipeline is applied first.\n")
    L.append(_table(results["adversarial"],
                    ["evasion", "effort", "fluency_penalty", "esr",
                     "recall_after", "recall_after_defense"],
                    ["evasion", "effort", "fluency pen.", "ESR",
                     "recall (attacked)", "recall (defended)"]))
    if any(r["evasion"] == "llm_paraphrase" for r in results["adversarial"]):
        L.append("\n`llm_paraphrase` is a **semantic** evasion (LLM reword, judged "
                 "label-preserving), not a character trick. Note its "
                 "`recall (defended)` barely improves on `recall (attacked)`: "
                 "normalization removes surface obfuscation but cannot reverse a "
                 "fluent rewrite. That row is the case for training-data "
                 "augmentation over preprocessing — its survivors are written to "
                 "`outputs/redteam_variants.jsonl`.")
    L.append("")

    # 7. Error analysis
    L.append("## Error analysis (qualitative)")
    L.append("_Representative false negatives (missed harmful):_")
    for e in results["errors"]["false_negatives"][:5]:
        L.append(f"- `{e['text']}` (score {e['score']:.2f})")
    L.append("\n_Representative false positives (over-flagged benign):_")
    for e in results["errors"]["false_positives"][:5]:
        L.append(f"- `{e['text']}` (score {e['score']:.2f})")
    L.append("")

    # 8. Recommendations
    L.append("## Recommendations")
    recs = ["**Ship a normalization preprocessor** (zero-width strip, NFKC, "
            "confusable folding, combining-mark strip, char-spacing collapse, "
            "de-leet) ahead of the classifier. The table above shows it recovers "
            "most recall lost to cheap character-level evasions."]
    if ws:
        recs.append(f"**Close the `{ws['column']}` gap**: targeted label collection and "
                    f"training augmentation for the `{ws['value']}` slice; route to a "
                    f"language-aware / multilingual model where applicable.")
    recs.append("**Augment training data** with the surviving adversarial variants "
                "(including LLM-generated paraphrases) as hard negatives.")
    recs.append("**Monitor slice recall as a guardrail**, not just aggregate F1, so "
                "the next blind spot is caught in metrics rather than in the wild.")
    for i, r in enumerate(recs, 1):
        L.append(f"{i}. {r}")
    L.append("")

    # 9. Limitations
    L.append("## Limitations & next steps")
    L.append("- Proxy data understates production distribution shift and the hardest "
             "(implicit / context-dependent) harms.")
    L.append("- Semantic evasions (coded language, paraphrase) need the LLM red-team "
             "layer and human label-preservation checks to evaluate properly.")
    L.append("- Next: extend to multimodal (text-in-image OCR bypass) and add "
             "conversation-level context signals.\n")
    return "\n".join(L)


def write_plots(results: Dict, outdir: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    os.makedirs(outdir, exist_ok=True)

    # PR curve
    pr = results["pr_curve"]
    ts = [p[0] for p in pr]; ps = [p[1] for p in pr]; rs = [p[2] for p in pr]
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(rs, ps, marker=".")
    ax.set_xlabel("recall"); ax.set_ylabel("precision"); ax.set_title("PR curve")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "pr_curve.png"), dpi=120)
    plt.close(fig)

    # cost-vs-impact (ESR vs effort, sized by fluency penalty)
    adv = results["adversarial"]
    eff_map = {"low": 0, "low-med": 1, "med": 2, "high": 3}
    flu_map = {"zero": 200, "low": 140, "low-med": 100, "med": 60, "high": 30}
    fig, ax = plt.subplots(figsize=(6, 4))
    for r in adv:
        x = eff_map.get(r["effort"], 0)
        ax.scatter(x, r["esr"], s=flu_map.get(r["fluency_penalty"], 60), alpha=0.6)
        ax.annotate(r["evasion"], (x, r["esr"]), fontsize=7,
                    xytext=(4, 2), textcoords="offset points")
    ax.set_xlabel("attacker effort (0=low)"); ax.set_ylabel("evasion success rate")
    ax.set_title("Cost vs impact (marker size = stealth)")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "cost_vs_impact.png"), dpi=120)
    plt.close(fig)
