import sqlite3

DB_PATH = r"C:\Users\sphs4\OneDrive\デスクトップ\ジャグラーラボ\database\juggler.db"

conn = sqlite3.connect(DB_PATH)

print("=" * 80)
print("9の日 再計算用DBスキーマ確認")
print("=" * 80)

tables = conn.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
""").fetchall()

print("\n【テーブル一覧】")

for (table_name,) in tables:
    print(f"\n--- {table_name} ---")

    columns = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    for col in columns:
        print(
            f"  {col[1]:30s}"
            f" type={col[2]:15s}"
            f" pk={col[5]}"
        )

print("\n" + "=" * 80)
print("daily_data サンプル")
print("=" * 80)

try:
    rows = conn.execute("""
        SELECT *
        FROM daily_data
        LIMIT 3
    """).fetchall()

    columns = [
        row[1]
        for row in conn.execute(
            'PRAGMA table_info("daily_data")'
        ).fetchall()
    ]

    print("\nカラム:")
    print(columns)

    print("\nデータ:")
    for row in rows:
        print(row)

except Exception as e:
    print("daily_data 読み込みエラー:", e)

print("\n" + "=" * 80)
print("island_all_setting_analysis サンプル")
print("=" * 80)

try:
    columns = [
        row[1]
        for row in conn.execute(
            'PRAGMA table_info("island_all_setting_analysis")'
        ).fetchall()
    ]

    print("\nカラム:")
    print(columns)

    rows = conn.execute("""
        SELECT *
        FROM island_all_setting_analysis
        LIMIT 5
    """).fetchall()

    print("\nデータ:")
    for row in rows:
        print(row)

except Exception as e:
    print("island_all_setting_analysis 読み込みエラー:", e)

conn.close()

print("\n" + "=" * 80)
print("終了")
print("=" * 80)