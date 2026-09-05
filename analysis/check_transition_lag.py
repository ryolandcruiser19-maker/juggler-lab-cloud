import pandas as pd

CSV_PATH = (
    "analysis/backtest_output/"
    "nine_day_transition_pairs.csv"
)

df = pd.read_csv(CSV_PATH)

dates = sorted(
    df["current_date"].unique()
)

print("=" * 80)
print("9の日 強い全台系 ローテーション分析")
print("=" * 80)

print()

print(
    "基準:"
)
print(
    "N回前の9の日に強い全台系だった島が、"
    "今回も同じ島で強い全台系だった割合"
)

print()

print(
    f"対象9の日: {len(dates)}回"
)

print()

print(
    f"{'何回前':<10}"
    f"{'対象回数':>12}"
    f"{'今回も強い':>14}"
    f"{'再投入率':>14}"
)

print("-" * 55)


for lag in range(1, 6):

    total_count = 0
    success_count = 0

    for i in range(
        lag,
        len(dates)
    ):

        previous_date = dates[i - lag]
        current_date = dates[i]

        pairs = df[
            (df["previous_date"] == previous_date)
            &
            (df["current_date"] == current_date)
            &
            (df["from_was_strong"] == 1)
            &
            (
                df["from_island"]
                ==
                df["to_island"]
            )
        ]

        total_count += len(pairs)

        success_count += int(
            (
                pairs["to_is_strong"] == 1
            ).sum()
        )

    if total_count > 0:

        rate = (
            success_count
            / total_count
            * 100
        )

    else:

        rate = 0.0

    print(
        f"{lag}回前"
        f"{total_count:>12}"
        f"{success_count:>14}"
        f"{rate:>13.2f}%"
    )


print()

print("=" * 80)
print("終了")
print("=" * 80)