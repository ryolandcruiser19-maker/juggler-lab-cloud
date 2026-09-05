# ジャグラーラボ クラウド化スターター

## 現段階
- Streamlit WebアプリをDockerで起動
- PlaywrightはクラウドではChromiumを直接起動
- ローカル環境では既存のWindows Chrome/CDP方式を維持
- SQLite `database/juggler.db` を同梱

## Railway側で必要な設定
Web Service:
- Dockerfileを使用
- `CLOUD_MODE=1`
- Volumeを `/app/database` にマウント
- Networking → Generate Domain

Cron Job:
- 同じコードから別Serviceを作成
- Start Command: `python scripts/run_daily.py`
- `CLOUD_MODE=1`
- Web Serviceと同じVolumeを `/app/database` にマウント
- CronはUTC基準

## 注意
P's CUBE取得がクラウドのヘッドレスChromiumでも成功するかは、実環境で確認が必要です。
Turnstile等が出た場合は、取得方式を別途調整します。

また、現在の `app_ui_v8.py` が参照する5Fマップ画像
`S9294_himawari_tower_5F-3-1-1024x724.jpg`
は今回のアップロードに含まれていないため、最終デプロイ前に追加が必要です。
