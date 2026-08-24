"""
CLI Entry Point for CodeAgentPro Offline Evaluation Pipeline.
Runs agent benchmarks, computes pass@1 / pass@k metrics, saves timestamped reports,
and optionally diffs against baseline runs for regression detection.
"""
import os
import sys
import yaml
import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Load .env file from backend directory or project root
load_dotenv(backend_dir / ".env")
load_dotenv()

from eval.harness import AsyncEvalHarness
from eval.metrics import EvalMetrics
from eval.report import EvalReport
from eval.compare import EvalComparator


def parse_args():
    parser = argparse.ArgumentParser(description="CodeAgentPro Agent Evaluation Pipeline")
    parser.add_argument("--provider", type=str, default="groq", help="LLM Provider (groq, gemini, ollama)")
    parser.add_argument("--model", type=str, default="openai/gpt-oss-20b", help="Model name")
    parser.add_argument("--language", type=str, default="All", help="Filter language (Python, JavaScript, C++, All)")
    parser.add_argument("--dataset", type=str, default=None, help="Path to tasks.yaml")
    parser.add_argument("--subset", type=int, default=None, help="Run only first N tasks")
    parser.add_argument("--max-debug", type=int, default=5, help="Max debug attempts per task")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for runs")
    parser.add_argument("--compare", type=str, default=None, help="Baseline JSON file path to compare against")
    return parser.parse_args()


def load_dataset(dataset_path: Path, language_filter: str, subset: int = None):
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {dataset_path}")
    with open(dataset_path, "r", encoding="utf-8") as f:
        tasks = yaml.safe_load(f)

    if not isinstance(tasks, list):
        raise ValueError("tasks.yaml must contain a top-level YAML list of task entries")

    if language_filter.lower() != "all":
        tasks = [t for t in tasks if t.get("language", "").lower() == language_filter.lower()]

    if subset and subset > 0:
        tasks = tasks[:subset]

    return tasks


def print_summary_table(summary: dict, model: str, provider: str):
    print("\n" + "=" * 65)
    print(f" CODEAGENTPRO AGENT EVALUATION BENCHMARK RESULTS")
    print("=" * 65)
    print(f" Model           : {model} ({provider})")
    print(f" Total Tasks     : {summary['total_tasks']}")
    print(f" Pass@1 Rate     : {summary['pass_at_1'] * 100:.1f}%")
    print(f" Pass@k Rate     : {summary['pass_at_k'] * 100:.1f}%")
    print(f" Give-Up Rate    : {summary['give_up_rate'] * 100:.1f}%")
    print(f" Avg Debug Iter  : {summary['avg_debug_attempts_repair']}")
    print(f" Avg Task Latency: {summary['avg_latency_per_task']}s")
    print(f" Sandbox Error   : {summary['sandbox_failure_rate'] * 100:.1f}%")
    print("-" * 65)
    print(" LANGUAGE BREAKDOWN:")
    for lang, m in summary.get("by_language", {}).items():
        print(f"   - {lang:<12}: Pass@1 = {m['pass_at_1']*100:5.1f}% | Pass@k = {m['pass_at_k']*100:5.1f}% | Latency = {m['avg_latency']}s")
    print("-" * 65)
    print(" DIFFICULTY BREAKDOWN:")
    for diff, m in summary.get("by_difficulty", {}).items():
        print(f"   - {diff:<12}: Pass@1 = {m['pass_at_1']*100:5.1f}% | Pass@k = {m['pass_at_k']*100:5.1f}% | Latency = {m['avg_latency']}s")
    print("-" * 65)
    print(" NODE LATENCY BREAKDOWN:")
    for node, lat in summary.get("avg_node_latencies", {}).items():
        print(f"   - {node:<16}: {lat:.3f}s")
    print("=" * 65 + "\n")


async def main_async():
    args = parse_args()
    eval_dir = Path(__file__).resolve().parent
    dataset_path = Path(args.dataset) if args.dataset else eval_dir / "dataset" / "tasks.yaml"
    output_dir = Path(args.output_dir) if args.output_dir else eval_dir / "runs"

    tasks = load_dataset(dataset_path, args.language, args.subset)
    print(f"[*] Loaded {len(tasks)} evaluation tasks from {dataset_path}")

    # Build model string with provider prefix if needed
    model_str = args.model
    if args.provider and ":" not in model_str:
        model_str = f"{args.provider}:{args.model}"

    harness = AsyncEvalHarness(model=model_str, max_debug_attempts=args.max_debug)
    
    print(f"[*] Starting evaluation run using model='{model_str}' across {len(tasks)} tasks...")
    task_results = await harness.run_dataset(tasks)

    summary = EvalMetrics.calculate_summary(task_results)
    print_summary_table(summary, args.model, args.provider)

    reporter = EvalReport(output_dir=str(output_dir))
    run_file = reporter.save_run(
        summary_metrics=summary,
        task_results=task_results,
        model=args.model,
        provider=args.provider,
        max_debug_attempts=args.max_debug,
        dataset_path=dataset_path,
    )
    print(f"[+] Saved evaluation run report to: {run_file}")

    if args.compare:
        comp_report, regressed = EvalComparator.compare_runs(args.compare, str(run_file))
        EvalComparator.print_comparison(comp_report)
        if regressed:
            print("[!] Quality regression detected against baseline!")
            sys.exit(1)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
