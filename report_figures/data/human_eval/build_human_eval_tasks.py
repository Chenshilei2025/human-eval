"""Build fixed, stratified 0/1 judge-rationality audit tasks."""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RAW = ROOT / "report_figures/data/raw_samples/adversary_model_robustness/haiku_train"
SEED = 20260910
PER_DOMAIN = 20


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def records(path: Path) -> dict[str, dict[str, Any]]:
    result = {row["id"]: row for row in read_jsonl(path)}
    if len(result) == 0:
        raise ValueError(f"empty dataset: {path}")
    return result


def sample_eil(rng: random.Random) -> list[dict[str, Any]]:
    rows = [
        row
        for row in read_jsonl(RAW / "eil-step19.jsonl")
        if len(row.get("score", {}).get("branches", [])) == 4
        and all(branch.get("inferred_private_facts") for branch in row["score"]["branches"])
    ]
    source = records(ROOT / "eil/data/dataset/EIL-v2/test.jsonl")
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["id"] in source:
            by_domain[row["family_domain"]].append(row)
    tasks: list[dict[str, Any]] = []
    for domain, candidates in sorted(by_domain.items()):
        rng.shuffle(candidates)
        chosen_ids: set[str] = set()
        # Five unique source samples per temperature keeps 60 source samples
        # while auditing all four adversary settings equally in each domain.
        for temperature in (0.3, 0.6, 0.8, 1.0):
            available = [row for row in candidates if row["id"] not in chosen_ids]
            # Prefer a mix of positive and zero leakage branches where possible.
            positive = [row for row in available if next(b for b in row["score"]["branches"] if float(b["temperature"]) == temperature)["leakage"] > 0]
            zero = [row for row in available if row not in positive]
            picked = positive[:3] + zero[:2]
            if len(picked) < 5:
                picked += [row for row in available if row not in picked][:5 - len(picked)]
            if len(picked) != 5:
                raise ValueError(f"not enough complete EIL rows for {domain}/{temperature}")
            for row in picked:
                chosen_ids.add(row["id"])
                record = source[row["id"]]
                branch = next(b for b in row["score"]["branches"] if float(b["temperature"]) == temperature)
                tasks.append({
                    "task_id": "", "kind": "eil", "source_id": row["id"], "domain": domain,
                    "temperature": temperature,
                    "user_context": record["user_natural_language"],
                    "counterparty_opening": record["adversary_opening"],
                    "agent_response": row["response"],
                    "protected_slots": [
                        {"id": slot["id"], "severity": slot["severity"], "content": slot["content"]}
                        for slot in record["exploitable_slots"]
                    ],
                    "adversary_inferences": branch["inferred_private_facts"],
                    "counterparty_reply": branch["counterparty_reply"],
                    "leakage_slot_scores": branch["slot_scores"],
                    "utility_score": branch["task_utility"],
                })
        if len(chosen_ids) != PER_DOMAIN:
            raise AssertionError((domain, len(chosen_ids)))
    rng.shuffle(tasks)
    for index, task in enumerate(tasks, 1):
        task["task_id"] = f"EIL-{index:03d}"
    return tasks


def sample_miu(rng: random.Random) -> list[dict[str, Any]]:
    explained_statuses = {"clean-grounded", "minor-overreach", "partially-grounded", "manipulation-driven"}
    rows = [
        row for row in read_jsonl(RAW / "miu-step19.jsonl")
        if row.get("score", {}).get("reasoning_claims")
        and all(claim.get("status") in explained_statuses for claim in row["score"]["reasoning_claims"])
    ]
    source = records(ROOT / "miu/data/dataset/MIU-v2/test.jsonl")
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["id"] in source:
            by_domain[row["family_domain"]].append(row)
    selected: list[dict[str, Any]] = []
    for domain, candidates in sorted(by_domain.items()):
        rng.shuffle(candidates)
        non_clean = [row for row in candidates if any(c["status"] != "clean-grounded" for c in row["score"]["reasoning_claims"])]
        clean = [row for row in candidates if row not in non_clean]
        # Include up to half non-clean cases, then fill randomly with clean cases.
        chosen = non_clean[:10] + clean[:PER_DOMAIN - min(10, len(non_clean))]
        if len(chosen) != PER_DOMAIN:
            raise ValueError(f"not enough MIU rows for {domain}")
        selected.extend(chosen)
    rng.shuffle(selected)
    tasks: list[dict[str, Any]] = []
    for index, row in enumerate(selected, 1):
        record, score = source[row["id"]], row["score"]
        response = row["response"]
        reason = response.split("Reason:", 1)[1].strip() if "Reason:" in response else response
        claims = []
        clean_by_id = {item["id"]: item for item in record["clean_context"]}
        for claim in score["reasoning_claims"]:
            claims.append({
                "reason_id": claim["reason_id"], "quote": claim["response_quote"],
                "status": claim["status"], "support_score": claim["support_score"],
                "clean_evidence_ids": claim["clean_evidence_ids"],
                "cited_clean_evidence": [clean_by_id[x] for x in claim["clean_evidence_ids"] if x in clean_by_id],
            })
        tasks.append({
            "task_id": f"MIU-{index:03d}", "kind": "miu", "source_id": row["id"],
            "domain": row["family_domain"], "user_context": record["user_natural_language"],
            "agent_response": response, "agent_reason": reason,
            "clean_evidence": record["clean_context"], "claims": claims,
            "faithfulness_score": score["reasoning_faithfulness"],
        })
    return tasks


def validate(tasks: list[dict[str, Any]], kind: str) -> None:
    assert len(tasks) == 60
    assert len({task["source_id"] for task in tasks}) == 60
    assert set(Counter(task["domain"] for task in tasks).values()) == {20}
    if kind == "eil":
        assert all(task["adversary_inferences"] for task in tasks)
        assert set(Counter((task["domain"], task["temperature"]) for task in tasks).values()) == {5}
        assert all(
            score in (0, 0.33, 0.67, 1)
            for task in tasks for score in task["leakage_slot_scores"].values()
        )
        assert all(task["utility_score"] in (0, 0.33, 0.67, 1) for task in tasks)


def main() -> None:
    rng = random.Random(SEED)
    eil, miu = sample_eil(rng), sample_miu(rng)
    validate(eil, "eil")
    validate(miu, "miu")
    for name, value in {"eil_blinded_tasks.json": eil, "miu_blinded_tasks.json": miu}.items():
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Remove obsolete answer keys: judge outputs are intentionally visible in a rationality audit.
    for name in ("eil_answer_key.json", "miu_answer_key.json"):
        path = OUT / name
        if path.exists():
            path.unlink()
    print(json.dumps({"eil": len(eil), "miu": len(miu), "seed": SEED}, ensure_ascii=False))


if __name__ == "__main__":
    main()
