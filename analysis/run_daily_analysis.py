import subprocess
import sys

SCRIPTS = [
    "create_machine_history_analysis.py",
    "create_machine_pattern_analysis.py",
    "create_island_trend_analysis.py",
    "create_machine_holdover_analysis.py",
    "create_store_condition_analysis.py",
    "create_alignment_analysis.py",
    "create_alignment_history_analysis.py",
    "create_alignment_history_summary.py",
    "create_prediction_score.py",
]

for script in SCRIPTS:
    print(f"===== {script} 開始 =====")

    result = subprocess.run(
        [sys.executable, f"/app/analysis/{script}"],
        check=False,
    )

    if result.returncode != 0:
        print(f"===== {script} 失敗 =====")
        raise SystemExit(result.returncode)

    print(f"===== {script} 完了 =====")

print("===== 全分析・Prediction Engine 完了 =====")
