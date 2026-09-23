# -*- coding: utf-8 -*-
# ==================================
# ジャグラーラボ v9  /  HOME
# ==================================
# STEP 2: HOMEのUIのみ。DB・分析ロジックには一切接続しない。
# CSSとHero/GOGOは クラウド版 app_ui_v8.py からそのまま移植している。
# 触らないこと。

import streamlit as st
import streamlit.components.v1 as components
import datetime
import random
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from analysis.views import (
    get_machine_statistics,
    get_latest_machine_rank,
    get_machine_history,
    get_prediction_top,
    get_latest_prediction_date,
)
from database.db import fetch_all, fetch_one

# scripts/realtime 配下は通常のパッケージ構成ではないため、
# get_realtime_data.py と同じ方式（sys.pathへのフォルダ追加）でimportする。
# realtime_analysis.py 自体は一切変更していない。
SCRIPTS_REALTIME_DIR = BASE_DIR / "scripts" / "realtime"
if str(SCRIPTS_REALTIME_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_REALTIME_DIR))

from realtime_analysis import (
    analyze_realtime,
    prepare_realtime_data,
    calculate_current_evaluation,
    analyze_realtime_v2,
)

# ぶどう入力機能で、台単体の再計算（analyze_machine等）に直接アクセスするため、
# core/ をsys.pathに追加する（realtime_analysis.py側と同じやり方）。
CORE_DIR = BASE_DIR / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from setting_estimation import analyze_machine, check_narabi_suspicion, get_high_setting_score

# ==================================
# ページ設定
# ==================================

st.set_page_config(
    page_title="ジャグラーラボ",
    page_icon="●",
    layout="wide",
)


# ==================================
# 仮データ（STEP 2のみ）
# ==================================
# TODO: STEP 3以降でDBの値に差し替える

STORE_NAME = "Hタワー店"
UPDATED_AT = "11:17"


# ==================================
# 画面の切り替え
# ==================================

page = st.query_params.get("page", "home")

# ==================================
# ブラウザの自動翻訳を無効化
# ==================================

components.html("""
<script>
(function() {
    var d = window.parent.document;
    if (!d.querySelector('meta[name="google"]')) {
        var m = d.createElement('meta');
        m.name = 'google';
        m.content = 'notranslate';
        d.head.appendChild(m);
    }
    d.documentElement.setAttribute('translate', 'no');
})();
</script>
""", height=0)

# ==================================
# v8から移植したCSS（変更禁止）
# ==================================

st.markdown("""
<style>

/* ---------- 基本 ---------- */
.stApp {
    background:
        radial-gradient(circle at 20% 0%, rgba(0,255,150,.055), transparent 28%),
        radial-gradient(circle at 85% 10%, rgba(0,150,255,.045), transparent 25%),
        #05090a;
    color: #d9f7ea;
}

.block-container {
    max-width: 1220px;
    padding-top: 1.1rem;
    padding-bottom: 3rem;
}

/* ---------- 文字 ---------- */
html, body, [class*="css"] {
    font-family: "Segoe UI", "Meiryo", sans-serif;
}

p, label, .stMarkdown, .stCaption {
    color: #a9c8bc;
}

h1, h2, h3 {
    color: #eafff5 !important;
}

/* ---------- Hero ---------- */
.lab-hero {
    position: relative;
    overflow: hidden;
    background:
        linear-gradient(135deg, rgba(7,20,18,.98), rgba(4,12,14,.98));
    border: 1px solid rgba(65,255,175,.38);
    border-radius: 16px;
    padding: 28px 30px 24px;
    margin-bottom: 18px;
    box-shadow:
        0 0 0 1px rgba(65,255,175,.05) inset,
        0 0 32px rgba(0,255,150,.08);
}

.lab-hero::before {
    content: "";
    position: absolute;
    inset: 0;
    background:
        repeating-linear-gradient(
            0deg,
            transparent 0px,
            transparent 3px,
            rgba(65,255,175,.018) 4px
        );
    pointer-events: none;
}

.lab-hero-title {
    position: relative;
    color: #eafff5;
    font-family: "Segoe UI", sans-serif;
    font-size: 2.05rem;
    font-weight: 800;
    letter-spacing: .18em;
    margin: 0;
    text-shadow: 0 0 18px rgba(65,255,175,.28);
}

.lab-hero-subtitle {
    position: relative;
    color: #6dffb8;
    margin-top: 7px;
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: .22em;
    text-transform: uppercase;
}

.lab-status {
    position: relative;
    display: inline-block;
    margin-top: 17px;
    padding: 5px 10px;
    border: 1px solid rgba(65,255,175,.35);
    border-radius: 999px;
    color: #78ffbf;
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .14em;
    background: rgba(0,255,150,.055);
}

.lab-status-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    margin-right: 7px;
    border-radius: 50%;
    background: #5dffad;
    box-shadow: 0 0 12px #5dffad;
}

/* ---------- セクション見出し ---------- */
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    border-left: 3px solid #47ffae;
    padding-left: 12px;
    letter-spacing: .04em;
}

/* ---------- Metric ---------- */
[data-testid="stMetric"] {
    background:
        linear-gradient(145deg, rgba(11,24,22,.96), rgba(5,14,16,.96));
    border: 1px solid rgba(65,255,175,.22);
    border-radius: 10px;
    padding: 13px 15px;
    box-shadow:
        0 0 0 1px rgba(255,255,255,.015) inset,
        0 8px 24px rgba(0,0,0,.22);
}

[data-testid="stMetricLabel"] {
    color: #76988b;
    font-weight: 700;
    letter-spacing: .06em;
}

[data-testid="stMetricValue"] {
    color: #eafff5;
    font-weight: 800;
    text-shadow: 0 0 12px rgba(65,255,175,.10);
}

/* ---------- ボタン ---------- */
.stButton > button {
    min-height: 42px;
    border-radius: 8px;
    border: 1px solid rgba(65,255,175,.42);
    background: rgba(5,20,17,.96);
    color: #8dffc8;
    font-weight: 800;
    letter-spacing: .04em;
    box-shadow: 0 0 16px rgba(0,255,150,.055);
    transition: all .18s ease;
}

.stButton > button:hover {
    border-color: #65ffb3;
    color: #eafff5;
    box-shadow:
        0 0 5px rgba(65,255,175,.35),
        0 0 22px rgba(65,255,175,.13);
    transform: translateY(-1px);
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0a2b20, #071916);
    border-color: #55ffae;
    color: #baffdc;
}


/* ---------- 入力 ---------- */
[data-testid="stNumberInput"] {
    background: rgba(7,18,19,.96) !important;
    border: 1px solid rgba(65,255,175,.30);
    border-radius: 10px;
    padding: 4px;
    box-shadow: 0 0 14px rgba(0,255,150,.035);
}

[data-testid="stNumberInput"] [data-baseweb="input"],
[data-testid="stNumberInput"] [data-baseweb="input"] > div {
    background: #071311 !important;
    border-color: rgba(65,255,175,.30) !important;
    border-radius: 7px !important;
}

[data-testid="stNumberInput"] input,
[data-testid="stNumberInput"] [data-baseweb="input"] input {
    background: #071311 !important;
    color: #eafff5 !important;
    -webkit-text-fill-color: #eafff5 !important;
    caret-color: #70ffbb !important;
    font-weight: 800 !important;
    font-size: 1.05rem !important;
}

[data-testid="stNumberInput"] input::placeholder {
    color: #55776b !important;
    -webkit-text-fill-color: #55776b !important;
}

[data-testid="stNumberInput"] button {
    background: #071311 !important;
    color: #73ffb9 !important;
    border-color: rgba(65,255,175,.16) !important;
}

[data-testid="stNumberInput"] button:hover {
    background: #0b211b !important;
    color: #eafff5 !important;
}
[data-testid="stNumberInput"] {
    background: rgba(7,18,19,.96) !important;
    border: 1px solid rgba(65,255,175,.30);
    border-radius: 10px;
    padding: 4px;
    box-shadow: 0 0 14px rgba(0,255,150,.035);
}

/* Streamlit / BaseWeb の実入力欄 */
[data-testid="stNumberInput"] [data-baseweb="input"],
[data-testid="stNumberInput"] [data-baseweb="input"] > div {
    background: #071311 !important;
    border-color: rgba(65,255,175,.30) !important;
    border-radius: 7px !important;
}

[data-testid="stNumberInput"] input,
[data-testid="stNumberInput"] [data-baseweb="input"] input {
    background: #071311 !important;
    color: #eafff5 !important;
    -webkit-text-fill-color: #eafff5 !important;
    caret-color: #70ffbb !important;
    font-weight: 800 !important;
    font-size: 1.05rem !important;
}

[data-testid="stNumberInput"] input::placeholder {
    color: #55776b !important;
    -webkit-text-fill-color: #55776b !important;
}

[data-testid="stNumberInput"] button {
    background: #071311 !important;
    color: #73ffb9 !important;
    border-color: rgba(65,255,175,.16) !important;
}

[data-testid="stNumberInput"] button:hover {
    background: #0b211b !important;
    color: #eafff5 !important;
}
[data-testid="stNumberInput"] {
    background: rgba(7,18,19,.92);
    border-radius: 9px;
}

[data-testid="stNumberInput"] input {
    color: #eafff5 !important;
    border-color: rgba(65,255,175,.3) !important;
    border-radius: 8px;
}

/* ---------- DataFrame ---------- */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(65,255,175,.16);
    border-radius: 9px;
    overflow: hidden;
    box-shadow: 0 8px 24px rgba(0,0,0,.20);
}

/* ---------- Alert ---------- */
[data-testid="stAlert"] {
    border-radius: 9px;
    background: rgba(8,22,21,.92);
}

/* ---------- Caption ---------- */
.stCaption {
    color: #668b7d !important;
    letter-spacing: .02em;
}

/* ---------- GOGO! visual ---------- */
.gogo-panel {
    display: flex;
    align-items: center;
    gap: 22px;
    padding: 12px 14px;
    margin: 0 0 20px 0;
    border: 1px solid rgba(65,255,175,.18);
    border-radius: 12px;
    background: rgba(3,11,12,.72);
}

.gogo-panel img {
    width: 185px;
    height: auto;
    filter: drop-shadow(0 0 14px rgba(65,255,175,.18));
}

.gogo-copy {
    color: #6dffb8;
    font-size: .75rem;
    line-height: 1.65;
    letter-spacing: .08em;
}

.gogo-copy strong {
    color: #eafff5;
    font-size: .95rem;
}

/* ---------- Mobile ---------- */
@media (max-width: 700px) {
    .block-container {
        padding: .75rem .65rem 2rem;
    }

    .lab-hero {
        padding: 22px 20px;
    }

    .lab-hero-title {
        font-size: 1.48rem;
        letter-spacing: .12em;
    }

    .lab-hero-subtitle {
        font-size: .68rem;
        letter-spacing: .14em;
    }

    [data-testid="stMetric"] {
        padding: 10px 11px;
    }

    .gogo-panel {
        gap: 13px;
    }

    .gogo-panel img {
        width: 120px;
    }

    .gogo-copy {
        font-size: .65rem;
    }
}

/* Streamlitの上部ツールバーを目立たせない */
[data-testid="stToolbar"] {
    visibility: hidden;
}

</style>
""", unsafe_allow_html=True)

