# ファイル分割リファクタリング完了報告

## 実施日
2026-04-03

## 目的
`ui/multi_filtering_outliner_ui.py` が4723行と巨大化していたため、保守性・可読性向上のためにファイルを分割

## 実施内容

### ファイルサイズの変化
- **変更前**: 4723行 (ui/multi_filtering_outliner_ui.py)
- **変更後**: 3537行 (ui/multi_filtering_outliner_ui.py)
- **削減**: 約1200行 (25%削減)

### 新規作成したファイル

#### 1. ウィジェット (ui/widgets/)
```
ui/widgets/
├── __init__.py                     # パッケージ初期化
├── editable_button.py              # 115行 - EditableButton
└── draggable_phrase_widget.py      # 144行 - DraggablePhraseWidget
```

**EditableButton** (115行)
- ダブルクリックで編集可能なボタン
- ドラッグ&ドロップで並べ替え可能
- 作業プリセットボタンで使用

**DraggablePhraseWidget** (144行)
- ドラッグ&ドロップ可能なフレーズ行
- チェックボックス（有効/無効、除外、完全一致）
- フレーズプリセット編集画面で使用

#### 2. ダイアログ (ui/dialogs/)
```
ui/dialogs/
├── __init__.py                      # パッケージ初期化
├── preset_import_dialog.py          # 172行 - PresetImportDialog
├── node_list_dialog.py              # 492行 - NodeListDialog
└── common_node_list_dialog.py       # 359行 - CommonNodeListDialog
```

**PresetImportDialog** (172行)
- プリセットインポート時の選択ダイアログ
- 上書き/増分/スキップの選択UI
- フレーズプリセットのインポート機能で使用

**NodeListDialog** (492行)
- 専用ノードリスト表示ダイアログ
- フレーズプリセット固有のフィルタリング
- ジオメトリ保存/復元機能（モデルごと）
- 自動更新・Maya選択同期

**CommonNodeListDialog** (359行)
- 共通ノードリスト表示ダイアログ
- unique_idで管理され、複数プリセット間で共有
- ジオメトリ保存/復元機能（モデルごと、ID単位）
- 自動更新・Maya選択同期

### メインファイルの変更

**ui/multi_filtering_outliner_ui.py**
- インポート文追加：
  ```python
  from ui.widgets import EditableButton, DraggablePhraseWidget
  from ui.dialogs import PresetImportDialog, NodeListDialog, CommonNodeListDialog
  ```
- クラス定義削除：
  - EditableButton (108行)
  - DraggablePhraseWidget (126行)
  - PresetImportDialog (160行)
  - NodeListDialog (464行)
  - CommonNodeListDialog (334行)
- 残存クラス：
  - FlowLayout (内部クラス、EZ_ModelingToolsのフォールバック)
  - MultiFilteringOutlinerWidget (メインクラス)

## 技術的な注意事項

### 循環参照の回避
`DraggablePhraseWidget.dropEvent()` で `MultiFilteringOutlinerWidget` を参照する際、遅延インポートを使用：
```python
from ui.multi_filtering_outliner_ui import MultiFilteringOutlinerWidget
```

### モジュールリロード
`one_line_launch.py` でモジュールを完全削除してから再読み込み：
```python
[sys.modules.pop(n,None) for n in sorted([...], key=lambda x:x.count('.'), reverse=True)]
```

## ディレクトリ構造（最終）

```
Multi_Filtering_Outliner/
├── ui/
│   ├── __init__.py
│   ├── multi_filtering_outliner_ui.py    # 3537行（メインウィジェット）
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── editable_button.py            # 115行
│   │   └── draggable_phrase_widget.py    # 144行
│   └── dialogs/
│       ├── __init__.py
│       ├── preset_import_dialog.py       # 172行
│       ├── node_list_dialog.py           # 492行
│       └── common_node_list_dialog.py    # 359行
├── tools/
│   ├── __init__.py
│   └── multi_filtering_outliner.py       # 148行（フィルタリングロジック）
├── one_line_launch.py
├── quick_launch.py
├── shelf_button.py
└── (その他のファイル)
```

## メリット

### 1. 可読性の向上
- 各ファイルが200-500行程度で読みやすい
- クラスの責任範囲が明確
- ファイル名から機能が推測できる

### 2. 保守性の向上
- ダイアログのバグ修正 → `ui/dialogs/` のみ変更
- ウィジェットの機能追加 → `ui/widgets/` のみ変更
- 変更の影響範囲が限定的

### 3. 再利用性
- `EditableButton` を他のプロジェクトで再利用可能
- ダイアログクラスを独立して使用可能

### 4. テスト容易性
- 各クラスを個別にユニットテスト可能
- モック作成が容易

### 5. 開発効率
- ファイル検索が高速
- IDEのオートコンプリートが高速
- マージコンフリクトの発生率低下

## 動作確認

### 構文チェック
```bash
python3 -m py_compile ui/multi_filtering_outliner_ui.py ui/widgets/*.py ui/dialogs/*.py
```
✅ すべてのファイルが構文エラーなし

### 動作テスト（推奨手順）
1. Mayaで `one_line_launch.py` のコードを実行
2. ウィンドウが正常に表示されることを確認
3. 作業プリセットボタンのドラッグ&ドロップを確認
4. フレーズプリセットのダイアログ表示を確認
5. 共通ダイアログのジオメトリ保存/復元を確認

## 今後の改善案（オプション）

### さらなる分割の可能性
現在のメインファイル（3537行）はまだ大きいため、以下の分割も検討可能：

1. **Mixinクラスによる分離**
   ```
   ui/mixins/
   ├── geometry_manager.py      # ジオメトリ保存/復元ロジック
   ├── dialog_manager.py         # ダイアログ管理ロジック
   └── settings_manager.py       # 設定保存/読み込みロジック
   ```

2. **プロジェクト/モデル管理の分離**
   ```
   ui/managers/
   ├── project_manager.py        # プロジェクト操作
   └── model_manager.py          # モデル操作
   ```

3. **作業/フレーズプリセット管理の分離**
   ```
   ui/managers/
   ├── work_manager.py           # 作業プリセット操作
   └── phrase_manager.py         # フレーズプリセット操作
   ```

ただし、現状の3537行は許容範囲内であり、これ以上の分割は必要に応じて実施すれば良い。

## まとめ
- ✅ ファイルサイズを25%削減（4723行 → 3537行）
- ✅ ウィジェット2クラスを分離（259行）
- ✅ ダイアログ3クラスを分離（1023行）
- ✅ 構文エラーなし
- ✅ 保守性・可読性が大幅に向上

## 関連ドキュメント
- [BUGFIX_DIALOG_GEOMETRY.md](BUGFIX_DIALOG_GEOMETRY.md) - ダイアログジオメトリ復元バグの修正記録
