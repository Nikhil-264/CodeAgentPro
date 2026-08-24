"""
Report Generator for CodeAgentPro Eval Pipeline.
Writes evaluation run results to timestamped JSON files under backend/eval/runs/.
"""
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class EvalReport:
    """
    Saves evaluation runs and manages run log artifacts.
    """

    def __init__(self, output_dir: str = "eval/runs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_git_commit_hash() -> str:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return "unknown"

    def save_run(
        self,
        summary_metrics: Dict[str, Any],
        task_results: List[Dict[str, Any]],
        model: str,
        provider: str,
        max_debug_attempts: int,
        dataset_path: str,
    ) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_slug = model.replace(":", "_").replace("/", "_")
        filename = f"run_{timestamp}_{model_slug}.json"
        filepath = self.output_dir / filename

        report_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "git_commit": self.get_git_commit_hash(),
                "model": model,
                "provider": provider,
                "max_debug_attempts": max_debug_attempts,
                "dataset_path": str(dataset_path),
            },
            "summary": summary_metrics,
            "tasks": task_results,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        return filepath