# ==================================
# v9で追加するCSS
# ==================================

st.markdown("""
<style>

/* ---------- Matrix風の背景（v9で追加） ---------- */
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background:
        repeating-linear-gradient(0deg,
            transparent 0px, transparent 2px,
            rgba(65,255,175,.012) 3px, rgba(65,255,175,.012) 3px),
        repeating-linear-gradient(90deg,
            transparent 0px, transparent 43px,
            rgba(65,255,175,.020) 44px),
        repeating-linear-gradient(0deg,
            transparent 0px, transparent 43px,
            rgba(65,255,175,.020) 44px);
}

.block-container {
    position: relative;
    z-index: 1;
}

/* ---------- HOME全体のまとまり ---------- */
.lab-home {
    max-width: 560px;
    margin: 0 auto;
}

/* ---------- 店舗名 / 更新時刻 ---------- */
.lab-bar {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
    padding: 9px 13px;
    margin-bottom: 20px;
    border: 1px solid rgba(65,255,175,.16);
    border-radius: 10px;
    background: rgba(3,11,12,.72);
}

.lab-bar-store {
    color: #eafff5;
    font-size: .92rem;
    font-weight: 800;
    letter-spacing: .06em;
}

.lab-bar-time {
    color: #6dffb8;
    font-size: .7rem;
    letter-spacing: .08em;
    white-space: nowrap;
}

/* ---------- SELECT MODULE ---------- */
.lab-label {
    color: #6dffb8;
    font-size: .7rem;
    font-weight: 800;
    letter-spacing: .26em;
    margin: 0 0 11px 2px;
}

/* ---------- MODULE 2x2 ---------- */
/* st.columns は狭い画面で縦積みになるため使わない。
   CSS Grid で必ず2列にする。 */
.module-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}

.module-card {
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    min-height: 118px;
    padding: 14px 15px 15px;
    border: 1px solid rgba(65,255,175,.34);
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(7,20,18,.97), rgba(4,12,14,.97));
    box-shadow:
        0 0 0 1px rgba(65,255,175,.05) inset,
        0 0 20px rgba(0,255,150,.06);
    text-decoration: none !important;
    transition: all .18s ease;
}

.module-card::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
        repeating-linear-gradient(0deg,
            transparent 0px, transparent 3px,
            rgba(65,255,175,.018) 4px);
}

.module-card:hover {
    border-color: #65ffb3;
    box-shadow:
        0 0 5px rgba(65,255,175,.30),
        0 0 24px rgba(65,255,175,.12);
    transform: translateY(-1px);
}

.module-no {
    position: absolute;
    top: 11px;
    right: 13px;
    color: rgba(109,255,184,.45);
    font-size: .62rem;
    font-weight: 800;
    letter-spacing: .12em;
}

.module-en {
    position: relative;
    display: block;
    color: #8dffc8;
    font-size: 1.0rem;
    font-weight: 800;
    letter-spacing: .1em;
    line-height: 1.2;
    text-shadow: 0 0 14px rgba(65,255,175,.22);
}

.module-jp {
    position: relative;
    display: block;
    margin-top: 6px;
    color: #a9c8bc;
    font-size: .66rem;
    letter-spacing: .04em;
}

/* ---------- 準備中ページ ---------- */
.lab-soon {
    max-width: 560px;
    margin: 0 auto;
    padding: 26px 20px;
    border: 1px solid rgba(65,255,175,.22);
    border-radius: 14px;
    background: rgba(3,11,12,.72);
    text-align: center;
}

.lab-soon-en {
    color: #8dffc8;
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: .14em;
}

.lab-soon-note {
    color: #a9c8bc;
    font-size: .7rem;
    letter-spacing: .06em;
    margin-top: 8px;
}

.lab-back {
    display: inline-block;
    margin-top: 18px;
    padding: 7px 16px;
    border: 1px solid rgba(65,255,175,.38);
    border-radius: 999px;
    color: #8dffc8 !important;
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: .14em;
    text-decoration: none !important;
}

/* ---------- REALTIME 詳細 ---------- */
.rt-wrap {
    max-width: 420px;
    margin: 0 auto;
    padding: 20px 22px 22px;
    border: 1px solid rgba(65,255,175,.34);
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(7,20,18,.98), rgba(4,12,14,.98));
    box-shadow:
        0 0 0 1px rgba(65,255,175,.05) inset,
        0 0 28px rgba(0,255,150,.07);
}

.rt-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
}

.rt-head-label {
    color: #6dffb8;
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: .24em;
}

.rt-head-no {
    color: #eafff5;
    font-size: 1.3rem;
    font-weight: 800;
    letter-spacing: .04em;
    text-shadow: 0 0 14px rgba(65,255,175,.24);
}

.rt-model {
    margin-top: 4px;
    color: #a9c8bc;
    font-size: .78rem;
    letter-spacing: .04em;
}

.rt-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 18px;
}

.rt-cell {
    padding: 10px 12px;
    border: 1px solid rgba(65,255,175,.16);
    border-radius: 10px;
    background: rgba(3,11,12,.7);
}

.rt-cell-label {
    display: block;
    color: #6dffb8;
    font-size: .64rem;
    letter-spacing: .1em;
}

.rt-cell-value {
    display: block;
    margin-top: 3px;
    color: #eafff5;
    font-size: 1.05rem;
    font-weight: 800;
}

.rt-rate {
    margin-top: 14px;
    padding: 10px 12px 12px;
    border: 1px solid rgba(65,255,175,.28);
    border-radius: 10px;
    background: rgba(0,255,150,.05);
}

.rt-rate-top {
    display: flex;
    align-items: center;
    gap: 10px;
}

.rt-rate-label {
    color: #6dffb8;
    font-size: .68rem;
    letter-spacing: .1em;
}

.rt-rate-value {
    color: #eafff5;
    font-size: 1.3rem;
    font-weight: 800;
}

.rt-rate-reason {
    margin-top: 7px;
    padding-top: 7px;
    border-top: 1px dashed rgba(65,255,175,.2);
    color: #a9c8bc;
    font-size: .68rem;
    line-height: 1.5;
    letter-spacing: .02em;
}

.rt-updated {
    margin-top: 14px;
    color: #6dffb8;
    font-size: .68rem;
    letter-spacing: .08em;
}

/* ---------- PAST DATA ---------- */
.pd-wrap {
    max-width: 480px;
    margin: 0 auto;
    padding: 20px 16px 22px;
    border: 1px solid rgba(65,255,175,.34);
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(7,20,18,.98), rgba(4,12,14,.98));
    box-shadow:
        0 0 0 1px rgba(65,255,175,.05) inset,
        0 0 28px rgba(0,255,150,.07);
}

.pd-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
}

.pd-head-label {
    color: #6dffb8;
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: .24em;
}

.pd-head-no {
    color: #eafff5;
    font-size: 1.3rem;
    font-weight: 800;
    letter-spacing: .04em;
    text-shadow: 0 0 14px rgba(65,255,175,.24);
}

.pd-model {
    margin-top: 4px;
    color: #a9c8bc;
    font-size: .78rem;
    letter-spacing: .04em;
}

.pd-table {
    margin-top: 16px;
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.pd-row {
    display: grid;
    grid-template-columns: .85fr .55fr .55fr .95fr 1fr .6fr;
    align-items: center;
    gap: 4px;
    padding: 8px 8px;
    border: 1px solid rgba(65,255,175,.16);
    border-radius: 8px;
    background: rgba(3,11,12,.7);
}

.pd-row-head {
    border: none;
    background: transparent;
    padding: 0 8px 2px;
}

.tm-row {
    grid-template-columns: .5fr 1.6fr .5fr;
}

a.tm-row {
    color: inherit !important;
    text-decoration: none !important;
    transition: border-color .15s ease;
}

a.tm-row:hover {
    border-color: #65ffb3;
}

.pd-row-head .pd-col {
    color: #6dffb8;
    font-size: .6rem;
    font-weight: 800;
    letter-spacing: .04em;
}

.pd-col {
    color: #eafff5;
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .01em;
    text-align: center;
    white-space: nowrap;
}

.pd-col-date {
    text-align: left;
    color: #cdeedd;
}

.pd-col-rate {
    font-size: .88rem;
    font-weight: 800;
}

.pd-rate-s { color: #6dffb8; text-shadow: 0 0 10px rgba(65,255,175,.4); }
.pd-rate-a { color: #cdeedd; }
.pd-rate-b { color: #7a8f88; }

.mv-card {
    display: block;
    padding: 8px 8px;
    border: 1px solid rgba(65,255,175,.16);
    border-radius: 8px;
    background: rgba(3,11,12,.7);
    text-decoration: none !important;
    color: inherit !important;
    transition: border-color .15s ease;
}

.mv-card:hover {
    border-color: #65ffb3;
}

.mv-row-top {
    display: grid;
    grid-template-columns: .32fr .58fr 1.2fr .55fr;
    align-items: center;
    gap: 4px;
}

.pd-col-rank {
    text-align: center;
    color: #6dffb8;
    font-size: .68rem;
    font-weight: 800;
}

.mv-row-stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 4px;
    margin-top: 5px;
    padding-top: 5px;
    border-top: 1px solid rgba(65,255,175,.1);
}

.mv-row-stats span {
    font-size: .6rem;
    color: #9fe6c8;
    text-align: center;
    white-space: nowrap;
}

.mv-row-narabi {
    margin-top: 5px;
    padding-top: 5px;
    border-top: 1px dashed rgba(65,255,175,.2);
    color: #a9c8bc;
    font-size: .62rem;
    line-height: 1.4;
}

.mv-setting-table {
    margin-top: 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.mv-setting-row {
    display: grid;
    grid-template-columns: .8fr 1fr 1fr 1fr;
    gap: 4px;
    padding: 6px 8px;
    border: 1px solid rgba(65,255,175,.16);
    border-radius: 8px;
    background: rgba(3,11,12,.7);
    font-size: .68rem;
    color: #eafff5;
    text-align: center;
}

.mv-setting-row-head {
    border: none;
    background: transparent;
    color: #6dffb8;
    font-size: .6rem;
    font-weight: 800;
}

.pd-range {
    margin-top: 3px;
    color: #6dffb8;
    font-size: .68rem;
    letter-spacing: .04em;
}

.pd-nav {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-top: 12px;
}

.pd-nav-btn {
    display: block;
    padding: 8px 10px;
    border: 1px solid rgba(65,255,175,.38);
    border-radius: 9px;
    background: rgba(5,20,17,.9);
    color: #8dffc8 !important;
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .04em;
    text-align: center;
    text-decoration: none !important;
}

.pd-nav-btn-disabled {
    color: #4a5a54 !important;
    border-color: rgba(65,255,175,.12);
    cursor: default;
}

/* ---------- \u30d5\u30ed\u30a2\u30ea\u30f3\u30af ---------- */
.lab-map-link {
    display: block;
    margin-top: 12px;
    padding: 9px 12px;
    border: 1px solid rgba(65,255,175,.3);
    border-radius: 9px;
    background: rgba(3,11,12,.7);
    color: #8dffc8 !important;
    font-size: .74rem;
    font-weight: 800;
    letter-spacing: .04em;
    text-align: center;
    text-decoration: none !important;
}

/* ---------- HEATMAP ---------- */
/* 実際の台マップはcomponents.html側の独自CSS（build_heatmap_html内）で完結しているため、
   ここでは凡例・見出し表示に使うpd-*クラスのみ流用している */

/* ---------- スマホ ---------- */
@media (max-width: 700px) {
    .module-card {
        min-height: 104px;
        padding: 12px 12px 13px;
    }

    .module-en {
        font-size: .92rem;
        letter-spacing: .08em;
    }

    .module-jp {
        font-size: .62rem;
    }

    .lab-bar {
        margin-bottom: 16px;
    }
}

</style>
""", unsafe_allow_html=True)


