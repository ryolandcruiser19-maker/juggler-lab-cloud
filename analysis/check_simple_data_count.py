import sqlite3

DB_PATH = r"database\juggler.db"
TARGET_DATE = "2025-12-12"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("=" * 90)
print(f"簡易データ 集計ロジック診断")
print(f"対象日: {TARGET_DATE}")
print("=" * 90)

# ============================================================
# 1. 島ごとのマスタ台数
# ============================================================

print()
print("【1. 現在の島マスタ台数】")

master_rows = cur.execute("""
    SELECT
        island,
        COUNT(DISTINCT number)
    FROM machines
    GROUP BY island
    ORDER BY MIN(number)
""").fetchall()

master_counts = {island: count for island, count in master_rows}

for island, count in master_rows:
    print(f"{island}: {count}台")


# ============================================================
# 2. 2025-12-12 daily_data の島別集計
# ============================================================

print()
print("【2. 2025-12-12 daily_data 島別集計】")

query = """
SELECT
    島,
    COUNT(*) AS 行数,
    COUNT(DISTINCT 台番号) AS ユニーク台数,
    COUNT(CASE WHEN 評価 IN ('◎', '○', '△') THEN 1 END) AS △以上行数,
    COUNT(DISTINCT CASE
        WHEN 評価 IN ('◎', '○', '△') THEN 台番号
    END) AS △以上ユニーク台数,
    COUNT(DISTINCT CASE
        WHEN 評価 = '◎' THEN 台番号
    END) AS ◎ユニーク台数,
    COUNT(DISTINCT CASE
        WHEN 評価 = '○' THEN 台番号
    END) AS ○ユニーク台数,
    COUNT(DISTINCT CASE
        WHEN 評価 = '△' THEN 台番号
    END) AS △ユニーク台数
FROM daily_data
WHERE 日付 = ?
  AND 備考 = '簡易データ'
GROUP BY 島
ORDER BY MIN(台番号)
"""

rows = cur.execute(query, (TARGET_DATE,)).fetchall()

print()
print(
    f"{'島':<12}"
    f"{'マスタ':>7}"
    f"{'行数':>7}"
    f"{'ユニーク':>9}"
    f"{'△以上行':>9}"
    f"{'△以上uniq':>11}"
    f"{'◎uniq':>8}"
    f"{'○uniq':>8}"
    f"{'△uniq':>8}"
    f"{'△以上率':>10}"
)

print("-" * 90)

for (
    island,
    row_count,
    unique_count,
    high_row_count,
    high_unique_count,
    bb_count,
    circle_count,
    triangle_count,
) in rows:

    master_count = master_counts.get(island, 0)

    if master_count:
        rate = high_unique_count / master_count * 100
    else:
        rate = 0

    print(
        f"{island:<12}"
        f"{master_count:>7}"
        f"{row_count:>7}"
        f"{unique_count:>9}"
        f"{high_row_count:>9}"
        f"{high_unique_count:>11}"
        f"{bb_count:>8}"
        f"{circle_count:>8}"
        f"{triangle_count:>8}"
        f"{rate:>9.2f}%"
    )


# ============================================================
# 3. 重複している台番号を確認
# ============================================================

print()
print("【3. 同一日・同一島・同一台番号の重複】")

duplicate_rows = cur.execute("""
    SELECT
        島,
        台番号,
        COUNT(*) AS 件数,
        GROUP_CONCAT(評価, ',') AS 評価一覧
    FROM daily_data
    WHERE 日付 = ?
      AND 備考 = '簡易データ'
    GROUP BY 島, 台番号
    HAVING COUNT(*) > 1
    ORDER BY 島, 台番号
""", (TARGET_DATE,)).fetchall()

print(f"重複台数: {len(duplicate_rows)}")

if duplicate_rows:
    for island, number, count, evaluations in duplicate_rows:
        print(
            f"{island}: 台番号={number}, "
            f"{count}行, 評価={evaluations}"
        )
else:
    print("重複はありません。")


# ============================================================
# 4. マイジャグラーA～Dを詳細確認
# ============================================================

print()
print("【4. マイジャグラーA～D 詳細】")

myislands = [
    "マイジャグ島A",
    "マイジャグ島B",
    "マイジャグ島C",
    "マイジャグ島D",
]

for island in myislands:

    print()
    print(f"--- {island} ---")

    rows = cur.execute("""
        SELECT
            台番号,
            評価,
            COUNT(*) AS 件数
        FROM daily_data
        WHERE 日付 = ?
          AND 備考 = '簡易データ'
          AND 島 = ?
        GROUP BY 台番号, 評価
        ORDER BY 台番号
    """, (TARGET_DATE, island)).fetchall()

    if not rows:
        print("データなし")
        continue

    for number, evaluation, count in rows:
        print(
            f"{number}: 評価={evaluation}, "
            f"{count}行"
        )


# ============================================================
# 5. 島別△以上率の妥当性チェック
# ============================================================

print()
print("【5. △以上率チェック】")

for (
    island,
    row_count,
    unique_count,
    high_row_count,
    high_unique_count,
    bb_count,
    circle_count,
    triangle_count,
) in rows if False else []:
    pass

# 再取得
check_rows = cur.execute("""
SELECT
    島,
    COUNT(DISTINCT CASE
        WHEN 評価 IN ('◎', '○', '△') THEN 台番号
    END) AS high_count
FROM daily_data
WHERE 日付 = ?
  AND 備考 = '簡易データ'
GROUP BY 島
ORDER BY MIN(台番号)
""", (TARGET_DATE,)).fetchall()

for island, high_count in check_rows:

    master_count = master_counts.get(island, 0)

    if master_count:
        rate = high_count / master_count * 100
    else:
        rate = 0

    status = "OK" if rate <= 100 else "NG"

    print(
        f"{island}: "
        f"{high_count}/{master_count} = "
        f"{rate:.2f}% [{status}]"
    )


conn.close()

print()
print("=" * 90)
print("終了")
print("=" * 90)