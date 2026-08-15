---
name: pandas-data-optimizer
description: 高速かつメモリ効率の良い pandas 実装パターン集。pandas でループ・apply・遅い処理・メモリ不足・dtype 起因のパフォーマンス問題を指摘されたとき、または大きめのデータ（数万行以上）を扱う前処理・特徴量生成を書く前に参照する。
---

# Pandas Data Optimizer

LLM は学習データの偏りから、`iterrows`、`apply(axis=1)`、`for` ループでのセル代入など**遅い古いイディオム**を書きがち。本スキルは、それらを**ベクトル化・適切な dtype・効率的な集約**に置き換えるためのチェックリストとレシピを提供する。

**いつ使うか**
- ユーザーから「遅い」「メモリが多い」「pandas の書き方を改善して」と指摘されたとき
- 数万行以上のデータに対する前処理・特徴量生成コードを書く・レビューするとき
- ログ系・トランザクション系など行数の多いテーブルを集計するとき

**基本方針（優先順位順）**
1. **ベクトル化**: ループ・`apply(axis=1)` を Series/DataFrame 演算・`numpy` 関数に置き換える
2. **dtype 最適化**: `category` / `int8`/`int16`/`int32` / `float32` を活用してメモリと演算速度を改善
3. **I/O 最適化**: `read_csv` 時点で `dtype` / `usecols` / `parse_dates` を指定し、後から変換しない
4. **集約・結合の高速化**: `groupby` の `observed=True`、`merge` 前の sort/index 化
5. **どうしても遅ければ Polars / DuckDB / Dask** を検討

---

## 1. ベクトル化（最重要）

### ❌ 遅い: 行ごとループ・`apply(axis=1)`

```python
# iterrows — 最悪レベルに遅い
for i, row in df.iterrows():
    df.at[i, "total"] = row["a"] + row["b"]

# apply(axis=1) — iterrows よりは速いが Python ループに変わりはない
df["total"] = df.apply(lambda r: r["a"] + r["b"], axis=1)
```

### ✅ 速い: 列演算 / `numpy` / `np.where`

```python
# 列演算
df["total"] = df["a"] + df["b"]

# 条件分岐は np.where / np.select
df["flag"] = np.where(df["x"] > 0, 1, 0)
df["bucket"] = np.select(
    [df["x"] < 0, df["x"] == 0, df["x"] > 0],
    ["neg", "zero", "pos"],
    default="unknown",
)
```

### 文字列も `.str` でベクトル化

```python
# ❌ apply で str 操作
df["upper"] = df["name"].apply(lambda s: s.upper())

# ✅ .str アクセサ
df["upper"] = df["name"].str.upper()
df["has_keyword"] = df["text"].str.contains("keyword", na=False)
```

### 日時も `.dt` でベクトル化

```python
# ❌
df["year"] = df["timestamp"].apply(lambda d: d.year)

# ✅
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["year"] = df["timestamp"].dt.year
df["hour"] = df["timestamp"].dt.hour
df["dow"]  = df["timestamp"].dt.dayofweek
```

### `apply` を使ってよい場面
- 戻り値が複数列 (`result_type="expand"`) で、ベクトル化が極端に複雑になるケース
- グループ単位の関数 (`groupby().apply()`)。それでも `agg` / `transform` で書ければそちらが速い

---

## 2. dtype 最適化（メモリと速度の両方に効く）

### カテゴリ型: 繰り返しの多い文字列カラムは積極的に `category` 化

ユニーク値の少ない文字列（性別、地域、デバイス種別、カテゴリ名など）は `category` にするとメモリが激減し、`groupby` も速くなる。目安は「ユニーク数 / 行数 < 0.5」程度。

```python
cat_cols = ["col_a", "col_b", "col_c"]  # 低カーディナリティな文字列列
for c in cat_cols:
    df[c] = df[c].astype("category")
```

**注意**: `category` カラムを `groupby` するときは `observed=True` を付ける（未使用カテゴリの空グループが作られて遅くなるのを防ぐ）。

```python
df.groupby("category_col", observed=True)["value"].mean()
```

### 数値型ダウンキャスト

`int64` / `float64` は多くの場面で過剰。

```python
# 整数: 値域に応じて最小型へ
df["int_col"] = pd.to_numeric(df["int_col"], downcast="integer")   # int8 等

# 浮動小数: 精度許せば float32
df["float_col"] = pd.to_numeric(df["float_col"], downcast="float")
```

### 欠損のある整数列は `Int64`（nullable integer）