# ==================================
# v8から移植したHero / GOGO（変更禁止）
# ==================================

st.markdown("""
<div class="lab-hero">
    <div class="lab-hero-title">JUGGLER LAB</div>
    <div class="lab-hero-subtitle">DATA ANALYSIS SYSTEM</div>
    <div class="lab-status"><span class="lab-status-dot"></span>SYSTEM READY</div>
</div>

<div class="gogo-panel">
    <img src="data:image/png;base64,{{GOGO_IMAGE}}" alt="GOGO signal">
    <div class="gogo-copy">
        <strong>GOGO SIGNAL / ANALYSIS MODE</strong><br>
        台データを解析し、現在の状況と次の狙い目を可視化します。
    </div>
</div>
""".replace("{{GOGO_IMAGE}}", "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PwJhsWPLVR/JW0Rm2222wZcWwO1rZmYGN918M/5644246+9/x/0PPID7H3wQk5OTmJ2bw+zsLMrlMqqVCkZGRrBq5UpsucUW2GLzzbHdtttit112wW677oqddtxxQQ3/CILPIfS6inLOce7HP45ttt6672VpNBq47i9/we+vuQa33XEH/n733Vi/fj0mp6YQBAGWjY1h8802wy4774y999wTRz7jGdh7zz37LkwcfthhePub3oRPnXeeN80sa4yWRbXRKq9Z1hzJczGl9twdkvbsVV+pPRdsz7w5cshfPtlycH3iFZ+sgTGADTwjLLJeKK0pSiAsMhAhJBAWA0YqT8Em46/3RZdKJXz2E5/AqpXzs/DdunXr8JMrr8SVV12Fa669FmEY5qafm5vD3NwcNmzciEcefRS333lnJk2lUsF+++yDpz7lKTho9Wo8/ZBDMDralgdi52DAbAvXxde96lU4+KlP7Wsx7nvgAXz7ggvw/R/+0Ls8frPZxNzcHJ5Yuxa333knfnrllfifz34W2227LV5+8sl42UknYcXy5X0r4xte+1pM/OY3+Mv11zvjIwheR1ipIKj78ggRBfUcskLtuXvMtnDfpfYco0h7fvAHf8S2J/mnBU68+lPPtFwyB4QNMvWVpXcMYMLYe4JBEA0kEBYnWGkkf59VAoGw8GjOTWt/uTVIw2KnrX+dt5DMWe95D/7fv/xL38oncc+99+Lr//u/uOTSSzE7N9fXe1UqFTz9kEPwzKOPxrHPehY232yz3PTX33gjXnraac64ADwcF5Vp37Uhi4JJ1L2d5Z67744ffve7fVN8ZmZn8YWvfAVf//a3Ua97eVQhbLJqFd711rfi1BNP7JvCcs+99+L5J56ImRn3dm0MLFouqhuZR2WYYvXxvIVkqD0Xas/eDfVCRMEkq3tZFLVnE63ac2Xz5Tj0ivcjGM06EEy87txnI4wEmmGEMBIIowhhFOEfT1yERridK79fXXEFnrTDDj0p+9HHHYf7HnjAHXnPo3uj2bwbQsRET35DfkOosPRcO46/YIXoAQBQqo4RjSQQBhw0h5BAGHasGHtJHhk85KCD+m48T09P45PnnotjTzgB5198cd+NZwCo1+v49e9+hw999KN4xrOfjde/5S34yc9/jrle37uAOvjRD36wb8bz3ffcgxNPOw1f/NrXujaeAWDtunX4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"), unsafe_allow_html=True)

# ==================================
# HOME
# ==================================
# 注意: HTMLは必ず行頭から書くこと。
# インデントするとMarkdownがコードブロックと解釈し、
# HTMLがそのまま画面に表示される。

HOME_HTML = """
<div class="lab-home">

<div class="lab-bar">
<span class="lab-bar-store">{store}</span>
<span class="lab-bar-time">データ更新 {updated}</span>
</div>

<div class="lab-label">SELECT MODULE</div>

<div class="module-grid" translate="no">

<a class="module-card" href="?page=realtime" target="_self">
<span class="module-no">01</span>
<span class="module-en">REALTIME</span>
<span class="module-jp">現在の台データ</span>
</a>

<a class="module-card" href="?page=past" target="_self">
<span class="module-no">02</span>
<span class="module-en">PAST DATA</span>
<span class="module-jp">過去データ</span>
</a>

<a class="module-card" href="?page=tomorrow" target="_self">
<span class="module-no">03</span>
<span class="module-en">TOMORROW</span>
<span class="module-jp">明日の予想</span>
</a>

<a class="module-card" href="?page=move" target="_self">
<span class="module-no">04</span>
<span class="module-en">MOVE</span>
<span class="module-jp">移動候補</span>
</a>

</div>
</div>
"""


# ==================================
# 各MODULE（STEP 3以降で中身を作る）
# ==================================

MODULES = {
    "realtime": ("REALTIME", "現在の台データ"),
    "past": ("PAST DATA", "過去データ"),
    "tomorrow": ("TOMORROW", "明日の予想"),
    "move": ("MOVE", "移動候補"),
}

SOON_HTML = """
<div class="lab-soon">
<div class="lab-soon-en">{en}</div>
<div class="lab-soon-note">{jp} / UNDER CONSTRUCTION</div>
<a class="lab-back" href="?page=home" target="_self">&#8592; BACK</a>
</div>
"""


# ==================================
# REALTIME（raw_data接続 / STEP 4-1改）
# ==================================
# 本日の raw_data（最新取得分）を対象に切り替え。
# prepare_realtime_data / calculate_current_evaluation は
# scripts/realtime/realtime_analysis.py の既存関数をそのまま利用（ロジック変更なし）。
# 順位・高設定率・平均合成（reasonの補足情報）は従来通り daily_data の履歴系関数を使用。

# TODO: 台選択UIができるまでの仮の対象台番号（動作確認用）
DEFAULT_MACHINE_NO = 969


# ==================================
# 台選択（machinesマスタ / STEP 5）
# ==================================
# REALTIME・PAST DATA共通の台番号選択欄。
# machinesテーブル（id, store, island, machine, number）をそのまま参照するだけで、
# 既存のテーブル・関数は変更していない。

def get_all_machines():
    rows = fetch_all(
        """
        SELECT number, machine, island
        FROM machines
        ORDER BY number
        """
    )
    return [dict(row) for row in rows]


def build_machine_options(machines):
    # st.selectboxはクリックして文字を打つと候補が自動で絞り込まれる
    # （Streamlit純正ウィジェットのネイティブ機能）。
    options = [
        "{number} {machine}（{island}）".format(
            number=m.get("number"),
            machine=m.get("machine") or "-",
            island=m.get("island") or "-",
        )
        for m in machines
    ]
    no_by_option = {
        opt: m.get("number") for opt, m in zip(options, machines)
    }
    return options, no_by_option


