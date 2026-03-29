# Multi Filtering Outliner

Multi Filtering Outlinerは、Mayaシーン内のノードをフレーズでフィルタリングして表示する独立したツールモジュールです。

## 機能

### フィルタリング機能
- **フレーズ検索**: 複数のフレーズでノードを検索
- **マッチモード**: 「いずれか一致」または「すべて一致」
- **トークン完全一致**: `_`区切りで完全一致検索（フレーズごとに設定可能）
- **除外フィルター**: 特定のフレーズに一致するノードを除外

### プリセット機能
- **複数のプリセット**: 検索条件をプリセットとして保存
- **自動保存**: フレーズ編集時に自動的に保存
- **ドラッグ&ドロップ**: フレーズの順序を入れ替え可能

### ノードリスト機能
- **アルファベット順表示**: ノード名でソート
- **ダブルクリックでコピー**: ノード名をクリップボードにコピー
- **右クリックメニュー**: ノード名のコピーまたはMayaで選択
- **自動選択**: リストで選択したノードがMayaでも選択される

### ダイアログ機能
- **モードレスダイアログ**: 複数のダイアログを同時に開ける
- **プリセット独立**: 各プリセットごとに独立したダイアログ
- **更新機能**: ダイアログ内で最新の検索結果に更新可能

## フォルダ構造

```
Multi_Filtering_Outliner/
├── __init__.py                           # モジュールエントリポイント
├── README.md                             # このファイル
├── launch_multi_filtering_outliner.py    # ランチャースクリプト
├── ui/
│   ├── __init__.py
│   └── multi_filtering_outliner_ui.py    # UIコンポーネント
└── tools/
    ├── __init__.py
    └── multi_filtering_outliner.py       # バックエンドロジック
```

## 使用方法

### インポート

```python
from Multi_Filtering_Outliner import MultiFilteringOutlinerWidget, create_multi_filtering_outliner_tab

# ウィジェットとして使用
widget = MultiFilteringOutlinerWidget()
widget.show()

# またはタブとして使用
tab = create_multi_filtering_outliner_tab(parent_widget)
```

### ランチャーを使用した起動

```python
import launch_multi_filtering_outliner
launch_multi_filtering_outliner.launch()
```

### 設定ファイル

設定は以下の場所に保存されます：
- パス: `~/.multi_filtering_outliner/multi_filtering_outliner_settings.json`
- 形式: JSON

**旧設定からの自動移行:**
- 初回起動時に `~/.ez_modeling_tools/node_filter_settings.json` が存在する場合、自動的に新しい場所に移行されます
- 移行後も旧設定ファイルはそのまま残ります（削除されません）

## 依存関係

- PySide6
- Maya Python API (cmds)

## ライセンス

独立したモジュールとして提供されます。
