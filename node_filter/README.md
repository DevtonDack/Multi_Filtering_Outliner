# Node Filter

Node Filterは、Mayaシーン内のノードをフレーズでフィルタリングして表示する独立したツールモジュールです。

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
node_filter/
├── __init__.py              # モジュールエントリポイント
├── README.md                # このファイル
├── ui/
│   ├── __init__.py
│   └── node_filter_ui.py    # UIコンポーネント
└── tools/
    ├── __init__.py
    └── node_filter.py       # バックエンドロジック
```

## 使用方法

### インポート

```python
from EZ_ModelingTools.node_filter import NodeFilterWidget, create_node_filter_tab

# ウィジェットとして使用
widget = NodeFilterWidget()
widget.show()

# またはタブとして使用
tab = create_node_filter_tab(parent_widget)
```

### 設定ファイル

設定は以下の場所に保存されます：
- パス: `~/.ez_modeling_tools/node_filter_settings.json`
- 形式: JSON

## 依存関係

- PySide6
- Maya Python API (cmds)
- EZ_ModelingTools.main (FlowLayout)

## ライセンス

EZ Modeling Toolsの一部として提供されます。