def render_machine_picker(form_key, current_no, machines, reset_week=False):
    options, no_by_option = build_machine_options(machines)
    current_option = next(
        (opt for opt, no in no_by_option.items() if no == current_no),
        options[0] if options else None,
    )
    with st.form(form_key):
        selected_option = st.selectbox(
            "台番号で検索",
            options,
            index=options.index(current_option) if current_option in options else 0,
        )
        submitted = st.form_submit_button("表示")
    if submitted:
        st.query_params["no"] = str(no_by_option[selected_option])
        if reset_week:
            st.query_params["week"] = "0"
        st.rerun()


def load_realtime_machine(machine_no):
    today = datetime.date.today().strftime("%Y-%m-%d")

    rows = fetch_all(
        """
        SELECT r.*
        FROM raw_data r
        INNER JOIN (
            SELECT 台番号, MAX(取得日時) AS max_dt
            FROM raw_data
            WHERE 日付 = ? AND 台番号 = ?
            GROUP BY 台番号
        ) latest
        ON r.台番号 = latest.台番号
        AND r.取得日時 = latest.max_dt
        WHERE r.日付 = ? AND r.台番号 = ?
        """,
        [today, machine_no, today, machine_no],
    )
    if not rows:
        return None

    df = pd.DataFrame([dict(row) for row in rows])
    df = prepare_realtime_data(df)
    row = df.iloc[0]
    current_rate = calculate_current_evaluation(row)

    rank = get_latest_machine_rank(machine_no)
    stats = get_machine_statistics(machine_no)

    games = row.get("G数")
    total = row.get("合成")
    bb = row.get("BIG数")
    rb = row.get("REG数")

    reason_parts = []
    if rank.get("順位") and rank.get("対象台数"):
        reason_parts.append(
            f"全{rank['対象台数']}台中{rank['順位']}位"
        )
    if stats.get("高設定率") is not None:
        reason_parts.append(f"高設定率 {stats['高設定率']}%")
    if stats.get("平均合成") is not None:
        reason_parts.append(f"平均合成 1/{stats['平均合成']}")

    return {
        "no": str(machine_no),
        "model": row.get("機種") or "-",
        "games": f"{int(games):,}" if pd.notna(games) else "-",
        "bb": str(int(bb)) if pd.notna(bb) else "-",
        "rb": str(int(rb)) if pd.notna(rb) else "-",
        "total": f"1/{total:g}" if pd.notna(total) else "-",
        "rate": current_rate or "-",
        "reason": "　/　".join(reason_parts) if reason_parts else "データ不足",
        "updated": row.get("取得日時") or "-",
    }

RT_HTML = """
<div class="rt-wrap">

<div class="rt-head">
<span class="rt-head-label">MACHINE</span>
<span class="rt-head-no">No.{no}</span>
</div>

<div class="rt-model">{model}</div>

<div class="rt-grid">
<div class="rt-cell"><span class="rt-cell-label">BB</span><span class="rt-cell-value">{bb}</span></div>
<div class="rt-cell"><span class="rt-cell-label">RB</span><span class="rt-cell-value">{rb}</span></div>
<div class="rt-cell"><span class="rt-cell-label">G\u6570</span><span class="rt-cell-value">{games}</span></div>
<div class="rt-cell"><span class="rt-cell-label">\u5408\u6210</span><span class="rt-cell-value">{total}</span></div>
<div class="rt-cell"><span class="rt-cell-label">\u3076\u3069\u3046</span><span class="rt-cell-value">{grape}</span></div>
<div class="rt-cell"><span class="rt-cell-label">\u3076\u3069\u3046\u78ba\u7387</span><span class="rt-cell-value">{grape_total}</span></div>
</div>

<div class="mv-setting-table">
<div class="mv-setting-row mv-setting-row-head">
<span>\u8a2d\u5b9a</span><span>\u53ef\u80fd\u6027</span><span>BB\u7406\u8ad6\u5024</span><span>RB\u7406\u8ad6\u5024</span>
</div>
{setting_rows}
</div>

<div class="rt-rate">
<div class="rt-rate-top">
<span class="rt-rate-label">DATA CONFIDENCE</span>
<span class="rt-rate-value {confidence_class}">{confidence}</span>
</div>
{narabi_detail_html}
</div>

<div class="rt-updated">\u30c7\u30fc\u30bf\u66f4\u65b0 {updated}</div>

<a class="lab-map-link" href="?page=heatmap&from=realtime" target="_self">\U0001F5FA \u30d5\u30ed\u30a2\u3067\u898b\u308b</a>

<a class="lab-back" href="?page=home" target="_self">&#8592; BACK</a>

</div>
"""


# ==================================
# PAST DATA（仮データ / STEP 3-2）
# ==================================
# TODO: 後の工程でDBの実データに差し替える

def load_past_week(machine_no, week_offset):
    """analysis.views.get_machine_history\u3092\u4f7f\u3044\u3001\u9031\u5358\u4f4d\u306b\u5207\u308a\u51fa\u3059\u3002
    \u623b\u308a\u5024: (\u305d\u306e\u9031\u306e\u65e5\u5225\u30c7\u30fc\u30bf list, \u5c65\u6b74\u7dcf\u65e5\u6570, \u6a5f\u7a2e\u540d)
    """
    df = get_machine_history(machine_no)
    if df.empty:
        return [], 0, None

    total = len(df)
    start = week_offset * 7
    chunk = df.iloc[start:start + 7]

    model = df.iloc[0].get("\u6a5f\u7a2e")

    days = []
    for _, row in chunk.iterrows():
        date_raw = str(row.get("\u65e5\u4ed8") or "")
        mmdd = date_raw[5:7] + "/" + date_raw[8:10] if len(date_raw) >= 10 else date_raw
        games = row.get("G\u6570")
        total_val = row.get("\u5408\u6210\u78ba\u7387")
        days.append({
            "date": mmdd,
            "date_iso": date_raw,
            "bb": str(row.get("BB", "-")),
            "rb": str(row.get("RB", "-")),
            "games": f"{games:,}" if games is not None else "-",
            "total": f"1/{total_val}" if total_val is not None else "-",
            "rate": row.get("\u8a55\u4fa1") or "-",
        })
    return days, total, model

PD_RATE_CLASS = {
    "\u25ce": "pd-rate-s",
    "\u25cb": "pd-rate-a",
    "\u25b3": "pd-rate-b",
}

# DATA CONFIDENCE（観測データの厚み）表示用。既存のpd-rate配色を流用するだけで、
# 高設定かどうかの判定バッジではない。
CONFIDENCE_CLASS = {
    "HIGH": "pd-rate-s",
    "MEDIUM": "pd-rate-a",
    "LOW": "pd-rate-b",
}

PD_ROW_HTML = """
<div class="pd-row">
<span class="pd-col pd-col-date">{date}</span>
<span class="pd-col pd-col-num">{bb}</span>
<span class="pd-col pd-col-num">{rb}</span>
<span class="pd-col pd-col-games">{games}</span>
<span class="pd-col pd-col-total">{total}</span>
<span class="pd-col pd-col-rate {rate_class}">{rate}</span>
</div>
"""

PD_HTML_HEAD = """
<div class="pd-wrap">

<div class="pd-head">
<span class="pd-head-label">PAST DATA</span>
<span class="pd-head-no">No.{no}</span>
</div>

<div class="pd-model">{model}</div>
<div class="pd-range">{range_start} \u301c {range_end}</div>

<div class="pd-table">

<div class="pd-row pd-row-head">
<span class="pd-col pd-col-date">\u65e5\u4ed8</span>
<span class="pd-col pd-col-num">BB</span>
<span class="pd-col pd-col-num">RB</span>
<span class="pd-col pd-col-games">G\u6570</span>
<span class="pd-col pd-col-total">\u5408\u6210</span>
<span class="pd-col pd-col-rate">\u8a55\u4fa1</span>
</div>
"""

PD_NAV_HTML = """
<div class="pd-nav">
{prev_btn}
{next_btn}
</div>
"""

PD_NAV_PREV_ACTIVE = '<a class="pd-nav-btn" href="?page=past&no={no}&week={prev_week}" target="_self">\u2190 \u524d\u306e\u9031</a>'
PD_NAV_PREV_DISABLED = '<span class="pd-nav-btn pd-nav-btn-disabled">\u2190 \u524d\u306e\u9031</span>'
PD_NAV_NEXT_ACTIVE = '<a class="pd-nav-btn" href="?page=past&no={no}&week={next_week}" target="_self">\u6b21\u306e\u9031 \u2192</a>'
PD_NAV_NEXT_DISABLED = '<span class="pd-nav-btn pd-nav-btn-disabled">\u6b21\u306e\u9031 \u2192</span>'

PD_MAP_LINK_HTML = (
    '<a class="lab-map-link" href="?page=heatmap&from=past&date={date_iso}" '
    'target="_self">\U0001F5FA \u30d5\u30ed\u30a2\u3067\u898b\u308b</a>\n'
)

PD_HTML_TAIL = """
</div>

<a class="lab-back" href="?page=home" target="_self">&#8592; BACK</a>

</div>
"""


# ==================================
# TOMORROW（DB接続 / STEP 4-2）
# ==================================
# get_prediction_top はanalysis/views.pyの既存関数をそのまま利用（ロジック変更なし）

def load_tomorrow_picks():
    df = get_prediction_top(limit=5)
    date = get_latest_prediction_date()
    if df.empty:
        return [], date

    picks = []
    for _, row in df.iterrows():
        score = row.get("\u7dcf\u5408\u30b9\u30b3\u30a2")
        judge = row.get("\u5224\u5b9a") or "-"
        island = row.get("\u5cf6")
        reason_parts = []
        if score is not None:
            reason_parts.append(f"\u7dcf\u5408\u30b9\u30b3\u30a2 {score}")
        if island:
            reason_parts.append(str(island))
        picks.append({
            "no": str(row.get("\u53f0\u756a\u53f7")),
            "model": row.get("\u6a5f\u7a2e") or "-",
            "rate": judge,
            "reason": "\u3000/\u3000".join(reason_parts) if reason_parts else "\u30c7\u30fc\u30bf\u4e0d\u8db3",
        })
    return picks, date

