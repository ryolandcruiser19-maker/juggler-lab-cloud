import sqlite3
from pathlib import Path


# ==========================================
# DB設定
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "juggler.db"


# ==========================================
# 島名の正規化
# ==========================================

NAME_MAP = {
    "ガール島": "ガール島",

    "ゴー島①": "ゴー島①",
    "ゴー島②": "ゴー島②",

    "マイジャグ島A": "マイジャグ島A",
    "マイジャグ島B": "マイジャグ島B",
    "マイジャグ島C": "マイジャグ島C",
    "マイジャグ島D": "マイジャグ島D",

    "ミラクル島": "ミラクル島",
    "ミスタ島": "ミスタ島",
    "ハッピ島": "ハッピ島",

    "ファン島①": "ファン島①",
    "ファン島②": "ファン島②",
}


# 絵文字付き名称を
# 「Unicodeコードポイント」で指定
#
# 実際の文字をコード内に書かないため、
# Python 3.14 の対話モードでも問題が起きにくい。

NAME_MAP.update({
    "\U0001f7e3ガール島": "ガール島",

    "\U0001f534ゴー島①": "ゴー島①",
    "\U0001f534ゴー島②": "ゴー島②",

    "\U0001f534マイジャグ島A": "マイジャグ島A",
    "\U0001f534マイジャグ島B": "マイジャグ島B",

    "\U0001f535ミラクル島": "ミラクル島",
    "\U0001f7e0ミスタ島": "ミスタ島",
    "\U0001f7e1ハッピ島": "ハッピ島",

    "\U0001f7e2ファン島①": "ファン島①",
    "\U0001f7e2ファン島②": "ファン島②",
})


# ==========================================
# 対象テーブル
# ==========================================

TABLES = [
    "island_all_setting_analysis",
]


# ==========================================
# DB接続
# ==========================================

print("DB:")
print(DB_PATH)

if not DB_PATH.exists():
    print("DBが見つかりません。")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()


# ==========================================
# 更新
# ==========================================

total_updated = 0

for table in TABLES:

    print()
    print("=" * 50)
    print(f"テーブル: {table}")
    print("=" * 50)

    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table,)
    )

    if cur.fetchone() is None:
        print("テーブルが存在しません。")
        continue

    for old_name, new_name in NAME_MAP.items():

        cur.execute(
            f'''
            SELECT COUNT(*)
            FROM "{table}"
            WHERE 島 = ?
            ''',
            (old_name,)
        )

        count = cur.fetchone()[0]

        if count == 0:
            continue

        cur.execute(
            f'''
            UPDATE "{table}"
            SET 島 = ?
            WHERE 島 = ?
            ''',
            (new_name, old_name)
        )

        print(
            f"{old_name} -> {new_name} : {count}件"
        )

        total_updated += count


# ==========================================
# 保存
# ==========================================

conn.commit()


# ==========================================
# 正規化後の確認
# ==========================================

print()
print("=" * 50)
print("正規化後の島名一覧")
print("=" * 50)

cur.execute(
    """
    SELECT DISTINCT 島
    FROM island_all_setting_analysis
    ORDER BY 島
    """
)

names = cur.fetchall()

for row in names:
    print(repr(row[0]))


print()
print("=" * 50)
print(f"更新件数: {total_updated}")
print("島名の正規化が完了しました。")
print("=" * 50)


conn.close()