`NaN` が混ざる整数列は通常 `float64` に昇格してしまう。明示的に nullable integer を使う:

```python
df["int_with_na"] = df["int_with_na"].astype("Int64")  # Int8/Int16/Int32 もある
```

### dtype を確認するイディオム

```python
df.memory_usage(deep=True).sum() / 1024**2   # MB
df.dtypes
df.info(memory_usage="deep")
```

---

## 3. I/O 最適化: `read_csv` 時点で型を決め切る

後から `astype` するより、読み込み時に型を渡すほうが速くてメモリも食わない。

```python
dtype_map = {
    "id":         "string",
    "category_a": "category",
    "category_b": "category",
    "amount":     "float32",
    "count":      "Int32",
}

df = pd.read_csv(
    "data/raw/data.csv",
    dtype=dtype_map,
    parse_dates=["timestamp"],
    usecols=list(dtype_map.keys()) + ["timestamp"],  # 不要列を読まない
)
```

巨大ファイルなら `chunksize=` で逐次集計するか、**Parquet** に一度変換してから読む（型情報が保存され桁違いに速い）:

```python
df.to_parquet("data/processed/data.parquet")
df = pd.read_parquet("data/processed/data.parquet")
```

---

## 4. 集約・結合の高速化

### `groupby` で `transform` / `agg` を使い分ける

```python
# グループ単位の集計値を行に付与したい（行数を保つ）
df["group_total"] = df.groupby("group_key")["value"].transform("sum")

# グループ単位の集計テーブルを作る
agg_df = df.groupby("group_key", observed=True).agg(
    total=("value", "sum"),
    n_rows=("value", "size"),
    n_unique=("item_id", "nunique"),
    last_time=("timestamp", "max"),
)
```

### `merge` は事前にキーをソート＆同一 dtype に揃える

- 結合キーの dtype が左右で違うとオブジェクト経由でフォールバックし激遅
- 何度も同じキーで結合するなら `set_index` → `join` のほうが速い

```python
# 同 dtype に揃える
left["key"]  = left["key"].astype("string")
right["key"] = right["key"].astype("string")

merged = left.merge(right, on="key", how="left")
```

### 連結は `concat` 1回でまとめる

```python
# ❌ ループ内で append/concat — O(N^2)
out = pd.DataFrame()
for chunk in chunks:
    out = pd.concat([out, chunk])

# ✅ リストに溜めて最後に 1 回
out = pd.concat(list_of_chunks, ignore_index=True)
```

---

## 5. その他の落とし穴

### Chained indexing を避ける（`SettingWithCopyWarning` の温床）

```python
# ❌
df[df["col"] == "A"]["score"] = 1.0

# ✅
df.loc[df["col"] == "A", "score"] = 1.0
```

### `isin` を活用する

```python
# ❌ apply
df[df["col"].apply(lambda x: x in target_values)]

# ✅
df[df["col"].isin(target_values)]
```

### 大きい式は `eval` / `query`

```python
# 数百万行で複数列を組み合わせる式は eval が速い
df["score"] = df.eval("a * 0.3 + b * 0.7 - c")
df.query("value > 10 and device == 'mobile'")
```

### `value_counts` / `nunique` は組み込みを使う

```python
df["col"].value_counts()
df["id"].nunique()
```

---

## 6. それでも遅い・メモリ不足の場合

- **Polars**: pandas API に近く、数倍〜十数倍速い。CSV / Parquet の読込も超高速
- **DuckDB**: SQL で巨大 CSV / Parquet を直接集計。中間 DataFrame を作らない
- **Dask**: 分散・out-of-core 処理。チャンク単位の pandas として扱える
- **PyArrow バックエンド**: `pd.read_csv(..., dtype_backend="pyarrow")` で string/null 取り扱いが軽量化

---

## クイックチェックリスト（コードを書く・レビューする前に）

- [ ] `for` ループ / `iterrows` / `itertuples` / `apply(axis=1)` を使っていないか
- [ ] 文字列カラムを `object` のまま放置していないか（`category` 化できる？）
- [ ] `int64` / `float64` 固定になっていないか（ダウンキャスト・nullable 型）
- [ ] `read_csv` で `dtype` / `parse_dates` / `usecols` を指定したか
- [ ] `groupby(category_col)` に `observed=True` を付けたか
- [ ] `merge` キーが左右で同 dtype か
- [ ] ループ内 `concat` / `append` をやっていないか
- [ ] `df[mask]["col"] = ...` のような chained indexing になっていないか