TM_ROW_HTML = """
<a class="pd-row tm-row" href="?page=tomorrow&no={no}" target="_self">
<span class="pd-col pd-col-date">No.{no}</span>
<span class="pd-col" style="text-align:left;">{model}</span>
<span class="pd-col pd-col-rate {rate_class}">{rate}</span>
</a>
"""

TM_HTML_HEAD = """
<div class="pd-wrap">

<div class="pd-head">
<span class="pd-head-label">TOMORROW</span>
<span class="pd-head-no">{date}</span>
</div>

<div class="pd-model">\u660e\u65e5\u306e\u4e88\u60f3\u53f0</div>

<div class="pd-table">

<div class="pd-row pd-row-head tm-row">
<span class="pd-col pd-col-date">\u53f0\u756a\u53f7</span>
<span class="pd-col" style="text-align:left;">\u6a5f\u7a2e</span>
<span class="pd-col pd-col-rate">\u8a55\u4fa1</span>
</div>
"""

TM_HTML_TAIL = """
</div>

<a class="lab-map-link" href="?page=heatmap&from=tomorrow" target="_self">\U0001F5FA \u30d5\u30ed\u30a2\u3067\u898b\u308b</a>

<a class="lab-back" href="?page=home" target="_self">&#8592; BACK</a>

</div>
"""

TM_DETAIL_HTML = """
<div class="rt-wrap">

<div class="rt-head">
<span class="rt-head-label">TOMORROW</span>
<span class="rt-head-no">No.{no}</span>
</div>

<div class="rt-model">{model}</div>

<div class="rt-rate">
<div class="rt-rate-top">
<span class="rt-rate-label">\u4e88\u60f3\u8a55\u4fa1</span>
<span class="rt-rate-value">{rate}</span>
</div>
<div class="rt-rate-reason">{reason}</div>
</div>

<div class="rt-updated">{date} \u306e\u4e88\u60f3</div>

<a class="lab-back" href="?page=tomorrow" target="_self">&#8592; \u4e00\u89a7\u306b\u623b\u308b</a>

</div>
"""


# ==================================
# MOVE（raw_data接続 / setting_estimation.py ベースの新ロジックに接続）
# ==================================
# 本日の raw_data（最新取得分）を analyze_realtime_v2() にそのまま渡す。
# analyze_realtime_v2 は scripts/realtime/realtime_analysis.py に追加した新関数で、
# 内部で core/setting_estimation.py のベイズ推定ロジック（SETTING POSSIBILITY／
# DATA CONFIDENCE／3並び疑いフラグ）を使う。旧来の◎○△評価やスコアは
# 「断定しない」方針のため表示せず、事実（BB／RB／G数・合成確率・設定1〜6
# それぞれの可能性と理論値・DATA CONFIDENCE・隣接状況）のみを見せる。
# 表示は2セクション構成：
#   ・現在の高設定候補（own_score＝設定4〜6合計%が高い順。ただし数値自体は非表示）
#   ・移動おすすめ（priority_score順＝マイジャグラーの3並び疑いを加味した順）
# 一覧では順位／台番号／機種／DATA CONFIDENCE／BB／RB／G数／合成・
# （あれば）3並び疑いの理由を表示し、詳細ページでは設定1〜6の可能性(%)と
# その理論BB/RB確率を全部並べて表示する。

# ==================================
# ぶどう入力（任意 / STEP 追加）
# ==================================
# analyze_machine()はもともとgrape_G（ぶどうを数えたG数）・grape_n（ぶどう回数）を
# 任意引数で受け取れる設計になっている。ここではREALTIME・MOVE詳細画面から
# その値を入力できるようにし、_build_move_pick()の中で該当台だけ
# analyze_machine()を再計算して差し替える（176台の一覧側の取得ロジック自体は
# 変更しない）。
#
# ぶどうはあくまで自分がその場で数えた範囲の任意入力のため、DBには保存せず
# st.session_state（このブラウザセッションの間だけ保持）に持たせる。

GRAPE_STATE_KEY = "grape_inputs"  # st.session_state[GRAPE_STATE_KEY] = {台番号: (grape_G, grape_n)}


def _get_grape_input(machine_no):
    return st.session_state.get(GRAPE_STATE_KEY, {}).get(machine_no)


def _set_grape_input(machine_no, grape_G, grape_n):
    st.session_state.setdefault(GRAPE_STATE_KEY, {})[machine_no] = (grape_G, grape_n)


def _clear_grape_input(machine_no):
    st.session_state.setdefault(GRAPE_STATE_KEY, {}).pop(machine_no, None)


def _apply_grape_override(r, by_id):
    """
    r（analyze_realtime_v2側で作られた分析結果）に対して、
    その台のぶどう入力がsession_stateにあれば、grape_G/grape_nありで
    analyze_machineを再計算し、own_score/narabi_suspicion/priority_scoreも
    合わせて再計算した結果を返す。入力が無ければrをそのまま返す。
    """
    grape = _get_grape_input(r["id"])
    if not grape:
        return r
    grape_G, grape_n = grape

    updated = analyze_machine(r["machine"], r["G"], r["bb"], r["rb"], grape_G, grape_n)
    updated["id"] = r["id"]
    updated["left_id"] = r.get("left_id")
    updated["right_id"] = r.get("right_id")
    updated["grape_G"] = grape_G
    updated["grape_n"] = grape_n

    left = by_id.get(r.get("left_id"))
    right = by_id.get(r.get("right_id"))
    suspicion = check_narabi_suspicion(updated, left, right)
    own_score = get_high_setting_score(updated["setting_possibility"])

    updated["own_score"] = round(own_score, 1)
    updated["narabi_suspicion"] = suspicion
    updated["priority_score"] = round(max(own_score, 50.0) if suspicion else own_score, 1)
    return updated


def render_grape_form(machine_no):
    """REALTIME・MOVE詳細画面の下に表示する、ぶどう入力フォーム。"""
    current = _get_grape_input(machine_no)
    cur_G, cur_n = current if current else (0, 0)

    st.markdown('<div class="rt-updated">ぶどう入力（任意・このブラウザだけで保持）</div>', unsafe_allow_html=True)

    if current:
        cur_prob = cur_G / cur_n if cur_n else None
        prob_label = f"（1/{cur_prob:g}）" if cur_prob else ""
        st.caption(f"現在の入力：ぶどう {cur_G:,}G / {cur_n}回{prob_label}")

    with st.form(f"grape_form_{machine_no}"):
        grape_G = st.number_input("ぶどうを数えたG数", min_value=0, value=int(cur_G), step=100)
        grape_n = st.number_input("ぶどう回数", min_value=0, value=int(cur_n), step=1)
        # st.columnsは狭い画面（スマホ）で縦積みになるため使わない（既存ルール）。
        # ボタンはそのまま縦に並べる。
        submitted = st.form_submit_button("反映")
        cleared = st.form_submit_button("クリア")

    if submitted:
        if grape_G > 0 and grape_n > 0:
            _set_grape_input(machine_no, grape_G, grape_n)
        else:
            _clear_grape_input(machine_no)
        st.rerun()
    if cleared:
        _clear_grape_input(machine_no)
        st.rerun()


def _fmt_int(val):
    return str(int(val)) if pd.notna(val) else "-"


def _fmt_games(val):
    return f"{int(val):,}" if pd.notna(val) else "-"


def _fmt_total(val):
    return f"1/{val:g}" if pd.notna(val) else "-"


def _fetch_today_analysis():
    """
    本日のraw_data最新分を analyze_realtime_v2() で分析する。
    REALTIME（1台）・MOVE（176台一覧）の両方から共通で使う。

    戻り値: (all_results, by_id, updated_lookup, date_label)
        all_results: 176台分の分析結果（priority_score順）
        by_id: {台番号: 分析結果} の辞書（隣接台参照・REALTIME単体取得用）
        updated_lookup: {台番号: 取得日時}
        date_label: 表示用の日付（MM/DD）
    """
    today = datetime.date.today().strftime("%Y-%m-%d")
    date_label = datetime.date.today().strftime("%m/%d")

    rows = fetch_all(
        """
        SELECT r.*
        FROM raw_data r
        INNER JOIN (
            SELECT 台番号, MAX(取得日時) AS max_dt
            FROM raw_data
            WHERE 日付 = ?
            GROUP BY 台番号
        ) latest
        ON r.台番号 = latest.台番号
        AND r.取得日時 = latest.max_dt
        WHERE r.日付 = ?
        """,
        [today, today],
    )

    if not rows:
        return [], {}, {}, date_label

    updated_lookup = {}
    for row in rows:
        row_dict = dict(row)
        no = row_dict.get("台番号")
        if no is not None:
            updated_lookup[int(no)] = row_dict.get("取得日時")

    df = pd.DataFrame([dict(row) for row in rows])
    result = analyze_realtime_v2(df)

    all_results = result["move"]  # build_move_candidates側で既にpriority_score順
    by_id = {r["id"]: r for r in all_results}

    return all_results, by_id, updated_lookup, date_label


def _build_move_pick(r, rank, by_id):
    r = _apply_grape_override(r, by_id)

    left = by_id.get(r.get("left_id"))
    right = by_id.get(r.get("right_id"))
    narabi_note = ""
    if r.get("narabi_suspicion"):
        left_no = left["id"] if left else "-"
        right_no = right["id"] if right else "-"
        narabi_note = (
            f"両隣（No.{left_no}／No.{right_no}）もマイジャグラーで、"
            "データも十分・高設定の可能性も高いため、3並び疑いがあります"
        )

    setting_rows = "".join(
        MV_SETTING_ROW_HTML.format(
            setting=s,
            possibility=r["setting_possibility"][s],
            bb_spec=r["spec"][s]["bb"],
            rb_spec=r["spec"][s]["rb"],
        )
        for s in range(1, 7)
    )

    return {
        "rank": rank,
        "no": str(r["id"]),
        "model": r["machine"] or "-",
        "bb": _fmt_int(r["bb"]),
        "rb": _fmt_int(r["rb"]),
        "games": _fmt_games(r["G"]),
        "total": _fmt_total(r.get("total_prob")),
        "grape": str(int(r["grape_n"])) if r.get("grape_n") else "-",
        "grape_total": _fmt_total(r.get("grape_prob")),
        "confidence": r["data_confidence"],
        "confidence_class": CONFIDENCE_CLASS.get(r["data_confidence"], ""),
        "setting_rows": setting_rows,
        "narabi_note": narabi_note,
        "narabi_html": (
            f'<div class="mv-row-narabi">{narabi_note}</div>' if narabi_note else ""
        ),
        "narabi_detail_html": (
            f'<div class="rt-rate-reason">{narabi_note}</div>' if narabi_note else ""
        ),
    }


