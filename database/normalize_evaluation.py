"""
ジャグラーラボ
評価値 正規化スクリプト

目的：
・「〇」と「○」を統一する
・評価値に混入している「⚠️」を削除する
・信頼度補正カラムは変更しない

変換ルール：

〇      → ○
〇⚠️    → ○
○⚠️    → ○
△⚠️    → △
◎⚠️    → ◎

その他の評価値は変更しない。

実行前にDBバックアップを作成する。
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime


# ============================================================
# DB設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "database" / "juggler.db"

BACKUP_DIR = BASE_DIR / "database" / "backup"


# ============================================================
# バックアップ
# ============================================================

def create_backup():
    """
    DBのバックアップを作成する
    """

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_path = (
        BACKUP_DIR
        / f"juggler_before_evaluation_normalize_{timestamp}.db"
    )

    shutil.copy2(DB_PATH, backup_path)

    print("=" * 70)
    print("DBバックアップ作成")
    print("=" * 70)
    print(f"元DB      : {DB_PATH}")
    print(f"バックアップ: {backup_path}")
    print()


# ============================================================
# 現在の評価値を確認
# ============================================================

def show_before(conn):
    """
    正規化前の評価値件数を表示
    """

    print("=" * 70)
    print("正規化前 評価値")
    print("=" * 70)

    rows = conn.execute(
        """
        SELECT
            評価,
            COUNT(*) AS 件数
        FROM daily_data
        GROUP BY 評価
        ORDER BY 件数 DESC
        """
    ).fetchall()

    for row in rows:
        print(f"{str(row['評価']):<10} {row['件数']:>8}件")

    print()


# ============================================================
# 正規化
# ============================================================

def normalize_evaluation(conn):
    """
    評価値だけを正規化する。

    信頼度補正カラムは変更しない。
    """

    print("=" * 70)
    print("評価値 正規化開始")
    print("=" * 70)

    # --------------------------------------------------------
    # 〇 → ○
    # --------------------------------------------------------

    cursor = conn.execute(
        """
        UPDATE daily_data
        SET 評価 = '○'
        WHERE 評価 = '〇'
        """
    )

    print(f"〇 → ○       : {cursor.rowcount}件")

    # --------------------------------------------------------
    # 〇⚠️ → ○
    # --------------------------------------------------------

    cursor = conn.execute(
        """
        UPDATE daily_data
        SET 評価 = '○'
        WHERE 評価 = '〇⚠️'
        """
    )

    print(f"〇⚠️ → ○     : {cursor.rowcount}件")

    # --------------------------------------------------------
    # ○⚠️ → ○
    # --------------------------------------------------------

    cursor = conn.execute(
        """
        UPDATE daily_data
        SET 評価 = '○'
        WHERE 評価 = '○⚠️'
        """
    )

    print(f"○⚠️ → ○     : {cursor.rowcount}件")

    # --------------------------------------------------------
    # △⚠️ → △
    # --------------------------------------------------------

    cursor = conn.execute(
        """
        UPDATE daily_data
        SET 評価 = '△'
        WHERE 評価 = '△⚠️'
        """
    )

    print(f"△⚠️ → △     : {cursor.rowcount}件")

    # --------------------------------------------------------
    # ◎⚠️ → ◎
    # --------------------------------------------------------

    cursor = conn.execute(
        """
        UPDATE daily_data
        SET 評価 = '◎'
        WHERE 評価 = '◎⚠️'
        """
    )

    print(f"◎⚠️ → ◎     : {cursor.rowcount}件")

    print()


# ============================================================
# 正規化後確認
# ============================================================

def show_after(conn):
    """
    正規化後の評価値件数を表示
    """

    print("=" * 70)
    print("正規化後 評価値")
    print("=" * 70)

    rows = conn.execute(
        """
        SELECT
            評価,
            COUNT(*) AS 件数
        FROM daily_data
        GROUP BY 評価
        ORDER BY 件数 DESC
        """
    ).fetchall()

    for row in rows:
        print(f"{str(row['評価']):<10} {row['件数']:>8}件")

    print()


# ============================================================
# 信頼度補正カラム確認
# ============================================================

def show_confidence(conn):
    """
    信頼度補正カラムが変更されていないことを確認する。
    """

    print("=" * 70)
    print("信頼度補正")
    print("=" * 70)

    rows = conn.execute(
        """
        SELECT
            信頼度補正,
            COUNT(*) AS 件数
        FROM daily_data
        GROUP BY 信頼度補正
        ORDER BY 件数 DESC
        """
    ).fetchall()

    for row in rows:
        print(f"{str(row['信頼度補正']):<10} {row['件数']:>8}件")

    print()


# ============================================================
# メイン
# ============================================================

def main():

    if not DB_PATH.exists():
        print("DBが見つかりません。")
        print(f"DB: {DB_PATH}")
        return

    print("=" * 70)
    print("ジャグラーラボ")
    print("評価値 正規化")
    print("=" * 70)
    print(f"DB: {DB_PATH}")
    print()

    # --------------------------------------------------------
    # バックアップ
    # --------------------------------------------------------

    create_backup()

    # --------------------------------------------------------
    # DB接続
    # --------------------------------------------------------

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:

        # ----------------------------------------------------
        # 正規化前確認
        # ----------------------------------------------------

        show_before(conn)

        # ----------------------------------------------------
        # 正規化
        # ----------------------------------------------------

        normalize_evaluation(conn)

        # ----------------------------------------------------
        # コミット
        # ----------------------------------------------------

        conn.commit()

        print("=" * 70)
        print("正規化をコミットしました。")
        print("=" * 70)
        print()

        # ----------------------------------------------------
        # 正規化後確認
        # ----------------------------------------------------

        show_after(conn)

        # ----------------------------------------------------
        # 信頼度補正確認
        # ----------------------------------------------------

        show_confidence(conn)

        # ----------------------------------------------------
        # 残存する⚠️確認
        # ----------------------------------------------------

        row = conn.execute(
            """
            SELECT COUNT(*) AS 件数
            FROM daily_data
            WHERE 評価 LIKE '%⚠️%'
            """
        ).fetchone()

        print("=" * 70)
        print("評価値に残っている⚠️")
        print("=" * 70)
        print(f"{row['件数']}件")
        print()

        if row["件数"] == 0:
            print("OK：評価値から⚠️が完全に除去されています。")
        else:
            print("注意：評価値に⚠️が残っています。")

        print()

    except Exception as e:

        conn.rollback()

        print("=" * 70)
        print("エラーが発生しました")
        print("=" * 70)
        print(e)
        print()
        print("DB変更はロールバックしました。")

    finally:

        conn.close()


if __name__ == "__main__":
    main()