# 統合ダイアログ (Integrated Dialog) 仕様書

## 概要

「統合ダイアログ」は、複数の共通ダイアログ(`CommonNodeListDialog`)のノードリストを 1 つのウィンドウ内にグリッド状に並べて同時に確認できるようにするための専用ダイアログである。ユーザーは画面を動的に分割し、各セルに共通ダイアログ ID を割り当てて、対応する共通ダイアログと同じフィルタリング結果を表示する。

`CommonNodeListDialog` が「フレーズプリセット 1 つ ↔ ダイアログ 1 つ」である一方、統合ダイアログは「複数の共通ダイアログを 1 つのウィンドウに集約した統合ビュー」として機能する。

## 基本仕様

### 表示内容
- 各セル(分割エリア)に以下を表示:
  - 対応する共通ダイアログ ID(ユーザーが指定、プルダウン等で選択)
  - そのフレーズプリセット名 (参考情報)
  - ノード数
  - フィルタ結果のノードリスト (ダブルクリックでコピー / 右クリックメニュー / 選択で Maya 選択)
- リストの内容は `CommonNodeListDialog.on_refresh` と同一のフィルタリングロジックを使用する
  - `work.common_filters` と `phrase_preset.phrase_data` をメインウィンドウと同等の条件(有効 + 非空テキスト)で適用
  - `use_common_filter` / `match_mode` / `dag_only` を反映

### 自動更新
- 各セルは `CommonNodeListDialog` と同様に 1 秒周期で内容を自動更新する
- 統合ダイアログ自体にフォーカスがあるときは自動更新を抑制する(`CommonNodeListDialog` の仕様に準拠)

## エリア分割仕様

### 制限
- 行数 (row): 最大 **100** (1 ～ 100)
- 列数 (column): 最大 **100** (1 ～ 100)
- **行ごとに独立した列数**を持てる
  - 例: 行 1 は 2 列、行 2 は 6 列、行 3 は 1 列など

### 分割データ構造

モデルプリセット直下に `integrated_dialog` を 1 つ保持する:

```python
model['integrated_dialog'] = {
    'open': False,                       # 起動時復元用の表示フラグ
    'geometry': {'x':..,'y':..,'width':..,'height':..},  # ウィンドウ位置
    'rows': [                            # 行の配列 (1～3 要素)
        {
            'cells': [                   # 行内のセル(1～6 要素)
                {'unique_id': '1'},      # 割り当てられた共通ダイアログ ID
                {'unique_id': '3'},
            ]
        },
        {
            'cells': [
                {'unique_id': ''},       # 空セル(ID 未割り当て): リスト空表示
            ]
        }
    ]
}
```

- 保存時: `save_settings` 経由で `projects[*].models[*].integrated_dialog` にシリアライズされる
- ロード時: `SettingsManagerMixin.load_settings` がそのまま辞書として読み込む

### UI 操作
- 上部ツールバー:
  - **+ 行追加** (最大 100 行まで)
  - **更新** (手動リフレッシュ)
- 各行ヘッダ:
  - **ドラッググリップ(≡)**: 行全体をドラッグして行順を並び替え
  - **+ 列** (最大 100 列まで)
  - **× 行削除**: その行を削除(最低 1 行は残す)
- 各セルヘッダ:
  - **ドラッググリップ(⋮⋮)**: セルをドラッグして並び替え(同一行・別行問わず、ドロップ先と入れ替え)
  - **共通ダイアログ ID 選択コンボボックス**
    - 選択肢: 現在の作業プリセットの `phrase_presets[*].unique_id` のリスト(表示は `"ID: 名前"`)
    - 空選択を許可(未割り当てセル)
  - **×ボタン**: そのセルを削除(行内の最後の 1 セルは削除不可)
- レイアウトは `QGridLayout` ではなく **行ごとに `QHBoxLayout`** を縦に並べ、行ごとに列数を変えられるようにする

### ドラッグ&ドロップ仕様
- **セル**: 各セル左上の `⋮⋮` グリップを掴み、別セルの上にドロップするとその 2 セルが入れ替わる(同行/別行問わず)
- **行**: 各行左上の `≡` グリップを掴み、別行の上にドロップするとその 2 行が入れ替わる
- MIME タイプ:
  - セル: `application/x-mfo-integrated-cell`、ペイロード `"row,col"`
  - 行: `application/x-mfo-integrated-row`、ペイロード `"row"`
- ドラッグ&ドロップ実装は `_DragGrip` ラベル(ドラッグ開始)と `_IntegratedCell` / `_IntegratedRow`(ドロップ受け入れ)で行う

## モデル管理ルール

### 1 モデル = 1 統合ダイアログ
- 統合ダイアログはモデルプリセットごとに 1 つのみ
- `MultiFilteringOutlinerWidget.integrated_dialogs` に `{model_key: IntegratedNodeListDialog}` 形式で保持
  - `model_key` = `(project_index, model_index)` のタプル、または専用のモデル unique_id
