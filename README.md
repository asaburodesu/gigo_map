# GiGO設置店舗マップ

## このマップについて
作成者:[asaburodesu](https://twitter.com/asaburodesu)

## 更新頻度
毎日 5:30頃更新が入ります。

## ローカル開発

### 必要なもの
- Node.js 22
- Python 3（店舗データを自分でスクレイピングする場合のみ）

### 起動手順
```sh
npm ci              # 依存パッケージのインストール
npm run fetch-data  # 公開中の data.json を public/ に取得
npm start           # http://localhost:3000 で起動
```

`npm start` / `npm run build` は `config.yml` から `src/config.json` と `.env` を生成します。

### 店舗データをスクレイピングで作る場合
CI と同じく `gigo_get.py` で `data.json` を生成できます（全店舗の詳細ページを巡回するため時間がかかります）。
```sh
python -m venv .venv
.venv\Scripts\activate          # macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
python gigo_get.py
move data.json public\          # macOS / Linux: mv data.json public/
```