def load_move_picks():
    # STEP改：台単体データ（own_score順）は移動おすすめ（priority_score順）と
    # ほぼ同じ出力になるため廃止し、移動おすすめのみを返す。
    all_results, by_id, _updated_lookup, date_label = _fetch_today_analysis()
    if not all_results:
        return [], date_label

    move_picks = [
        _build_move_pick(r, i + 1, by_id) for i, r in enumerate(all_results)
    ]
    return move_picks, date_label


def load_realtime_machine_v2(machine_no):
    all_results, by_id, updated_lookup, _date_label = _fetch_today_analysis()
    r = by_id.get(machine_no)
    if r is None:
        return None
    pick = _build_move_pick(r, None, by_id)
    pick["updated"] = updated_lookup.get(machine_no) or "-"
    return pick


MV_ROW_HTML = """
<a class="mv-card" href="?page=move&no={no}" target="_self">
<div class="mv-row-top">
<span class="pd-col pd-col-rank">{rank}位</span>
<span class="pd-col pd-col-date">No.{no}</span>
<span class="pd-col" style="text-align:left;">{model}</span>
<span class="pd-col pd-col-rate {confidence_class}">{confidence}</span>
</div>
<div class="mv-row-stats">
<span>BB {bb}</span>
<span>RB {rb}</span>
<span>G数 {games}</span>
<span>合成 {total}</span>
</div>
{narabi_html}
</a>
"""


def build_move_section_html(head_html, tail_html, picks):
    if not picks:
        return head_html + '<div class="pd-row">該当なし</div>' + tail_html
    rows = "".join(
        MV_ROW_HTML.format(
            rank=p["rank"], no=p["no"], model=p["model"],
            confidence=p["confidence"], confidence_class=p["confidence_class"],
            bb=p["bb"], rb=p["rb"], games=p["games"], total=p["total"],
            narabi_html=p["narabi_html"],
        )
        for p in picks
    )
    return head_html + rows + tail_html


MV_PAGE_SIZE = 5


def build_move_nav_html(param_name, current_page, total_items, other_param_name=None, other_page=None):
    total_pages = max(1, (total_items + MV_PAGE_SIZE - 1) // MV_PAGE_SIZE)
    if total_pages <= 1:
        return ""

    other_qs = f"&{other_param_name}={other_page}" if other_param_name else ""

    if current_page > 0:
        prev_btn = (
            f'<a class="pd-nav-btn" href="?page=move&{param_name}={current_page - 1}'
            f'{other_qs}" target="_self">← 前の5件</a>'
        )
    else:
        prev_btn = '<span class="pd-nav-btn pd-nav-btn-disabled">← 前の5件</span>'

    if current_page + 1 < total_pages:
        next_btn = (
            f'<a class="pd-nav-btn" href="?page=move&{param_name}={current_page + 1}'
            f'{other_qs}" target="_self">次の5件 →</a>'
        )
    else:
        next_btn = '<span class="pd-nav-btn pd-nav-btn-disabled">次の5件 →</span>'

    return f'<div class="pd-nav">{prev_btn}{next_btn}</div>'


MV_HTML_HEAD = """
<div class="pd-wrap">

<div class="pd-head">
<span class="pd-head-label">MOVE</span>
<span class="pd-head-no">{date}</span>
</div>
"""

MV_SECTION_MOVE_HEAD = """
<div class="pd-model">移動おすすめ（隣接状況を含めた優先順）</div>

<div class="pd-table">
"""

MV_SECTION_MOVE_TAIL = """
</div>
"""

MV_HTML_TAIL = """
<a class="lab-map-link" href="?page=heatmap&from=move&mp={mp}" target="_self">🗺 フロアで見る</a>

<a class="lab-back" href="?page=home" target="_self">&#8592; BACK</a>

</div>
"""

MV_SETTING_ROW_HTML = """
<div class="mv-setting-row">
<span>設定{setting}</span>
<span>{possibility}%</span>
<span>1/{bb_spec:g}</span>
<span>1/{rb_spec:g}</span>
</div>
"""

MV_DETAIL_HTML = """
<div class="rt-wrap">

<div class="rt-head">
<span class="rt-head-label">MOVE</span>
<span class="rt-head-no">No.{no}</span>
</div>

<div class="rt-model">{model}</div>

<div class="rt-grid">
<div class="rt-cell"><span class="rt-cell-label">BB</span><span class="rt-cell-value">{bb}</span></div>
<div class="rt-cell"><span class="rt-cell-label">RB</span><span class="rt-cell-value">{rb}</span></div>
<div class="rt-cell"><span class="rt-cell-label">G数</span><span class="rt-cell-value">{games}</span></div>
<div class="rt-cell"><span class="rt-cell-label">合成</span><span class="rt-cell-value">{total}</span></div>
<div class="rt-cell"><span class="rt-cell-label">ぶどう</span><span class="rt-cell-value">{grape}</span></div>
<div class="rt-cell"><span class="rt-cell-label">ぶどう確率</span><span class="rt-cell-value">{grape_total}</span></div>
</div>

<div class="mv-setting-table">
<div class="mv-setting-row mv-setting-row-head">
<span>設定</span><span>可能性</span><span>BB理論値</span><span>RB理論値</span>
</div>
{setting_rows}
</div>

<div class="rt-rate">
<div class="rt-rate-top">
<span class="rt-rate-label">DATA CONFIDENCE</span>
<span class="rt-rate-value {confidence_class}">{confidence}</span>
</div>
{narabi_detail_html}
</div>

<div class="rt-updated">{date} 時点</div>

<a class="lab-back" href="?page=move" target="_self">&#8592; 一覧に戻る</a>

</div>
"""




# ==================================
# HEATMAP（v8の台マップ座標を移植 / STEP 3-5改）
# ==================================
# 座標データ（machine_rows）はapp_ui_v8.py（1810〜2009行付近）から
# そのままコピーしたもの。値は一切変更していない。
# v8では新規タブ遷移（target="_blank"）だったが、v9はページ内遷移方式のため、
# タップしたら同じタブでREALTIME（その台番号）に直接移動するよう変更した
# （components.html はiframeのため、遷移には target="_top" ＋ 絶対URLが必要）。
# 評価（◎○△）による色分けは今回は行わず、座標移植とタップ遷移のみ。

HM_FROM_LABEL = {
    "realtime": "REALTIME",
    "tomorrow": "TOMORROW",
    "move": "MOVE",
    "past": "PAST DATA",
}


machine_rows = [

    # ================================================
    # 上段
    # ================================================

    {
        "machines": list(range(901, 909)),
        "x": 37.9,
        "y": 22.8,
        "width": 20.1,
        "height": 5.4,
    },

    {
        "machines": list(range(936, 928, -1)),
        "x": 37.9,
        "y": 28.2,
        "width": 20.1,
        "height": 5.4,
    },

    {
        "machines": list(range(909, 919)),
        "x": 60.0,
        "y": 22.8,
        "width": 25.3,
        "height": 5.4,
    },

    {
        "machines": list(range(928, 918, -1)),
        "x": 60.0,
        "y": 28.2,
        "width": 25.3,
        "height": 5.4,
    },


    # ================================================
    # ② 937～983 / 949～968
    # ================================================

    {
        "machines": list(range(937, 949)),
        "x": 27.8,
        "y": 35.5,
        "width": 30.2,
        "height": 5.4,
    },

    {
        "machines": list(range(983, 968, -1)),
        "x": 20.3,
        "y": 40.9,
        "width": 37.7,
        "height": 5.4,
    },

    {
        "machines": list(range(949, 959)),
        "x": 60.0,
        "y": 35.5,
        "width": 25.3,
        "height": 5.4,
    },

    {
        "machines": list(range(968, 958, -1)),
        "x": 60.0,
        "y": 40.9,
        "width": 25.3,
        "height": 5.4,
    },


    # ================================================
    # ③ 984～1023 / 994～1013
    # ================================================

    {
        "machines": list(range(984, 994)),
        "x": 32.7,
        "y": 48.2,
        "width": 25.3,
        "height": 5.4,
    },

    {
        "machines": list(range(1023, 1013, -1)),
        "x": 32.7,
        "y": 53.6,
        "width": 25.3,
        "height": 5.4,
    },

    {
        "machines": list(range(994, 1004)),
        "x": 60.0,
        "y": 48.2,
        "width": 25.3,
        "height": 5.4,
    },

    {
        "machines": list(range(1013, 1003, -1)),
        "x": 60.0,
        "y": 53.6,
        "width": 25.3,
        "height": 5.4,
    },


    # ================================================
    # ④ 1024～1070 / 1039～1058
    # ================================================

    {
        "machines": list(range(1024, 1039)),
        "x": 20.3,
        "y": 60.9,
        "width": 37.7,
        "height": 5.4,
    },

    {
        "machines": list(range(1070, 1058, -1)),
        "x": 27.8,
        "y": 66.3,
        "width": 30.2,
        "height": 5.4,
    },

    {
        "machines": list(range(1039, 1049)),
        "x": 60.0,
        "y": 60.9,
        "width": 25.3,
        "height": 5.4,
    },

    {
        "machines": list(range(1058, 1048, -1)),
        "x": 60.0,
        "y": 66.3,
        "width": 25.3,
        "height": 5.4,
    },


    # ================================================
    # ⑤ 1071～1106 / 1079～1098
    # ================================================

    {
        "machines": list(range(1071, 1079)),
        "x": 37.9,
        "y": 73.8,
        "width": 20.1,
        "height": 5.4,
    },

    {
        "machines": list(range(1106, 1098, -1)),
        "x": 37.9,
        "y": 79.2,
        "width": 20.1,
        "height": 5.4,
    },

    {
        "machines": list(range(1079, 1089)),
        "x": 60.0,
        "y": 73.8,
        "width": 25.3,
        "height": 5.4,
    },

    {
        "machines": list(range(1098, 1088, -1)),
        "x": 60.0,
        "y": 79.2,
        "width": 25.3,
        "height": 5.4,
    },
]


HM_RATE_COLOR = {
    "◎": "#ff3c3c",
    "○": "#ffaa28",
    "△": "#fff9a0",
}

HM_TOMORROW_COLOR = "#4dd9ff"


def get_today_machine_evaluations():
    # REALTIME/MOVEと同じ考え方：本日のraw_data最新分を評価する。
    # prepare_realtime_data / calculate_current_evaluation は既存・未変更。
    today = datetime.date.today().strftime("%Y-%m-%d")

    rows = fetch_all(
        """
        SELECT r.*
        FROM raw_data r
        INNER JOIN (
            SELECT 台番号, MAX(取得日時) AS max_dt
            FROM raw_data
            WHERE 日付 = ?
            GROUP BY 台番号
        ) latest
        ON r.台番号 = latest.台番号
        AND r.取得日時 = latest.max_dt
        WHERE r.日付 = ?
        """,
        [today, today],
    )
    if not rows:
        return {}

    df = pd.DataFrame([dict(row) for row in rows])
    df = prepare_realtime_data(df)

    result = {}
    for _, row in df.iterrows():
        no = row.get("台番号数値")
        if pd.notna(no):
            result[int(no)] = calculate_current_evaluation(row)
    return result


def get_daily_machine_evaluations(date):
    # daily_data（確定済み過去データ）から、指定日の台番号ごとの評価を取得する。
    if not date:
        return {}
    rows = fetch_all(
        """
        SELECT 台番号, 評価
        FROM daily_data
        WHERE 日付 = ?
        """,
        [date],
    )
    return {
        int(r["台番号"]): r["評価"]
        for r in rows
        if r["評価"]
    }


def get_adjacent_daily_date(date, direction):
    # daily_dataに実際にデータがある、指定日の前後の日付を1件取得する。
    if direction == "prev":
        row = fetch_one(
            "SELECT MAX(日付) AS d FROM daily_data WHERE 日付 < ?",
            [date],
        )
    else:
        row = fetch_one(
            "SELECT MIN(日付) AS d FROM daily_data WHERE 日付 > ?",
            [date],
        )
    return row["d"] if row and row["d"] else None


def get_tomorrow_machine_colors():
    # TOMORROWに表示されている予想上位5台だけを、単一色（水色）で塗る。
    # get_prediction_top はanalysis/views.pyの既存関数をそのまま利用（ロジック変更なし）。
    df = get_prediction_top(limit=5)
    if df.empty:
        return {}
    result = {}
    for _, row in df.iterrows():
        no = row.get("台番号")
        if pd.notna(no):
            result[int(no)] = HM_TOMORROW_COLOR
    return result


def get_move_map_colors(mp):
    # MOVE「移動おすすめ」セクションで、今表示中のページ（5台）だけを水色で塗る。
    move_picks, _mv_date = load_move_picks()
    if not move_picks:
        return {}
    page_picks = move_picks[mp * MV_PAGE_SIZE: (mp + 1) * MV_PAGE_SIZE]
    return {int(p["no"]): HM_TOMORROW_COLOR for p in page_picks}


def get_high_setting56_colors(threshold=50.0):
    # REALTIME用：設定5・6の可能性の合計がthreshold(%)を超える台だけを水色で塗る。
    # 3並び疑いフラグと同じ50%を既定値に使用。
    all_results, _by_id, _updated_lookup, _date_label = _fetch_today_analysis()
    if not all_results:
        return {}
    result = {}
    for r in all_results:
        possibility = r["setting_possibility"]
        score_56 = possibility[5] + possibility[6]
        if score_56 > threshold:
            result[r["id"]] = HM_TOMORROW_COLOR
    return result


def build_heatmap_html(seat_colors=None, legend_items=None, link_page="realtime"):
    try:
        _current_url = st.context.url
        _parts = urlsplit(_current_url)
        app_url = urlunsplit((_parts.scheme, _parts.netloc, _parts.path, "", ""))
    except Exception:
        app_url = ""

    seat_colors = seat_colors or {}

    legend_html = ""
    if legend_items:
        items_html = "".join(
            f'<span><i style="background:{color}"></i>{label}</span>'
            for label, color in legend_items
        )
        legend_html = f'<div class="hm-legend">{items_html}</div>'

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport"
      content="width=device-width,
               initial-scale=1.0,
               maximum-scale=1.0,
               user-scalable=yes">
<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    padding: 0;
    background: #05090a;
    font-family: "Segoe UI", "Meiryo", sans-serif;
}}

