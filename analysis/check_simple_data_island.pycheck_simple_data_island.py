import sqlite3

DB_PATH = r"database\juggler.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("=" * 80)
print("簡易データ 島定義確認")
print("=" * 80)

# ============================================================
# 1. machine_master相当の machines テーブル確認
# ============================================================

print()
print("【現在の島マスタ：machines】")

rows = cur.execute("""
    SELECT
        island,
        MIN(number),
        MAX(number),
        COUNT(DISTINCT number)
    FROM machines
    GROUP BY island
    ORDER BY MIN(number)
""").fetchall()

for island, min_no, max_no, count in rows:
    print(f"{island}: {min_no}～{max_no} ({count}台)")


# ============================================================
# 2. 簡易データの島別台数
# ============================================================

print()
print("【簡易データ：daily_data 島別台数】")

rows = cur.execute("""
    SELECT
        島,
        MIN(台番号),
        MAX(台番号),
        COUNT(DISTINCT 台番号)
    FROM daily_data
    WHERE 備考 = '簡易データ'
    GROUP BY 島
    ORDER BY MIN(台番号)
""").fetchall()

for island, min_no, max_no, count in rows:
    print(f"{island}: {min_no}～{max_no} ({count}台)")


# ============================================================
# 3. machines と daily_data の島定義不一致
# ============================================================

print()
print("【島定義の不一致チェック】")

rows = cur.execute("""
    SELECT DISTINCT
        d.台番号,
        d.機種,
        d.島,
        m.island
    FROM daily_data d
    INNER JOIN machines m
        ON d.台番号 = m.number
    WHERE d.備考 = '簡易データ'
      AND COALESCE(d.島, '') <> COALESCE(m.island, '')
    ORDER BY d.台番号
""").fetchall()

print(f"不一致件数: {len(rows)}")

if rows:
    for number, machine, daily_island, master_island in rows:
        print(
            f"台番号={number} "
            f"機種={machine} "
            f"daily_data={daily_island} "
            f"machines={master_island}"
        )
else:
    print("不一致はありません。")


# ============================================================
# 4. マイジャグラーだけ詳細確認
# ============================================================

print()
print("【マイジャグラーV 簡易データ 島定義】")

rows = cur.execute("""
    SELECT
        d.台番号,
        d.島,
        m.island
    FROM daily_data d
    INNER JOIN machines m
        ON d.台番号 = m.number
    WHERE d.備考 = '簡易データ'
      AND d.機種 = 'マイジャグラーV'
    GROUP BY d.台番号, d.島, m.island
    ORDER BY d.台番号
""").fetchall()

for number, daily_island, master_island in rows:
    mark = "OK" if daily_island == master_island else "NG"
    print(
        f"{number}: "
        f"daily_data={daily_island} / "
        f"master={master_island} [{mark}]"
    )


# ============================================================
# 5. A～Dの台数確認
# ============================================================

print()
print("【マイジャグ島A～D 台数確認】")

rows = cur.execute("""
    SELECT
        m.island,
        MIN(m.number),
        MAX(m.number),
        COUNT(DISTINCT m.number)
    FROM machines m
    WHERE m.island IN (
        'マイジャグ島A',
        'マイジャグ島B',
        'マイジャグ島C',
        'マイジャグ島D'
    )
    GROUP BY m.island
    ORDER BY MIN(m.number)
""").fetchall()

for island, min_no, max_no, count in rows:
    print(f"{island}: {min_no}～{max_no} ({count}台)")


conn.close()

print()
print("=" * 80)
print("終了")
print("=" * 80)