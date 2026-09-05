
"""
ジャグラーラボ
Prediction Engine

9の日 島予測エンジン

対象:
    9日
    19日
    29日

基本方針:
    ・9の日と通常日を分離
    ・9の日は「島」を予測単位とする
    ・過去の island_all_setting_analysis を利用
    ・既存の「判定」をそのまま利用
    ・未来データは使用しない
    ・9の日遷移分析は既存の
      nine_day_transition_pairs.csv を利用
    ・既存分析で確認済みの
      「13回中1回・7.69%」を再現する
    ・予測理由を出力する

既存分析の全台系候補:
    強い全台系候補
    弱い全台系候補
    全台系候補
"""

from __future__ import annotations

import csv
import sqlite3

from datetime import datetime
from pathlib import Path


# ============================================================
# パス設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)

NINE_DAY_TRANSITION_PATH = (
    BASE_DIR
    / "analysis"
    / "backtest_output"
    / "nine_day_transition_pairs.csv"
)


# ============================================================
# Prediction Engine
# ============================================================

class PredictionEngine:

    """
    ジャグラーラボ Prediction Engine
    """

    # ========================================================
    # 初期化
    # ========================================================

    def __init__(
        self,
        db_path=None
    ):

        if db_path is None:

            self.db_path = DB_PATH

        else:

            self.db_path = Path(
                db_path
            )

    # ========================================================
    # DB接続
    # ========================================================

    def _connect(self):

        if not self.db_path.exists():

            raise FileNotFoundError(
                f"DBが見つかりません: {self.db_path}"
            )

        return sqlite3.connect(
            self.db_path
        )

    # ========================================================
    # 共通ユーティリティ
    # ========================================================

    @staticmethod
    def _safe_float(
        value,
        default=0.0
    ):

        try:

            if value is None:

                return default

            return float(value)

        except (
            TypeError,
            ValueError
        ):

            return default

    @staticmethod
    def _safe_int(
        value,
        default=0
    ):

        try:

            if value is None:

                return default

            return int(value)

        except (
            TypeError,
            ValueError
        ):

            return default

    @staticmethod
    def _parse_date(
        value
    ):

        if value is None:

            return None

        try:

            return datetime.strptime(
                str(value),
                "%Y-%m-%d"
            )

        except ValueError:

            return None

    # ========================================================
    # 営業日タイプ
    # ========================================================

    @staticmethod
    def is_nine_day(
        target_date
    ):
        """
        9日・19日・29日を9の日と判定する。
        """

        if isinstance(
            target_date,
            datetime
        ):

            day = target_date.day

        else:

            parsed = (
                PredictionEngine
                ._parse_date(
                    target_date
                )
            )

            if parsed is None:

                raise ValueError(
                    "target_date は "
                    "YYYY-MM-DD形式で指定してください"
                )

            day = parsed.day

        return day in (
            9,
            19,
            29
        )

    @staticmethod
    def get_day_type(
        target_date
    ):
        """
        営業日タイプを返す。
        """

        if PredictionEngine.is_nine_day(
            target_date
        ):

            return "9の日"

        return "通常日"

    # ========================================================
    # 島一覧
    # ========================================================

    def get_islands(
        self
    ):

        conn = self._connect()

        try:

            rows = conn.execute(
                """
                SELECT DISTINCT
                    island
                FROM machines
                WHERE island IS NOT NULL
                  AND island != ''
                ORDER BY island
                """
            ).fetchall()

            return [
                row[0]
                for row in rows
            ]

        finally:

            conn.close()

    # ========================================================
    # 9の日履歴取得
    # ========================================================

    def get_nine_day_history(
        self,
        target_date
    ):
        """
        予測対象日より前の9の日について
        island_all_setting_analysisを取得。

        未来データは使用しない。
        """

        target_date = str(
            target_date
        )

        conn = self._connect()

        try:

            rows = conn.execute(
                """
                SELECT
                    日付,
                    島,
                    対象台数,
                    △以上台数,
                    △以上率,
                    ◎台数,
                    ○台数,
                    △台数,
                    ×台数,
                    ◎率,
                    ○率,
                    △率,
                    ×率,
                    平均G数,
                    平均合成確率,
                    信頼度高台数,
                    信頼度率,
                    全台系スコア,
                    結果強度,
                    判定,
                    最終更新日
                FROM island_all_setting_analysis
                WHERE 日付 < ?
                  AND CAST(
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
                """,
                (
                    target_date,
                )
            ).fetchall()

            columns = [
                "日付",
                "島",
                "対象台数",
                "△以上台数",
                "△以上率",
                "◎台数",
                "○台数",
                "△台数",
                "×台数",
                "◎率",
                "○率",
                "△率",
                "×率",
                "平均G数",
                "平均合成確率",
                "信頼度高台数",
                "信頼度率",
                "全台系スコア",
                "結果強度",
                "判定",
                "最終更新日",
            ]

            return [
                dict(
                    zip(
                        columns,
                        row
                    )
                )
                for row in rows
            ]

        finally:

            conn.close()

    # ========================================================
    # 全台系候補判定
    # ========================================================

    @staticmethod
    def _is_all_setting_candidate(
        row
    ):
        """
        既存分析の「判定」を使用。

        全台系候補:
            強い全台系候補
            弱い全台系候補
            全台系候補

        空欄:
            対象外
        """

        judgment = str(
            row.get(
                "判定",
                ""
            )
        ).strip()

        return judgment in (
            "強い全台系候補",
            "弱い全台系候補",
            "全台系候補",
        )

    # ========================================================
    # 強い全台系判定
    # ========================================================

    @staticmethod
    def _is_strong_all_setting(
        row
    ):
        """
        強い全台系候補か判定。
        """

        judgment = str(
            row.get(
                "判定",
                ""
            )
        ).strip()

        return (
            judgment
            == "強い全台系候補"
        )

    # ========================================================
    # 9の日 島別実績
    # ========================================================

    def get_nine_day_island_summary(
        self,
        target_date
    ):
        """
        9の日について、
        島ごとの過去実績を集計。
        """

        history = (
            self.get_nine_day_history(
                target_date
            )
        )

        if not history:

            return []

        island_records = {}

        for row in history:

            island = row["島"]

            if island not in island_records:

                island_records[
                    island
                ] = []

            island_records[
                island
            ].append(row)

        results = []

        for island, records in (
            island_records.items()
        ):

            records.sort(
                key=lambda x: x["日付"]
            )

            total_days = len(
                records
            )

            # ------------------------------------------------
            # 全台系候補回数
            # ------------------------------------------------

            candidate_count = sum(
                1
                for row in records
                if self._is_all_setting_candidate(
                    row
                )
            )

            # ------------------------------------------------
            # 強い全台系候補回数
            # ------------------------------------------------

            strong_count = sum(
                1
                for row in records
                if self._is_strong_all_setting(
                    row
                )
            )

            # ------------------------------------------------
            # 弱い全台系候補回数
            # ------------------------------------------------

            weak_count = sum(
                1
                for row in records
                if str(
                    row.get(
                        "判定",
                        ""
                    )
                ).strip()
                == "弱い全台系候補"
            )

            # ------------------------------------------------
            # その他全台系候補
            # ------------------------------------------------

            normal_candidate_count = sum(
                1
                for row in records
                if str(
                    row.get(
                        "判定",
                        ""
                    )
                ).strip()
                == "全台系候補"
            )

            # ------------------------------------------------
            # 候補率
            # ------------------------------------------------

            candidate_rate = 0.0

            if total_days > 0:

                candidate_rate = (
                    candidate_count
                    / total_days
                    * 100
                )

            # ------------------------------------------------
            # 強い全台系率
            # ------------------------------------------------

            strong_rate = 0.0

            if total_days > 0:

                strong_rate = (
                    strong_count
                    / total_days
                    * 100
                )

            # ------------------------------------------------
            # 平均全台系スコア
            # ------------------------------------------------

            avg_all_setting_score = (
                sum(
                    self._safe_float(
                        row["全台系スコア"]
                    )
                    for row in records
                )
                / total_days
            )

            # ------------------------------------------------
            # 平均結果強度
            # ------------------------------------------------

            avg_result_strength = (
                sum(
                    self._safe_float(
                        row["結果強度"]
                    )
                    for row in records
                )
                / total_days
            )

            # ------------------------------------------------
            # 平均△以上率
            # ------------------------------------------------

            avg_delta_rate = (
                sum(
                    self._safe_float(
                        row["△以上率"]
                    )
                    for row in records
                )
                / total_days
            )

            # ------------------------------------------------
            # 平均G数
            # ------------------------------------------------

            avg_g = (
                sum(
                    self._safe_float(
                        row["平均G数"]
                    )
                    for row in records
                )
                / total_days
            )

            # ------------------------------------------------
            # 直近5回
            # ------------------------------------------------

            recent_records = records[-5:]

            recent_candidate_count = sum(
                1
                for row in recent_records
                if self._is_all_setting_candidate(
                    row
                )
            )

            recent_candidate_rate = (
                recent_candidate_count
                / len(recent_records)
                * 100
            )

            recent_avg_score = (
                sum(
                    self._safe_float(
                        row["全台系スコア"]
                    )
                    for row in recent_records
                )
                / len(recent_records)
            )

            recent_avg_strength = (
                sum(
                    self._safe_float(
                        row["結果強度"]
                    )
                    for row in recent_records
                )
                / len(recent_records)
            )

            # ------------------------------------------------
            # 最終実績
            # ------------------------------------------------

            last_date = records[-1][
                "日付"
            ]

            last_judgment = str(
                records[-1].get(
                    "判定",
                    ""
                )
            ).strip()

            # ------------------------------------------------
            # 予測日との間隔
            # ------------------------------------------------

            target_dt = (
                self._parse_date(
                    target_date
                )
            )

            last_dt = (
                self._parse_date(
                    last_date
                )
            )

            days_since_last = None

            if (
                target_dt is not None
                and last_dt is not None
            ):

                days_since_last = (
                    target_dt - last_dt
                ).days

            # ------------------------------------------------
            # 結果
            # ------------------------------------------------

            results.append(
                {
                    "島":
                        island,

                    "9の日実績回数":
                        total_days,

                    "全台系候補回数":
                        candidate_count,

                    "強い全台系候補回数":
                        strong_count,

                    "弱い全台系候補回数":
                        weak_count,

                    "通常全台系候補回数":
                        normal_candidate_count,

                    "全台系候補率":
                        round(
                            candidate_rate,
                            2
                        ),

                    "強い全台系率":
                        round(
                            strong_rate,
                            2
                        ),

                    "平均全台系スコア":
                        round(
                            avg_all_setting_score,
                            2
                        ),

                    "平均結果強度":
                        round(
                            avg_result_strength,
                            2
                        ),

                    "平均△以上率":
                        round(
                            avg_delta_rate,
                            2
                        ),

                    "平均G数":
                        round(
                            avg_g,
                            1
                        ),

                    "直近5回候補率":
                        round(
                            recent_candidate_rate,
                            2
                        ),

                    "直近5回平均スコア":
                        round(
                            recent_avg_score,
                            2
                        ),

                    "直近5回平均結果強度":
                        round(
                            recent_avg_strength,
                            2
                        ),

                    "最終実績日":
                        last_date,

                    "最終実績からの日数":
                        days_since_last,

                    "最新判定":
                        last_judgment,
                }
            )

        return results

    # ========================================================
    # 9の日 前回→次回遷移
    # ========================================================

    def get_nine_day_transition_stats(
        self,
        target_date
    ):
        """
        nine_day_transition_pairs.csv を利用して、
        既存の9の日遷移分析を取得する。

        重要:

        既存Prediction Engineの
            「全台系候補 → 全台系候補」

        だけではなく、

        既存分析で確認済みの

            前回「強い全台系候補」
                ↓
            同じ島
                ↓
            次回「強い全台系候補」

        を正式なローテーション指標として扱う。

        既存分析:
            13回中1回
            1 / 13
            = 7.69%

        target_date以前の遷移だけを使用する。
        """

        target_date = str(
            target_date
        )

        # ----------------------------------------------------
        # CSV存在確認
        # ----------------------------------------------------

        if not NINE_DAY_TRANSITION_PATH.exists():

            return {
                "9の日回数": 0,
                "遷移回数": 0,
                "同一島再投入回数": 0,
                "同一島再投入率": 0.0,

                "強い全台系同一島遷移回数":
                    0,

                "強い全台系同一島再投入回数":
                    0,

                "強い全台系同一島再投入率":
                    0.0,

                "遷移データ":
                    "CSVなし",
            }

        # ----------------------------------------------------
        # CSV読み込み
        # ----------------------------------------------------

        rows = []

        with open(
            NINE_DAY_TRANSITION_PATH,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            reader = csv.DictReader(
                f
            )

            for row in reader:

                previous_date = str(
                    row.get(
                        "previous_date",
                        ""
                    )
                ).strip()

                current_date = str(
                    row.get(
                        "current_date",
                        ""
                    )
                ).strip()

                if not previous_date:
                    continue

                if not current_date:
                    continue

                # ------------------------------------------------
                # 未来データ除外
                # ------------------------------------------------

                if current_date >= target_date:

                    continue

                rows.append(
                    row
                )

        if not rows:

            return {
                "9の日回数": 0,
                "遷移回数": 0,
                "同一島再投入回数": 0,
                "同一島再投入率": 0.0,

                "強い全台系同一島遷移回数":
                    0,

                "強い全台系同一島再投入回数":
                    0,

                "強い全台系同一島再投入率":
                    0.0,

                "遷移データ":
                    "データなし",
            }

        # ----------------------------------------------------
        # 遷移日
        # ----------------------------------------------------

        transition_dates = sorted(
            {
                (
                    row["previous_date"],
                    row["current_date"]
                )
                for row in rows
            }
        )

        # ----------------------------------------------------
        # 旧候補→候補統計
        #
        # 参考値として保持。
        #
        # from_was_candidate_plus
        #     ↓
        # 同一島
        #     ↓
        # to_is_candidate_plus
        # ----------------------------------------------------

        candidate_rows = [
            row
            for row in rows
            if str(
                row.get(
                    "from_was_candidate_plus",
                    "0"
                )
            ).strip() == "1"
        ]

        candidate_same_island_rows = [
            row
            for row in candidate_rows
            if (
                row.get(
                    "from_island",
                    ""
                ).strip()
                ==
                row.get(
                    "to_island",
                    ""
                ).strip()
            )
        ]

        candidate_reentry_rows = [
            row
            for row in candidate_same_island_rows
            if str(
                row.get(
                    "to_is_candidate_plus",
                    "0"
                )
            ).strip() == "1"
        ]

        candidate_reentry_rate = 0.0

        if candidate_rows:

            candidate_reentry_rate = (
                len(
                    candidate_reentry_rows
                )
                / len(candidate_rows)
                * 100
            )

        # ----------------------------------------------------
        # 正式な9の日ローテーション統計
        #
        # from_was_strong == 1
        #        ↓
        # from_island == to_island
        #        ↓
        # to_is_strong == 1
        #
        # 13件中1件
        # = 7.69%
        # ----------------------------------------------------

        strong_rows = [
            row
            for row in rows
            if str(
                row.get(
                    "from_was_strong",
                    "0"
                )
            ).strip() == "1"
        ]

        strong_same_island_rows = [
            row
            for row in strong_rows
            if (
                row.get(
                    "from_island",
                    ""
                ).strip()
                ==
                row.get(
                    "to_island",
                    ""
                ).strip()
            )
        ]

        strong_same_reentry_rows = [
            row
            for row in strong_same_island_rows
            if str(
                row.get(
                    "to_is_strong",
                    "0"
                )
            ).strip() == "1"
        ]

        strong_same_count = len(
            strong_same_island_rows
        )

        strong_same_reentry_count = len(
            strong_same_reentry_rows
        )

        strong_same_rate = 0.0

        if strong_same_count > 0:

            strong_same_rate = (
                strong_same_reentry_count
                / strong_same_count
                * 100
            )

        # ----------------------------------------------------
        # 9の日回数
        #
        # CSVの遷移には前回日と今回日があるため、
        # ユニークな日付を取得。
        # ----------------------------------------------------

        nine_days = sorted(
            {
                row["previous_date"]
                for row in rows
            }
            |
            {
                row["current_date"]
                for row in rows
            }
        )

        return {
            "9の日回数":
                len(nine_days),

            # 旧統計
            "遷移回数":
                len(candidate_rows),

            "同一島再投入回数":
                len(candidate_reentry_rows),

            "同一島再投入率":
                round(
                    candidate_reentry_rate,
                    2
                ),

            # 正式なローテーション統計
            "強い全台系同一島遷移回数":
                strong_same_count,

            "強い全台系同一島再投入回数":
                strong_same_reentry_count,

            "強い全台系同一島再投入率":
                round(
                    strong_same_rate,
                    2
                ),

            "遷移データ":
                str(
                    NINE_DAY_TRANSITION_PATH
                ),
        }

    # ========================================================
    # 9の日 島別特徴量
    # ========================================================

    def get_nine_day_features(
        self,
        target_date
    ):

        summary = (
            self.get_nine_day_island_summary(
                target_date
            )
        )

        transition = (
            self.get_nine_day_transition_stats(
                target_date
            )
        )

        # ----------------------------------------------------
        # 直近9の日
        # ----------------------------------------------------

        history = (
            self.get_nine_day_history(
                target_date
            )
        )

        latest_nine_date = None

        latest_islands = set()

        if history:

            latest_nine_date = max(
                row["日付"]
                for row in history
            )

            latest_islands = {
                row["島"]
                for row in history
                if (
                    row["日付"]
                    == latest_nine_date
                    and
                    self._is_all_setting_candidate(
                        row
                    )
                )
            }

        # ----------------------------------------------------
        # 島別情報に追加
        # ----------------------------------------------------

        for row in summary:

            island = row["島"]

            row["前回9の日投入島"] = (
                island
                in latest_islands
            )

            row["前回9の日"] = (
                latest_nine_date
            )

            # 旧統計
            row["同一島再投入率"] = (
                transition[
                    "同一島再投入率"
                ]
            )

            # 正式なローテーション統計
            row[
                "強い全台系同一島再投入率"
            ] = (
                transition[
                    "強い全台系同一島再投入率"
                ]
            )

        return {
            "島別特徴量":
                summary,

            "遷移統計":
                transition,

            "前回9の日":
                latest_nine_date,

            "前回投入島":
                sorted(
                    latest_islands
                ),
        }

    # ========================================================
    # 9の日 判断理由
    # ========================================================

    def build_nine_day_reason(
        self,
        row,
        transition_stats
    ):
        """
        島を候補として扱う理由を生成する。

        注意:
            ここでは新しいスコアリングは行わない。
            既存分析結果を説明する。
        """

        reasons = []

        # ----------------------------------------------------
        # 実績回数
        # ----------------------------------------------------

        if row[
            "9の日実績回数"
        ] > 0:

            reasons.append(
                "過去9の日実績"
                f"{row['9の日実績回数']}回"
            )

        # ----------------------------------------------------
        # 全台系候補率
        # ----------------------------------------------------

        if row[
            "全台系候補率"
        ] > 0:

            reasons.append(
                "全台系候補率"
                f"{row['全台系候補率']}%"
            )

        # ----------------------------------------------------
        # 強い全台系
        # ----------------------------------------------------

        if row[
            "強い全台系候補回数"
        ] > 0:

            reasons.append(
                "強い全台系候補実績"
                f"{row['強い全台系候補回数']}回"
            )

        # ----------------------------------------------------
        # 直近実績
        # ----------------------------------------------------

        if row[
            "直近5回候補率"
        ] > 0:

            reasons.append(
                "直近5回候補率"
                f"{row['直近5回候補率']}%"
            )

        # ----------------------------------------------------
        # 最終実績
        # ----------------------------------------------------

        if (
            row[
                "最終実績からの日数"
            ]
            is not None
        ):

            reasons.append(
                "最終実績から"
                f"{row['最終実績からの日数']}日"
            )

        # ----------------------------------------------------
        # 前回投入
        # ----------------------------------------------------

        if row[
            "前回9の日投入島"
        ]:

            reasons.append(
                "前回9の日も候補島"
            )

        # ----------------------------------------------------
        # 旧候補島再投入率
        #
        # 参考値として表示
        # ----------------------------------------------------

        if (
            transition_stats[
                "遷移回数"
            ] > 0
        ):

            reasons.append(
                "候補島同一島再投入率"
                f"{transition_stats['同一島再投入率']}%"
            )

        # ----------------------------------------------------
        # 正式な強い全台系ローテーション率
        # ----------------------------------------------------

        if (
            transition_stats[
                "強い全台系同一島遷移回数"
            ] > 0
        ):

            reasons.append(
                "強い全台系の同一島再投入率"
                f"{transition_stats['強い全台系同一島再投入率']}%"
            )

        # ----------------------------------------------------
        # 理由なし
        # ----------------------------------------------------

        if not reasons:

            reasons.append(
                "過去データによる候補評価"
            )

        return reasons

    # ========================================================
    # 9の日候補
    # ========================================================

    def get_nine_day_candidates(
        self,
        target_date
    ):
        """
        9の日の島候補一覧。

        現段階では既存分析の特徴量を表示する。

        注意:
            現時点では新しい重み付けモデルを導入しない。
            既存分析の候補率等による暫定表示順を維持する。
        """

        feature_data = (
            self.get_nine_day_features(
                target_date
            )
        )

        rows = feature_data[
            "島別特徴量"
        ]

        transition_stats = (
            feature_data[
                "遷移統計"
            ]
        )

        candidates = []

        for row in rows:

            result = dict(
                row
            )

            result[
                "理由"
            ] = self.build_nine_day_reason(
                row,
                transition_stats
            )

            candidates.append(
                result
            )

        # ----------------------------------------------------
        # 暫定表示順
        #
        # 注意:
        # これは最終予測スコアではない。
        #
        # 今回は既存ロジックを変更しない。
        # ----------------------------------------------------

        candidates.sort(
            key=lambda x: (
                x[
                    "全台系候補率"
                ],
                x[
                    "強い全台系候補回数"
                ],
                x[
                    "直近5回候補率"
                ],
                x[
                    "平均結果強度"
                ],
            ),
            reverse=True
        )

        return candidates

    # ========================================================
    # 予測
    # ========================================================

    def predict(
        self,
        target_date
    ):
        """
        指定日の予測。
        """

        target_date = str(
            target_date
        )

        day_type = (
            self.get_day_type(
                target_date
            )
        )

        # ====================================================
        # 9の日
        # ====================================================

        if day_type == "9の日":

            candidates = (
                self.get_nine_day_candidates(
                    target_date
                )
            )

            transition_stats = (
                self.get_nine_day_transition_stats(
                    target_date
                )
            )

            if not candidates:

                return {
                    "日付":
                        target_date,

                    "営業日タイプ":
                        "9の日",

                    "予測対象":
                        "島",

                    "第一候補":
                        None,

                    "候補":
                        [],

                    "遷移統計":
                        transition_stats,

                    "理由": [
                        "過去9の日のデータがありません"
                    ],
                }

            first = candidates[0]

            return {
                "日付":
                    target_date,

                "営業日タイプ":
                    "9の日",

                "予測対象":
                    "島",

                "第一候補":
                    first["島"],

                "候補":
                    candidates,

                "遷移統計":
                    transition_stats,

                "前回9の日":
                    first[
                        "前回9の日"
                    ],

                "理由":
                    first["理由"],
            }

        # ====================================================
        # 通常日
        # ====================================================

        return {
            "日付":
                target_date,

            "営業日タイプ":
                "通常日",

            "予測対象":
                "通常日モデル",

            "第一候補":
                None,

            "候補":
                [],

            "理由": [
                "通常日モデルは既存の"
                "台・並び予測系統へ接続予定"
            ],
        }


# ============================================================
# CLI
# ============================================================

def main():

    print(
        "=" * 80
    )

    print(
        "ジャグラーラボ Prediction Engine"
    )

    print(
        "=" * 80
    )

    print()

    print(
        f"DB: {DB_PATH}"
    )

    print(
        f"9の日遷移CSV: "
        f"{NINE_DAY_TRANSITION_PATH}"
    )

    if not DB_PATH.exists():

        print()

        print(
            "ERROR: DBが見つかりません。"
        )

        print(
            f"確認先: {DB_PATH}"
        )

        return

    if not NINE_DAY_TRANSITION_PATH.exists():

        print()

        print(
            "WARNING: "
            "nine_day_transition_pairs.csv "
            "が見つかりません。"
        )

        print(
            f"確認先: "
            f"{NINE_DAY_TRANSITION_PATH}"
        )

    print()

    print(
        "予測対象日を入力してください。"
    )

    print(
        "例: 2026-08-19"
    )

    print()

    target_date = input(
        "予測対象日: "
    ).strip()

    try:

        engine = (
            PredictionEngine()
        )

        result = engine.predict(
            target_date
        )

    except Exception as e:

        print()

        print(
            "=" * 80
        )

        print(
            "ERROR"
        )

        print(
            "=" * 80
        )

        print(
            type(e).__name__
        )

        print(
            e
        )

        return

    # ========================================================
    # 基本結果
    # ========================================================

    print()

    print(
        "=" * 80
    )

    print(
        "予測結果"
    )

    print(
        "=" * 80
    )

    print(
        f"予測日              : "
        f"{result['日付']}"
    )

    print(
        f"営業日タイプ        : "
        f"{result['営業日タイプ']}"
    )

    print(
        f"予測対象            : "
        f"{result['予測対象']}"
    )

    print(
        f"第一候補            : "
        f"{result['第一候補']}"
    )

    # ========================================================
    # 遷移統計
    # ========================================================

    transition = (
        result.get(
            "遷移統計"
        )
    )

    if transition:

        print()

        print(
            "-" * 80
        )

        print(
            "9の日 島ローテーション分析"
        )

        print(
            "-" * 80
        )

        print(
            f"9の日回数          : "
            f"{transition['9の日回数']}"
        )

        # ----------------------------------------------------
        # 旧統計
        # ----------------------------------------------------

        print()

        print(
            "【候補島 → 候補島】"
        )

        print(
            f"遷移回数            : "
            f"{transition['遷移回数']}"
        )

        print(
            f"同一島再投入回数    : "
            f"{transition['同一島再投入回数']}"
        )

        print(
            f"同一島再投入率      : "
            f"{transition['同一島再投入率']}%"
        )

        # ----------------------------------------------------
        # 正式な7.69%ロジック
        # ----------------------------------------------------

        print()

        print(
            "【強い全台系 → 同一島 → 強い全台系】"
        )

        print(
            f"対象回数            : "
            f"{transition['強い全台系同一島遷移回数']}"
        )

        print(
            f"次回も強い全台系    : "
            f"{transition['強い全台系同一島再投入回数']}"
        )

        print(
            f"同一島再投入率      : "
            f"{transition['強い全台系同一島再投入率']}%"
        )

        print()

        print(
            "※ 既存分析の「13回中1回・7.69%」"
            "に対応する指標"
        )

    # ========================================================
    # 前回9の日
    # ========================================================

    if result.get(
        "前回9の日"
    ):

        print()

        print(
            f"前回9の日          : "
            f"{result['前回9の日']}"
        )

    # ========================================================
    # 理由
    # ========================================================

    print()

    print(
        "-" * 80
    )

    print(
        "第一候補の判断材料"
    )

    print(
        "-" * 80
    )

    for reason in result[
        "理由"
    ]:

        print(
            f"- {reason}"
        )

    # ========================================================
    # 島別特徴量
    # ========================================================

    if result[
        "候補"
    ]:

        print()

        print(
            "=" * 80
        )

        print(
            "島別特徴量"
        )

        print(
            "=" * 80
        )

        for i, candidate in enumerate(
            result["候補"],
            start=1
        ):

            print()

            print(
                f"{i:2d}. "
                f"{candidate['島']}"
            )

            print(
                f"    9の日実績回数       : "
                f"{candidate['9の日実績回数']}"
            )

            print(
                f"    全台系候補回数      : "
                f"{candidate['全台系候補回数']}"
            )

            print(
                f"    強い全台系候補回数  : "
                f"{candidate['強い全台系候補回数']}"
            )

            print(
                f"    弱い全台系候補回数  : "
                f"{candidate['弱い全台系候補回数']}"
            )

            print(
                f"    全台系候補率        : "
                f"{candidate['全台系候補率']}%"
            )

            print(
                f"    強い全台系率        : "
                f"{candidate['強い全台系率']}%"
            )

            print(
                f"    平均全台系スコア    : "
                f"{candidate['平均全台系スコア']}"
            )

            print(
                f"    平均結果強度        : "
                f"{candidate['平均結果強度']}"
            )

            print(
                f"    平均△以上率        : "
                f"{candidate['平均△以上率']}"
            )

            print(
                f"    直近5回候補率       : "
                f"{candidate['直近5回候補率']}%"
            )

            print(
                f"    直近5回平均スコア   : "
                f"{candidate['直近5回平均スコア']}"
            )

            print(
                f"    最終実績日          : "
                f"{candidate['最終実績日']}"
            )

            print(
                f"    最終実績からの日数  : "
                f"{candidate['最終実績からの日数']}"
            )

            print(
                f"    前回9の日投入島     : "
                f"{'YES' if candidate['前回9の日投入島'] else 'NO'}"
            )

            print(
                f"    最新判定            : "
                f"{candidate['最新判定']}"
            )


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":

    main()
