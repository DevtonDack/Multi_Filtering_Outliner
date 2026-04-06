# バグフィックス記録: ダイアログジオメトリ復元問題

## 発生日
2026-04-03

## 問題の概要
モデルプリセット間で切り替えを行うと、共通ダイアログ（unique_id で管理）のウィンドウ位置が正しく復元されず、直前のモデルの位置が引き継がれてしまう問題。

## 具体的な症状
1. モデル1で共通ダイアログID=2を位置A (x=4245, y=533) に配置
2. Model_Bに切り替え、ID=2が位置B (x=4104, y=722) に移動
3. モデル1に戻る
4. **期待**: ID=2が位置Aに復元される
5. **実際**: ID=2が位置B（Model_Bの位置）のまま

## 根本原因

### ファイル
`/home/devton_dack_lts/Multi_Filtering_Outliner/ui/multi_filtering_outliner_ui.py`

### 問題のあったコード（4585-4606行目付近）
```python
# 共通ダイアログが開いていた場合
common_dialog_open = phrase_preset.get('common_dialog_open', False)
if common_dialog_open and unique_id:
    # 既に同じIDのダイアログが作成済みでないかチェック
    if unique_id not in self.common_dialogs:
        # 共通ダイアログを作成
        dialog = CommonNodeListDialog(
            unique_id=unique_id,
            parent_widget=self,
            parent=self
        )
        self.common_dialogs[unique_id] = dialog

        # ジオメトリを復元（このフレーズプリセットのジオメトリを使用）
        if 'common_dialog_geometry' in phrase_preset:
            geometry = phrase_preset['common_dialog_geometry']
            dialog.setGeometry(geometry['x'], geometry['y'], geometry['width'], geometry['height'])
            print(f"共通ダイアログを復元しました: ID={unique_id}, 位置 x={geometry['x']}, y={geometry['y']}")
        else:
            print(f"共通ダイアログを復元しました: ID={unique_id} (ジオメトリなし)")

        dialog.show()
```

### 問題点
`if unique_id not in self.common_dialogs:` の条件により、**既にダイアログインスタンスが存在する場合、ジオメトリ復元処理がスキップされていた**。

これにより：
- モデル1 → Model_B の切り替え時：新規作成なのでModel_Bのジオメトリが適用される
- Model_B → モデル1 の切り替え時：既に存在するため、Model_Bのジオメトリのまま（モデル1のジオメトリが復元されない）

## 修正内容

### 修正後のコード
```python
# 共通ダイアログが開いていた場合
common_dialog_open = phrase_preset.get('common_dialog_open', False)
if common_dialog_open and unique_id:
    # 既に同じIDのダイアログが作成済みでないかチェック
    if unique_id not in self.common_dialogs:
        # 共通ダイアログを作成
        dialog = CommonNodeListDialog(
            unique_id=unique_id,
            parent_widget=self,
            parent=self
        )
        self.common_dialogs[unique_id] = dialog
        dialog.show()
        print(f"共通ダイアログを新規作成: ID={unique_id}")
    else:
        # 既存のダイアログを取得
        dialog = self.common_dialogs[unique_id]
        if not dialog.isVisible():
            dialog.show()
        print(f"共通ダイアログを再表示: ID={unique_id}")

    # ジオメトリを復元（このモデルのフレーズプリセットのジオメトリを使用）
    if 'common_dialog_geometry' in phrase_preset:
        geometry = phrase_preset['common_dialog_geometry']
        dialog.setGeometry(geometry['x'], geometry['y'], geometry['width'], geometry['height'])
        print(f"共通ダイアログのジオメトリを復元: ID={unique_id}, 位置 x={geometry['x']}, y={geometry['y']}")
    else:
        print(f"共通ダイアログのジオメトリなし: ID={unique_id}")
```

### 変更のポイント
1. **ジオメトリ復元処理を条件分岐の外に移動**
   - 新規作成時も既存ダイアログ再利用時も、必ずジオメトリを復元する

2. **既存ダイアログの処理を明示的に追加**
   - `else` ブロックで既存ダイアログを取得
   - 非表示の場合は再表示

3. **デバッグ出力の改善**
   - 新規作成、再表示、ジオメトリ復元を個別にログ出力

