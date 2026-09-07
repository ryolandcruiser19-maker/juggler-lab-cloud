import sqlite3
from pathlib import Path
import pandas as pd


# ============================================================
# DB設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = Path("/app/data/juggler.db") if __import__("os").getenv("CLOUD_MODE") == "1" else BASE_DIR / "database" / "juggler.db"


# ============================================================
# 現在の島境界を machines テーブルから取得
# ============================================================

def load_machine_master(conn):

    machines = pd.read_sql(
        """
        SELECT
            number,
            island
        FROM machines
        ORDER BY number
        """,
        conn
    )

    if machines.empty:
        raise RuntimeError(
            "machines テーブルに台情報がありません。"
        )

    # 台番号の重複チェック
    duplicated = (
        machines[
            machines["number"].duplicated(keep=False)
        ]
        .sort_values("number")
    )

    if not duplicated.empty:
        print("警告: machines テーブルに台番号重複があります。")
        print(duplicated.to_string(index=False))
        raise RuntimeError(
            "machines.number に重複があります。"
        )

    print(
        "machines テーブルから現在の島定義を取得:",
        len(machines),
        "台"
    )

    return machines


# ============================================================
# 1日分の並び分析
# ============================================================

def analyze_date(
    conn,
    date,
    machine_master
):

    # --------------------------------------------------------
    # 当日のデータ取得
    #
    # 島は daily_data から取得しない。
    # machines テーブルの現在の島定義を使用する。
    # --------------------------------------------------------

    df = pd.read_sql(
        """
        SELECT
            d.日付,
            d.台番号,
            d.G数,
            d.合成確率,
            d.評価,
            m.island
        FROM daily_data AS d
        INNER JOIN machines AS m
            ON d.台番号 = m.number
        WHERE d.日付 = ?
        ORDER BY
            m.island,
            d.台番号
        """,
        conn,
        params=[date]
    )

    if df.empty:
        return []

    results = []

    # --------------------------------------------------------
    # 現在の machines テーブルの島定義でグループ化
    # --------------------------------------------------------

    for island, group in df.groupby(
        "island",
        sort=False
    ):

        group = (
            group
            .sort_values("台番号")
            .reset_index(drop=True)
        )

        # ----------------------------------------------------
        # 3台並びをチェック
        # ----------------------------------------------------

        for i in range(len(group) - 2):

            window = group.iloc[i:i + 3]

            nums = (
                window["台番号"]
                .astype(int)
                .tolist()
            )

            # 3台が完全な連番であることを確認
            if nums[1] != nums[0] + 1:
                continue

            if nums[2] != nums[1] + 1:
                continue

            # ------------------------------------------------
            # 評価数
            # ------------------------------------------------

            star_count = (
                window["評価"]
                .eq("◎")
                .sum()
            )

            circle_count = (
                window["評価"]
                .eq("○")
                .sum()
            )

            # ◎2台以上のみ登録
            if star_count < 2:
                continue

            # ------------------------------------------------
            # 並びスコア
            # ------------------------------------------------

            score = (
                star_count * 10
                +
                circle_count * 5
            )

            # ------------------------------------------------
            # 判定
            # ------------------------------------------------

            if star_count == 3:
                judge = "強い並び"
            else:
                judge = "並び候補"

            # ------------------------------------------------
            # 平均G数
            # ------------------------------------------------

            avg_games = (
                window["G数"]
                .dropna()
                .mean()
            )

            if pd.notna(avg_games):
                avg_games = round(
                    float(avg_games),
                    1
                )
            else:
                avg_games = None

            # ------------------------------------------------
            # 平均合成確率
            # ------------------------------------------------

            avg_probability = (
                window["合成確率"]
                .dropna()
                .mean()
            )

            if pd.notna(avg_probability):
                avg_probability = round(
                    float(avg_probability),
                    1
                )
            else:
                avg_probability = None

            # ------------------------------------------------
            # 保存
            # ------------------------------------------------

            results.append(
                (
                    str(date),
                    island,
                    nums[0],
                    nums[2],
                    3,
                    int(star_count),
                    int(circle_count),
                    avg_games,
                    avg_probability,
                    int(score),
                    judge
                )
            )

    return results