.map-viewport {{
    position: relative;
    width: 100%;
    aspect-ratio: 1024 / 724;
    overflow: hidden;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(65,255,175,.12);
    border-radius: 10px;
}}

.map {{
    position: absolute;
    inset: 0;
    transform-origin: 0% 0%;
    transition: transform .25s ease;
    z-index: 32;
    pointer-events: none;
}}

.quad-overlay {{
    position: absolute;
    inset: 0;
    display: grid;
    grid-template-columns: 59% 41%;
    grid-template-rows: 60% 40%;
    z-index: 30;
}}

.quad {{
    border: 1px dashed rgba(65,255,175,.35);
    cursor: zoom-in;
}}

.quad:active {{
    background: rgba(65,255,175,.1);
}}

.zoom-back {{
    position: absolute;
    top: 8px;
    left: 8px;
    z-index: 40;
    padding: 7px 14px;
    border: 1px solid rgba(65,255,175,.5);
    border-radius: 8px;
    background: rgba(4,18,15,.92);
    color: #6dffb8;
    font-size: 11px;
    font-weight: 800;
    cursor: pointer;
    display: none;
}}

.machine {{
    position: absolute;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(4, 18, 15, 0.94);
    border: 1px solid rgba(74, 255, 178, 0.55);
    border-radius: 2px;
    color: #d9ffec;
    font-weight: 800;
    font-size: 6px;
    letter-spacing: -0.4px;
    padding: 0;
    box-shadow: 0 0 6px rgba(65,255,175,.12);
    line-height: 1;
    overflow: hidden;
    white-space: nowrap;
    z-index: 35;
    cursor: pointer;
    pointer-events: auto;
    transition: background .14s ease, border-color .14s ease, box-shadow .14s ease;
}}

.machine:hover {{
    background: rgba(27, 83, 59, 0.98);
    color: #ffffff;
    border-color: #78ffc0;
    box-shadow: 0 0 14px rgba(65,255,175,.55);
    z-index: 36;
}}

.hm-legend {{
    position: absolute;
    top: 8px;
    left: 8px;
    z-index: 25;
    display: flex;
    gap: 8px;
    padding: 4px 8px;
    border: 1px solid rgba(65,255,175,.25);
    border-radius: 6px;
    background: rgba(4,18,15,.85);
    pointer-events: none;
}}

.hm-legend span {{
    display: flex;
    align-items: center;
    gap: 3px;
    font-size: 10px;
    font-weight: 800;
    color: #cdeedd;
}}

.hm-legend i {{
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 2px;
}}

</style>
</head>
<body>
<div class="map-viewport" id="map-viewport">
{legend_html}
<div class="map" id="map">
"""

    for row_data in machine_rows:
        machines = row_data["machines"]
        x = row_data["x"]
        y = row_data["y"]
        width = row_data["width"]
        height = row_data["height"]

        if row_data.get("vertical", False):
            machine_height = height / len(machines)
            for i, machine in enumerate(machines):
                top = y + i * machine_height
                seat_color = seat_colors.get(machine)
                color_style = (
                    f"background: {seat_color}26; border-color: {seat_color};"
                    if seat_color else ""
                )
                html += f"""
                <a class="machine"
                    aria-label="MACHINE {str(machine).zfill(4)} を選択"
                    href="{app_url}?page={link_page}&no={machine}"
                    target="_top"
                    title="MACHINE {str(machine).zfill(4)} / クリックして選択"
                    style="
                        left: {x}%;
                        top: {top}%;
                        width: {width}%;
                        height: {machine_height}%;
                        {color_style}
                    "
                >
                    {machine}
                </a>
                """
        else:
            machine_width = width / len(machines)
            for i, machine in enumerate(machines):
                left = x + i * machine_width
                seat_color = seat_colors.get(machine)
                color_style = (
                    f"background: {seat_color}26; border-color: {seat_color};"
                    if seat_color else ""
                )
                html += f"""
                <a class="machine"
                    aria-label="MACHINE {str(machine).zfill(4)} を選択"
                    href="{app_url}?page={link_page}&no={machine}"
                    target="_top"
                    title="MACHINE {str(machine).zfill(4)} / クリックして選択"
                    style="
                        left: {left}%;
                        top: {y}%;
                        width: {machine_width}%;
                        height: {height}%;
                        {color_style}
                    "
                >
                    {machine}
                </a>
                """

    html += """
