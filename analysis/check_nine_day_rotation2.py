"""
ジャグラーラボ
9の日 強い全台系ローテーション分析

目的:
    N回前の9の日に強い全台系だった島が、
    今回も同じ島で強い全台系だった割合を確認する。

対象:
    1回前
    2回前
    3回前
    4回前
    5回前

注意:
    新しい予測モデルを作るための分析ではない。
    既存の「7.69%」の元ロジックを確認するための診断用。
"""

import sqlite3
from collections import defaultdict
from pathlib import Path


# ============================================================
# パス
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


# ============================================================
# DB読み込み
# ============================================================

conn = sqlite3.connect(DB_PATH)

rows = conn.execute(
    """
    SELECT
        日付,
        島,
        判定
    FROM island_all_setting_analysis
    WHERE CAST(
        substr(日付, 9, 2)
        AS INTEGER
    ) IN (
        9,
        19,
        29
    )
    ORDER BY
        日付,
        島
    """
).fetchall()

conn.close()


# ============================================================
# 日付 → 島 → 判定
# ============================================================

days = defaultdict(dict)

for date, island, judgment in rows:

    days[date][island] = (
        str(judgment).strip()
        if judgment is not None
        else ""
    )


dates = sorted(days.keys())


# ============================================================
# 基本情報
# ============================================================

print("=" * 80)
print("9の日 強い全台系 ローテーション分析")
print("=" * 80)

print()

print(
    f"DB: {DB_PATH}"
)

print()

print(
    f"9の日: {len(dates)}回"
)

print()

print(
    dates
)


# ============================================================
# 強い全台系島
# ============================================================

def get_strong_islands(date):

    return {
        island
        for island, judgment
        in days[date].items()
        if judgment == "強い全台系候補"
    }


# ============================================================
# N回前 → 今回
# ============================================================

print()

print("=" * 80)
print(
    "N回前の強い全台系島 → 今回の同一島再投入"
)
print("=" * 80)

print()

print(
    "基準:"
)

print(
    "N回前の9の日に強い全台系だった島が、"
)

print(
    "今回も同じ島で強い全台系だった割合"
)

print()


header = (
    f"{'何回前':<12}"
    f"{'対象島数':>12}"
    f"{'今回も強い':>14}"
    f"{'再投入率':>14}"
)

print(header)

print("-" * 55)


for n in range(1, 6):

    target_island_count = 0

    same_strong_count = 0

    detail = []

    # --------------------------------------------------------
    # N回前のデータを基準にする
    # --------------------------------------------------------

    for i in range(
        n,
        len(dates)
    ):

        previous_date = dates[i - n]

        current_date = dates[i]

        previous_strong = (
            get_strong_islands(
                previous_date
            )
        )

        current_strong = (
            get_strong_islands(
                current_date
            )
        )

        # N回前に強い島がなければ
        # 分母には入れない
        if not previous_strong:
            continue

        # ----------------------------------------------------
        # 島単位でカウント
        # ----------------------------------------------------

        target_island_count += (
            len(previous_strong)
        )

        same_islands = (
            previous_strong
            & current_strong
        )

        same_strong_count += (
            len(same_islands)
        )

        # 詳細保存
        for island in sorted(
            previous_strong
        ):

            detail.append(
                {
                    "previous_date":
                        previous_date,

                    "current_date":
                        current_date,

                    "island":
                        island,

                    "same_strong":
                        island
                        in current_strong,
                }
            )

    # --------------------------------------------------------
    # 再投入率
    # --------------------------------------------------------

    if target_island_count > 0:

        rate = (
            same_strong_count
            / target_island_count
            * 100
        )

    else:

        rate = 0.0

    print(
        f"{n}回前".ljust(12)
        + f"{target_island_count:>12}"
        + f"{same_strong_count:>14}"
        + f"{rate:>13.2f}%"
    )

    # --------------------------------------------------------
    # 詳細
    # --------------------------------------------------------

    print()

    print(
        f"--- {n}回前 詳細 ---"
    )

    if not detail:

        print(
            "対象なし"
        )

    else:

        for item in detail:

            mark = (
                "◎"
                if item["same_strong"]
                else "×"
            )

            print(
                f"{mark} "
                f"{item['previous_date']} "
                f"→ "
                f"{item['current_date']} "
                f"{item['island']}"
            )

    print()


# ============================================================
# 特定の7.69%を確認
# ============================================================

print("=" * 80)
print(
    "参考：既存分析 13回中1回・7.69%"
)
print("=" * 80)

print()

print(
    "上記のN回前集計とは別に、"
)

print(
    "既存分析で確認済みの"
)

print(
    "「13回中1回・7.69%」は"
)

print(
    "Prediction Engineでは既存結果として保持する。"
)

print()

print(
    "この診断結果をもって、"
)

print(
    "7.69%を新しい定義に置き換えない。"
)

print()

print("=" * 80)
print("終了")
print("=" * 80)