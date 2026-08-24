"""
Run Comparison & Regression Detection for CodeAgentPro Eval Pipeline.
Diffs baseline vs candidate run files and flags quality or performance regressions.
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


class EvalComparator:
    """
    Compares two evaluation run JSON files (baseline vs candidate).
    """

    @staticmethod
    def load_run(file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Run file not found: {file_path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def compare_runs(
        baseline_path: str,
        candidate_path: str,
        regression_threshold: float = 0.05
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Compares candidate against baseline.
        Returns (comparison_dict, has_regression).
        """
        base = EvalComparator.load_run(baseline_path)
        cand = EvalComparator.load_run(candidate_path)

        base_summary = base.get("summary", {})
        cand_summary = cand.get("summary", {})

        diff_metrics = {
            "pass_at_1": {
                "baseline": base_summary.get("pass_at_1", 0.0),
                "candidate": cand_summary.get("pass_at_1", 0.0),
                "delta": round(cand_summary.get("pass_at_1", 0.0) - base_summary.get("pass_at_1", 0.0), 4),
            },
            "pass_at_k": {
                "baseline": base_summary.get("pass_at_k", 0.0),
                "candidate": cand_summary.get("pass_at_k", 0.0),
                "delta": round(cand_summary.get("pass_at_k", 0.0) - base_summary.get("pass_at_k", 0.0), 4),
            },
            "give_up_rate": {
                "baseline": base_summary.get("give_up_rate", 0.0),
                "candidate": cand_summary.get("give_up_rate", 0.0),
                "delta": round(cand_summary.get("give_up_rate", 0.0) - base_summary.get("give_up_rate", 0.0), 4),
            },
            "avg_latency": {
                "baseline": base_summary.get("avg_latency_per_task", 0.0),
                "candidate": cand_summary.get("avg_latency_per_task", 0.0),
                "delta": round(cand_summary.get("avg_latency_per_task", 0.0) - base_summary.get("avg_latency_per_task", 0.0), 3),
            },
        }

        # Task level status changes
        base_tasks = {t["task_id"]: t for t in base.get("tasks", [])}
        cand_tasks = {t["task_id"]: t for t in cand.get("tasks", [])}

        regressed_tasks: List[str] = []
        improved_tasks: List[str] = []

        for tid, base_t in base_tasks.items():
            cand_t = cand_tasks.get(tid)
            if not cand_t:
                continue
            base_pass = base_t.get("passed", False)
            cand_pass = cand_t.get("passed", False)

            if base_pass and not cand_pass:
                regressed_tasks.append(tid)
            elif not base_pass and cand_pass:
                improved_tasks.append(tid)

        # Regressions check
        p1_drop = diff_metrics["pass_at_1"]["delta"] < -regression_threshold
        pk_drop = diff_metrics["pass_at_k"]["delta"] < -regression_threshold
        has_regression = p1_drop or pk_drop or (len(regressed_tasks) > 0)

        comparison_report = {
            "baseline_meta": base.get("metadata", {}),
            "candidate_meta": cand.get("metadata", {}),
            "diff_metrics": diff_metrics,
            "regressed_tasks": regressed_tasks,
            "improved_tasks": improved_tasks,
            "has_regression": has_regression,
            "regression_threshold": regression_threshold,
        }

        return comparison_report, has_regression

    @staticmethod
    def print_comparison(comp: Dict[str, Any]) -> None:
        diffs = comp["diff_metrics"]
        print("=" * 60)
        print(" EVALUATION COMPARISON REPORT")
        print("=" * 60)
        print(f"Baseline  : {comp['baseline_meta'].get('model')} ({comp['baseline_meta'].get('git_commit')})")
        print(f"Candidate : {comp['candidate_meta'].get('model')} ({comp['candidate_meta'].get('git_commit')})")
        print("-" * 60)
        print(f"{'Metric':<20} | {'Baseline':<10} | {'Candidate':<10} | {'Delta':<10}")
        print("-" * 60)
        for m_name, vals in diffs.items():
            sign = "+" if vals['delta'] > 0 else ""
            print(f"{m_name:<20} | {vals['baseline']:<10} | {vals['candidate']:<10} | {sign}{vals['delta']:<10}")
        print("-" * 60)
        if comp["regressed_tasks"]:
            print(f"[REGRESSIONS FLIPPED PASS->FAIL]: {', '.join(comp['regressed_tasks'])}")
        if comp["improved_tasks"]:
            print(f"[IMPROVEMENTS FLIPPED FAIL->PASS]: {', '.join(comp['improved_tasks'])}")
        if comp["has_regression"]:
            print("[WARNING] Quality Regressions Detected!")
        else:
            print("[SUCCESS] No Regressions Detected.")
        print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m eval.compare <baseline_json> <candidate_json> [threshold]")
        sys.exit(1)
    b_file = sys.argv[1]
    c_file = sys.argv[2]
    thresh = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
    report, regressed = EvalComparator.compare_runs(b_file, c_file, thresh)
    EvalComparator.print_comparison(report)
    if regressed:
        sys.exit(1)
