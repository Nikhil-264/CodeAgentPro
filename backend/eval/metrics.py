"""
Metrics Calculator for CodeAgentPro Eval Pipeline.
Aggregates task evaluation results into summary benchmarks.
"""
from typing import Any, Dict, List


class EvalMetrics:
    """
    Computes aggregate metrics from a list of per-task evaluation result dicts.
    """

    @staticmethod
    def calculate_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_tasks = len(results)
        if total_tasks == 0:
            return {
                "total_tasks": 0,
                "pass_at_1": 0.0,
                "pass_at_k": 0.0,
                "give_up_rate": 0.0,
                "avg_debug_attempts_repair": 0.0,
                "avg_latency_per_task": 0.0,
                "avg_node_latencies": {},
                "sandbox_failure_rate": 0.0,
                "by_language": {},
                "by_difficulty": {},
            }

        passed_at_1_count = sum(1 for r in results if r.get("pass_at_1", False))
        passed_at_k_count = sum(1 for r in results if r.get("pass_at_k", False))
        give_up_count = sum(1 for r in results if r.get("hit_max_debug", False))
        sandbox_error_count = sum(1 for r in results if r.get("sandbox_error", False))

        repair_attempts_list = [r["debug_attempts"] for r in results if r.get("debug_attempts", 0) > 0]
        avg_debug_repair = (sum(repair_attempts_list) / len(repair_attempts_list)) if repair_attempts_list else 0.0

        total_latencies = [r.get("total_latency", 0.0) for r in results]
        avg_latency = sum(total_latencies) / total_tasks

        # Node latencies aggregate
        node_totals: Dict[str, float] = {}
        node_counts: Dict[str, int] = {}
        for r in results:
            for node, lat in r.get("node_latencies", {}).items():
                node_totals[node] = node_totals.get(node, 0.0) + lat
                node_counts[node] = node_counts.get(node, 0) + 1

        avg_node_latencies = {
            node: round(node_totals[node] / node_counts[node], 3)
            for node in node_totals
        }

        # Sub-group aggregations
        by_language = EvalMetrics._aggregate_subgroups(results, "language")
        by_difficulty = EvalMetrics._aggregate_subgroups(results, "difficulty")

        return {
            "total_tasks": total_tasks,
            "pass_at_1": round(passed_at_1_count / total_tasks, 4),
            "pass_at_k": round(passed_at_k_count / total_tasks, 4),
            "give_up_rate": round(give_up_count / total_tasks, 4),
            "avg_debug_attempts_repair": round(avg_debug_repair, 2),
            "avg_latency_per_task": round(avg_latency, 3),
            "avg_node_latencies": avg_node_latencies,
            "sandbox_failure_rate": round(sandbox_error_count / total_tasks, 4),
            "by_language": by_language,
            "by_difficulty": by_difficulty,
        }

    @staticmethod
    def _aggregate_subgroups(results: List[Dict[str, Any]], key: str) -> Dict[str, Dict[str, Any]]:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in results:
            group_val = str(r.get(key, "unknown"))
            groups.setdefault(group_val, []).append(r)

        out = {}
        for g_name, g_items in groups.items():
            cnt = len(g_items)
            p1 = sum(1 for item in g_items if item.get("pass_at_1", False))
            pk = sum(1 for item in g_items if item.get("pass_at_k", False))
            lat = sum(item.get("total_latency", 0.0) for item in g_items) / cnt
            out[g_name] = {
                "count": cnt,
                "pass_at_1": round(p1 / cnt, 4),
                "pass_at_k": round(pk / cnt, 4),
                "avg_latency": round(lat, 3),
            }
        return out