- モデル切替時:
  1. 現在開いている統合ダイアログのジオメトリと分割構成を `model['integrated_dialog']` に保存
  2. ダイアログを閉じる
  3. 新しいモデルの `integrated_dialog` が `open=True` なら復元

### 作業プリセット切替時
- **統合ダイアログの分割構成・ジオメトリは変更しない**
- 各セルに設定された `unique_id` は保持されたまま、`get_current_work_preset()` 経由で現在の作業プリセットから同じ `unique_id` のフレーズプリセットを引き当てて再フィルタ
- 該当 `unique_id` が現在の作業プリセットに存在しない場合、そのセルは「該当プリセットなし」と表示し、リストは空にする
- `WorkPresetManagerMixin.switch_to_work` から `refresh_integrated_dialogs()` を呼び出す

### フレーズプリセットの追加/削除/ID 変更時
- `refresh_integrated_dialogs()` で各セルのコンボボックス候補を更新する
- ID が消えたセルは空扱い

## クラス設計

### 新規ファイル: `ui/dialogs/integrated_node_list_dialog.py`

```python
class IntegratedNodeListDialog(QtWidgets.QDialog):
    def __init__(self, project_index, model_index, parent_widget, parent=None): ...
    def _create_ui(self): ...                # ツールバー + 行コンテナ
    def _rebuild_from_data(self): ...        # model['integrated_dialog'] から UI を再構築
    def add_row(self): ...
    def delete_row(self, row_idx): ...       # 任意行を削除
    def add_cell(self, row_idx): ...
    def delete_cell(self, row_idx, col_idx): ...  # 任意セルを削除
    def _on_cell_dropped(self, target_cell, src_row, src_col): ...  # セル入れ替え
    def _on_row_dropped(self, target_row, src_row): ...            # 行入れ替え
    def on_refresh(self): ...                # 全セルを再フィルタ
    def _auto_refresh(self): ...             # タイマー呼び出し
    def save_layout_to_data(self): ...       # 分割構成を model データに書き戻す
    def save_current_geometry(self): ...
    def closeEvent(self, event): ...
```

内部ヘルパ(同ファイル内に定義):
- `_DragGrip(QLabel)`: ドラッグ開始用のハンドル。mime_type とペイロード取得コールバックで駆動
- `_IntegratedCell(QFrame)`: セル 1 つ分。グリップ + ID コンボ + カウント + 削除ボタン + QListWidget。ドロップを受け付けて `cell_dropped` シグナルを発行
- `_IntegratedRow(QWidget)`: 行 1 つ分のコンテナ。ドロップを受け付けて `row_dropped` シグナルを発行

### `MultiFilteringOutlinerWidget` への追加
- `self.integrated_dialogs = {}` (キー: `(project_index, model_index)`)
- `open_integrated_dialog()`: メニュー/ボタンから呼ばれるエントリポイント
- `refresh_integrated_dialogs()`: `switch_to_work`, フレーズプリセット変更後等から呼ばれる更新フック
- `save_integrated_dialog_state()`: モデル切替前に状態を保存
- `restore_integrated_dialog()`: `restore_model_dialogs` 拡張として呼ばれる

### エントリポイント
- メインウィンドウのツールバーに **「統合ダイアログを開く」** ボタン (もしくは既存のメニュー内に項目) を追加
- クリックで現在のモデルに対応する統合ダイアログを作成 / 表示する

## 永続化

### 保存
- `save_settings` 時、現在表示中の統合ダイアログがあれば `save_layout_to_data` を呼び、`rows/cells/unique_id` と `geometry` を `model['integrated_dialog']` に書き戻す
- `open` フラグは表示状態に追従する

### 起動/モデル切替時の復元
- `restore_model_dialogs` で `model.get('integrated_dialog', {}).get('open')` が True の場合に生成
- `rebuild_from_data` で分割構成を復元
- `geometry` を `clamp_to_screen` で画面内に補正

## エラー/エッジケース
- `rows` が空の場合: 最低 1 行 1 セルを自動生成する
- `cells` が空の行: 最低 1 セルを自動生成する
- 未割り当てセル(`unique_id == ''`): リスト空表示、コンボで選択可能
- モデルにフレーズプリセットが存在しない場合: コンボの選択肢は空、セルはリスト空表示

## 既存機能との関係
- `CommonNodeListDialog` と独立して動作する(同時に複数の統合ダイアログを開くわけではないが、既存の共通ダイアログと統合ダイアログは並行表示可能)
- 統合ダイアログのセル内リストは `CommonNodeListDialog` と同じフィルタリングロジックを共有する(将来的にはヘルパ関数へ抽出を検討)