# ============================================================
# 全期間の履歴分析
# ============================================================

def create_alignment_history_analysis():

    print("=" * 60)
    print("alignment_history 再構築開始")
    print("=" * 60)

    print()
    print("DB:", DB_PATH)

    conn = sqlite3.connect(DB_PATH)

    try:

        # ----------------------------------------------------
        # 現在の島定義を取得
        # ----------------------------------------------------

        machine_master = load_machine_master(conn)

        # ----------------------------------------------------
        # 対象日取得
        # ----------------------------------------------------

        dates = pd.read_sql(
            """
            SELECT DISTINCT
                日付
            FROM daily_data
            WHERE 日付 IS NOT NULL
            ORDER BY 日付
            """,
            conn
        )

        print(
            "対象日数:",
            len(dates)
        )

        if dates.empty:

            print(
                "daily_data に対象日がありません。"
            )

            return

        # ----------------------------------------------------
        # 全期間分析
        # ----------------------------------------------------

        all_results = []

        for index, row in dates.iterrows():

            date = row["日付"]

            results = analyze_date(
                conn,
                date,
                machine_master
            )

            all_results.extend(results)

            # 進捗表示
            if (
                (index + 1) % 30 == 0
                or
                index == 0
                or
                index + 1 == len(dates)
            ):

                print(
                    f"{index + 1}/{len(dates)} 日完了:",
                    date,
                    "→",
                    len(results),
                    "件"
                )

        print()
        print(
            "再構築対象件数:",
            len(all_results)
        )

        # ----------------------------------------------------
        # 既存履歴を削除
        # ----------------------------------------------------

        cursor = conn.cursor()

        print()
        print(
            "既存 alignment_history を削除します..."
        )

        cursor.execute(
            """
            DELETE FROM alignment_history
            """
        )

        deleted_count = cursor.rowcount

        print(
            "既存削除件数:",
            deleted_count
        )

        # ----------------------------------------------------
        # 新しい履歴を登録
        # ----------------------------------------------------

        if all_results:

            cursor.executemany(
                """
                INSERT INTO alignment_history
                (
                    日付,
                    島,
                    開始台番号,
                    終了台番号,
                    台数,
                    ◎台数,
                    ○台数,
                    平均G数,
                    平均合成確率,
                    並びスコア,
                    判定
                )
                VALUES
                (
                    ?,?,?,?,?,?,?,?,?,?,?
                )
                """,
                all_results
            )

        conn.commit()

        # ----------------------------------------------------
        # 結果確認
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("alignment_history 再構築完了")
        print("=" * 60)

        print(
            "登録件数:",
            len(all_results)
        )

        # ----------------------------------------------------
        # 島別件数
        # ----------------------------------------------------

        check = pd.read_sql(
            """
            SELECT
                島,
                COUNT(*) AS 件数
            FROM alignment_history
            GROUP BY 島
            ORDER BY 島
            """,
            conn
        )

        print()
        print("=== 島別登録件数 ===")

        if not check.empty:
            print(
                check.to_string(index=False)
            )

        # ----------------------------------------------------
        # 古い絵文字島名が残っていないか確認
        # ----------------------------------------------------

        old_islands = pd.read_sql(
            """
            SELECT DISTINCT 島
            FROM alignment_history
            WHERE 島 LIKE '🔴%'
               OR 島 LIKE '🔵%'
               OR 島 LIKE '🟠%'
               OR 島 LIKE '🟡%'
               OR 島 LIKE '🟢%'
               OR 島 LIKE '🟣%'
            ORDER BY 島
            """,
            conn
        )

        print()
        print("=== 旧島名チェック ===")

        if old_islands.empty:

            print(
                "旧島名はありません。OK"
            )

        else:

            print(
                "警告: 旧島名が残っています。"
            )

            print(
                old_islands.to_string(index=False)
            )

    finally:

        conn.close()


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":

    create_alignment_history_analysis()
