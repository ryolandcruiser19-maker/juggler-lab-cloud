import sqlite3
from collections import defaultdict

DB_PATH = r"C:\Users\sphs4\OneDrive\デスクトップ\ジャグラーラボ\database\juggler.db"

# ============================================================
# 判定基準
# ============================================================
# 今回は「△以上率」を基準として再計算する。
#
# 全台系候補 : △以上率 50%以上
# 強い全台系 : △以上率 70%以上
#
# ※必要なら後で既存Prediction Engineの正式基準に合わせて変更する。
CANDIDATE_THRESHOLD = 50.0
STRONG_THRESHOLD = 70.0


# ============================================================
# DB接続
# ============================================================
conn = sqlite3.connect(DB_PATH)


# ============================================================
# 1. 現在の島構成を取得
# ============================================================
print("=" * 80)
print("9の日 全台系再計算＋ローテーション分析")
print("=" * 80)

print()
print("現在の島構成を machines テーブルから取得")


island_machine_rows = conn.execute("""
    SELECT island, COUNT(*)
    FROM machines
    GROUP BY island
    ORDER BY island
""").fetchall()

current_island_size = {
    island: count
    for island, count in island_machine_rows
}

print()
print("【現在の島台数】")

for island, count in current_island_size.items():
    print(f"{island:20s} : {count:3d}台")


# ============================================================
# 2. 9の日一覧
# ============================================================
rows = conn.execute("""
    SELECT DISTINCT 日付
    FROM daily_data
    WHERE CAST(substr(日付, 9, 2) AS INTEGER) IN (9, 19, 29)
    ORDER BY 日付
""").fetchall()

nine_days = [r[0] for r in rows]

print()
print("=" * 80)
print("9の日")
print("=" * 80)

print()
print(f"9の日: {len(nine_days)}回")
print(nine_days)


# ============================================================
# 3. 9の日の島別「△以上台数」を取得
# ============================================================
#
# daily_dataでは古い簡易データの場合、
# △以上の台しか存在しない。
#
# したがって、
#
#   島に存在するdaily_data行数
#
# を「△以上台数」とする。
#
# 同じ日・同じ台が重複していた場合に備えてDISTINCT台番号。
# ============================================================

rows = conn.execute("""
    SELECT
        日付,
        島,
        COUNT(DISTINCT 台番号) AS delta_over_count
    FROM daily_data
    WHERE CAST(substr(日付, 9, 2) AS INTEGER) IN (9, 19, 29)
    GROUP BY 日付, 島
    ORDER BY 日付, 島
""").fetchall()


delta_over = defaultdict(dict)

for date, island, count in rows:
    delta_over[date][island] = count


# ============================================================
# 4. 島別再計算
# ============================================================

recalculated = defaultdict(dict)

for date in nine_days:

    for island, total_machines in current_island_size.items():

        delta_count = delta_over[date].get(island, 0)

        if total_machines <= 0:
            continue

        rate = delta_count / total_machines * 100.0

        if rate >= STRONG_THRESHOLD:
            judgement = "強い全台系"
        elif rate >= CANDIDATE_THRESHOLD:
            judgement = "全台系候補"
        else:
            judgement = ""

        recalculated[date][island] = {
            "total": total_machines,
            "delta_count": delta_count,
            "rate": rate,
            "judgement": judgement,
        }


# ============================================================
# 5. 再計算結果を表示
# ============================================================

print()
print("=" * 80)
print("9の日 島別再計算結果")
print("=" * 80)

for date in nine_days:

    print()
    print(f"【{date}】")

    for island in current_island_size:

        data = recalculated[date].get(island)

        if data is None:
            continue

        print(
            f"{island:20s} "
            f"分母={data['total']:2d} "
            f"△以上={data['delta_count']:2d} "
            f"△以上率={data['rate']:6.2f}% "
            f"{data['judgement']}"
        )


# ============================================================
# 6. 強い全台系ローテーション分析
# ============================================================

print()
print("=" * 80)
print("N回前の強い全台系島 → 今回の同一島再投入")
print("=" * 80)

print()
print("基準:")
print("N回前の9の日に「強い全台系」だった島が、")
print("今回も同じ島で「強い全台系」だった割合")

print()
print(f"全台系候補基準 : △以上率 {CANDIDATE_THRESHOLD:.1f}%以上")
print(f"強い全台系基準 : △以上率 {STRONG_THRESHOLD:.1f}%以上")


# ============================================================
# N回前分析
# ============================================================

for n in range(1, 6):

    target_count = 0
    repeat_count = 0

    details = []

    for i in range(n, len(nine_days)):

        previous_date = nine_days[i - n]
        current_date = nine_days[i]

        previous_data = recalculated[previous_date]
        current_data = recalculated[current_date]

        for island in current_island_size:

            prev = previous_data.get(island)
            curr = current_data.get(island)

            if prev is None or curr is None:
                continue

            if prev["judgement"] == "強い全台系":

                target_count += 1

                if curr["judgement"] == "強い全台系":
                    repeat_count += 1

                    details.append(
                        (
                            "◎",
                            previous_date,
                            current_date,
                            island,
                            prev["rate"],
                            curr["rate"],
                        )
                    )
                else:

                    details.append(
                        (
                            "×",
                            previous_date,
                            current_date,
                            island,
                            prev["rate"],
                            curr["rate"],
                        )
                    )

    if target_count > 0:
        repeat_rate = repeat_count / target_count * 100.0
    else:
        repeat_rate = 0.0

    print()
    print(
        f"{n}回前"
        f"{target_count:20d}"
        f"{repeat_count:15d}"
        f"{repeat_rate:13.2f}%"
    )

    print()
    print(f"--- {n}回前 詳細 ---")

    for (
        result,
        previous_date,
        current_date,
        island,
        previous_rate,
        current_rate,
    ) in details:

        print(
            f"{result} "
            f"{previous_date} → {current_date} "
            f"{island:20s} "
            f"前={previous_rate:6.2f}% "
            f"今回={current_rate:6.2f}%"
        )


# ============================================================
# 7. 島別の再計算後統計
# ============================================================

print()
print("=" * 80)
print("再計算後 島別9の日統計")
print("=" * 80)

for island in current_island_size:

    candidate_count = 0
    strong_count = 0
    rates = []

    for date in nine_days:

        data = recalculated[date].get(island)

        if data is None:
            continue

        rates.append(data["rate"])

        if data["rate"] >= CANDIDATE_THRESHOLD:
            candidate_count += 1

        if data["rate"] >= STRONG_THRESHOLD:
            strong_count += 1

    if not rates:
        continue

    candidate_rate = candidate_count / len(rates) * 100.0
    strong_rate = strong_count / len(rates) * 100.0
    avg_rate = sum(rates) / len(rates)

    print()
    print(f"{island}")

    print(f"  9の日実績回数       : {len(rates)}")
    print(f"  全台系候補回数      : {candidate_count}")
    print(f"  強い全台系回数      : {strong_count}")
    print(f"  全台系候補率        : {candidate_rate:.2f}%")
    print(f"  強い全台系率        : {strong_rate:.2f}%")
    print(f"  平均△以上率         : {avg_rate:.2f}%")


# ============================================================
# 8. 終了
# ============================================================

conn.close()

print()
print("=" * 80)
print("終了")
print("=" * 80)