</div>
<div class="quad-overlay" id="quad-overlay">
<div class="quad" data-origin="31.70% 34.65%" data-scale="2.4570"></div>
<div class="quad" data-origin="87.25% 35.03%" data-scale="2.5510"></div>
<div class="quad" data-origin="31.70% 88.36%" data-scale="2.4570"></div>
<div class="quad" data-origin="81.59% 81.73%" data-scale="3.5336"></div>
</div>
<button class="zoom-back" id="zoom-back">&#8592; \u5168\u4f53\u8868\u793a\u306b\u623b\u308b</button>
</div>
<script>
(function() {
    var mapEl = document.getElementById('map');
    var overlay = document.getElementById('quad-overlay');
    var backBtn = document.getElementById('zoom-back');

    Array.prototype.forEach.call(
        overlay.querySelectorAll('.quad'),
        function(q) {
            q.addEventListener('click', function() {
                var scale = q.getAttribute('data-scale') || '2';
                mapEl.style.transformOrigin = q.getAttribute('data-origin');
                mapEl.style.transform = 'scale(' + scale + ')';
                overlay.style.display = 'none';
                backBtn.style.display = 'block';
            });
        }
    );

    backBtn.addEventListener('click', function() {
        mapEl.style.transform = 'scale(1)';
        overlay.style.display = 'grid';
        backBtn.style.display = 'none';
    });

    Array.prototype.forEach.call(
        document.querySelectorAll('.machine'),
        function(m) {
            m.addEventListener('click', function(e) {
                e.preventDefault();
                var url = m.getAttribute('href');
                try {
                    var topLink = window.parent.document.getElementById('hm-nav-link');
                    if (topLink) {
                        topLink.href = url;
                        topLink.click();
                        return;
                    }
                } catch (err) {}
                window.open(url, '_top');
            });
        }
    );
})();
</script>
</body>
</html>
"""
    return html


# ==================================
# 表示
# ==================================

if page == "realtime":
    try:
        machine_no = int(st.query_params.get("no", str(DEFAULT_MACHINE_NO)))
    except ValueError:
        machine_no = DEFAULT_MACHINE_NO

    all_machines = get_all_machines()
    render_machine_picker("mc_form_realtime", machine_no, all_machines)

    machine = load_realtime_machine_v2(machine_no)
    if machine:
        st.markdown(RT_HTML.format(**machine), unsafe_allow_html=True)
        render_grape_form(machine_no)
    else:
        st.markdown(
            SOON_HTML.format(en="REALTIME", jp=f"No.{machine_no} \u306e\u30c7\u30fc\u30bf\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093"),
            unsafe_allow_html=True,
        )
elif page == "past":
    try:
        machine_no = int(st.query_params.get("no", str(DEFAULT_MACHINE_NO)))
    except ValueError:
        machine_no = DEFAULT_MACHINE_NO
    try:
        week = max(int(st.query_params.get("week", "0")), 0)
    except ValueError:
        week = 0

    all_machines = get_all_machines()
    render_machine_picker("mc_form_past", machine_no, all_machines, reset_week=True)

    days, total, model = load_past_week(machine_no, week)
    if not days:
        st.markdown(
            SOON_HTML.format(en="PAST DATA", jp=f"No.{machine_no} \u306e\u5c65\u6b74\u304c\u3042\u308a\u307e\u305b\u3093"),
            unsafe_allow_html=True,
        )
    else:
        rows = "".join(
            PD_ROW_HTML.format(
                date=d["date"], bb=d["bb"], rb=d["rb"], games=d["games"],
                total=d["total"], rate=d["rate"],
                rate_class=PD_RATE_CLASS.get(d["rate"], ""),
            )
            for d in days
        )
        next_btn = (
            PD_NAV_NEXT_DISABLED if week == 0
            else PD_NAV_NEXT_ACTIVE.format(no=machine_no, next_week=week - 1)
        )
        prev_btn = (
            PD_NAV_PREV_DISABLED if (week + 1) * 7 >= total
            else PD_NAV_PREV_ACTIVE.format(no=machine_no, prev_week=week + 1)
        )
        nav = PD_NAV_HTML.format(prev_btn=prev_btn, next_btn=next_btn)
        map_link = PD_MAP_LINK_HTML.format(date_iso=days[0].get("date_iso", ""))
        pd_html = (
            PD_HTML_HEAD.format(
                no=machine_no, model=model or "-",
                range_start=days[-1]["date"], range_end=days[0]["date"],
            )
            + rows + nav + map_link + PD_HTML_TAIL
        )
        st.markdown(pd_html, unsafe_allow_html=True)
elif page == "tomorrow":
    tm_picks, tm_date = load_tomorrow_picks()
    if not tm_picks:
        st.markdown(
            SOON_HTML.format(en="TOMORROW", jp="\u4e88\u6e2c\u30c7\u30fc\u30bf\u304c\u3042\u308a\u307e\u305b\u3093"),
            unsafe_allow_html=True,
        )
    else:
        no = st.query_params.get("no")
        pick = next((p for p in tm_picks if p["no"] == no), None)
        if pick:
            st.markdown(
                TM_DETAIL_HTML.format(date=tm_date or "-", **pick),
                unsafe_allow_html=True,
            )
        else:
            rows = "".join(
                TM_ROW_HTML.format(
                    no=p["no"], model=p["model"], rate=p["rate"],
                    rate_class=PD_RATE_CLASS.get(p["rate"], ""),
                )
                for p in tm_picks
            )
            tm_html = (
                TM_HTML_HEAD.format(date=tm_date or "-") + rows + TM_HTML_TAIL
            )
            st.markdown(tm_html, unsafe_allow_html=True)
elif page == "move":
    move_picks, mv_date = load_move_picks()
    if not move_picks:
        st.markdown(
            SOON_HTML.format(en="MOVE", jp="移動候補データがありません"),
            unsafe_allow_html=True,
        )
    else:
        no = st.query_params.get("no")
        pick = next((p for p in move_picks if p["no"] == no), None)
        if pick:
            st.markdown(
                MV_DETAIL_HTML.format(date=mv_date or "-", **pick),
                unsafe_allow_html=True,
            )
            render_grape_form(int(pick["no"]))
        else:
            try:
                mp = max(int(st.query_params.get("mp", "0")), 0)
            except ValueError:
                mp = 0

            move_page_picks = move_picks[mp * MV_PAGE_SIZE: (mp + 1) * MV_PAGE_SIZE]

            move_section = build_move_section_html(
                MV_SECTION_MOVE_HEAD, MV_SECTION_MOVE_TAIL, move_page_picks
            )
            move_nav = build_move_nav_html("mp", mp, len(move_picks))

            mv_html = (
                MV_HTML_HEAD.format(date=mv_date or "-")
                + move_section
                + move_nav
                + MV_HTML_TAIL.format(mp=mp)
            )
            st.markdown(mv_html, unsafe_allow_html=True)
elif page == "heatmap":
    src = st.query_params.get("from", "home")
    back_to = src if src in HM_FROM_LABEL else "home"

    HM_LEGEND_TODAY = [("◎", HM_RATE_COLOR["◎"]), ("○", HM_RATE_COLOR["○"]), ("△", HM_RATE_COLOR["△"])]

    if src == "past":
        hm_date = st.query_params.get("date") or get_previous_date()
        raw_evaluations = get_daily_machine_evaluations(hm_date)
        seat_colors = {
            no: HM_RATE_COLOR.get(rate)
            for no, rate in raw_evaluations.items()
            if HM_RATE_COLOR.get(rate)
        }
        legend_items = HM_LEGEND_TODAY
        link_page = "past"
        date_label = hm_date or "-"
        tap_hint = "過去データ（週表示）"
        prev_date = get_adjacent_daily_date(hm_date, "prev") if hm_date else None
        next_date = get_adjacent_daily_date(hm_date, "next") if hm_date else None
        prev_btn = (
            f'<a class="pd-nav-btn" href="?page=heatmap&from=past&date={prev_date}" '
            f'target="_self">&#8592; \u524d\u65e5</a>'
            if prev_date else
            '<span class="pd-nav-btn pd-nav-btn-disabled">&#8592; \u524d\u65e5</span>'
        )
        next_btn = (
            f'<a class="pd-nav-btn" href="?page=heatmap&from=past&date={next_date}" '
            f'target="_self">\u7fcc\u65e5 &#8594;</a>'
            if next_date else
            '<span class="pd-nav-btn pd-nav-btn-disabled">\u7fcc\u65e5 &#8594;</span>'
        )
        nav_html = f'<div class="pd-nav">{prev_btn}{next_btn}</div>'
    elif src == "tomorrow":
        seat_colors = get_tomorrow_machine_colors()
        legend_items = [("\u4e88\u60f3\u53f0", HM_TOMORROW_COLOR)]
        link_page = "tomorrow"
        _pred_date = get_latest_prediction_date()
        date_label = _pred_date or "\u4e88\u60f3\u30c7\u30fc\u30bf\u306a\u3057"
        tap_hint = "TOMORROWの理由詳細"
        nav_html = ""
    elif src == "move":
        try:
            mp = max(int(st.query_params.get("mp", "0")), 0)
        except ValueError:
            mp = 0
        seat_colors = get_move_map_colors(mp)
        legend_items = [("\u79fb\u52d5\u304a\u3059\u3059\u3081", HM_TOMORROW_COLOR)]
        link_page = "move"
        date_label = "\u672c\u65e5"
        tap_hint = "MOVEの詳細"
        nav_html = ""
    else:
        seat_colors = get_high_setting56_colors()
        legend_items = [("\u8a2d\u5b9a5\u30fb6\u306e\u53ef\u80fd\u6027\u9ad8", HM_TOMORROW_COLOR)]
        link_page = "realtime"
        date_label = "\u672c\u65e5"
        tap_hint = "REALTIME"
        nav_html = ""

    st.markdown(
        f'<div class="pd-wrap">'
        f'<div class="pd-head">'
        f'<span class="pd-head-label">HEATMAP</span>'
        f'<span class="pd-head-no">{date_label}</span>'
        f'</div>'
        f'<div class="pd-model">MACHINE MAP / 台マップ（タップすると{tap_hint}に移動）</div>'
        f'{nav_html}'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<a id="hm-nav-link" href="#" style="display:none;"></a>',
        unsafe_allow_html=True,
    )
    components.html(
        build_heatmap_html(seat_colors, legend_items, link_page),
        height=760, scrolling=False,
    )
    st.markdown(
        f'<div class="pd-wrap">'
        f'<a class="lab-back" href="?page={back_to}" target="_self">&#8592; 戻る</a>'
        f'</div>',
        unsafe_allow_html=True,
    )
elif page in MODULES:
    en, jp = MODULES[page]
    st.markdown(SOON_HTML.format(en=en, jp=jp), unsafe_allow_html=True)
else:
    st.markdown(
        HOME_HTML.format(store=STORE_NAME, updated=UPDATED_AT),
        unsafe_allow_html=True,
    )