## 設計思想の再確認

### unique_id の役割
- 同じ unique_id を持つフレーズプリセットは、**共通ダイアログで同じコンテンツ（ノードリスト）を共有**
- しかし、**ウィンドウ位置（ジオメトリ）はモデルごとに独立**

### データ構造
```json
{
  "projects": [
    {
      "models": [
        {
          "name": "モデル1",
          "window_geometry": {...},
          "works": [
            {
              "phrase_presets": [
                {
                  "unique_id": 2,
                  "common_dialog_open": true,
                  "common_dialog_geometry": {
                    "x": 4245,
                    "y": 533,
                    "width": 400,
                    "height": 600
                  }
                }
              ]
            }
          ]
        },
        {
          "name": "Model_B",
          "window_geometry": {...},
          "works": [
            {
              "phrase_presets": [
                {
                  "unique_id": 2,  // 同じID
                  "common_dialog_open": true,
                  "common_dialog_geometry": {
                    "x": 4104,  // 異なる位置
                    "y": 722,
                    "width": 400,
                    "height": 600
                  }
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

## 関連する修正履歴

### 前提となる修正
1. **unique_id の複製時の保持**（on_duplicate_model関数）
   - モデル複製時に unique_id を再生成せず、元の ID を維持
   - これにより、複製されたモデルでも同じ共通ダイアログコンテンツを共有

2. **ジオメトリ保存タイミングの変更**
   - リアルタイム保存（moveEvent）から、イベントベース保存に変更
   - 保存タイミング: モデル切り替え時（on_model_changed）、ウィンドウクローズ時（closeEvent）

3. **dialog_key と unique_id の使い分け**
   - 専用ダイアログ: `dialog_key = f"{work_name}::{phrase_name}"` で管理
   - 共通ダイアログ: `unique_id` で管理

## テスト方法

### 確認手順
1. モデル1で共通ダイアログ（任意の unique_id）を開く
2. ダイアログを特定の位置Aに移動
3. Model_Bに切り替え
4. 同じ unique_id の共通ダイアログが別の位置Bに移動されていることを確認
5. モデル1に戻る
6. **検証**: ダイアログが位置Aに正しく復元されることを確認

### 期待される動作
- 各モデルごとに独立したダイアログ位置が保存・復元される
- 同じ unique_id でもモデルが異なれば異なる位置を持つことができる
- コンテンツ（ノードリスト）は unique_id で共有される

## Pythonキャッシュ問題の対処

### 発生した問題
コードを修正してもMayaで古いコードが実行され続ける現象が発生。

### 原因
- Python の .pyc ファイルキャッシュ
- sys.modules への古いモジュール登録

### 解決方法
`one_line_launch.py` のリロード処理を改善：
```python
# 修正前: importlib.reload() を使用（条件が複雑で失敗することがある）
# 修正後: sys.modules.pop() で完全削除してから再インポート
[sys.modules.pop(n,None) for n in sorted([n for n in list(sys.modules.keys())
 if n in['ui','tools'] or n.startswith('ui.') or n.startswith('tools.')],
 key=lambda x:x.count('.'), reverse=True)]
```

### クリーンな再起動手順
```python
import os
import shutil
import sys

# __pycache__ ディレクトリを物理削除
ui_pycache = r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner\ui\__pycache__'
if os.path.exists(ui_pycache):
    shutil.rmtree(ui_pycache)

tools_pycache = r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner\tools\__pycache__'
if os.path.exists(tools_pycache):
    shutil.rmtree(tools_pycache)

# sys.modules から完全削除
modules_to_remove = [n for n in sys.modules.keys()
                     if n in ['ui', 'tools'] or n.startswith('ui.') or n.startswith('tools.')]
for mod in modules_to_remove:
    sys.modules.pop(mod, None)

# 再読み込み
sys.path.insert(0, r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner')
from ui.multi_filtering_outliner_ui import MultiFilteringOutlinerWidget
multi_filtering_outliner_window = MultiFilteringOutlinerWidget()
multi_filtering_outliner_window.show()
```

## 修正日時
2026-04-03

## 修正者
Claude Code (AI Assistant)

## ステータス
✅ 解決済み - 動作確認完了
