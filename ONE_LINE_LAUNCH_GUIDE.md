# Multi Filtering Outliner - 1行起動ガイド

## 最速起動方法

Multi Filtering Outlinerを1行のコマンドで起動できます。

---

## 方法1: launch_command.txt を使う（最も簡単）

1. **[launch_command.txt](launch_command.txt)** をテキストエディタで開く
2. 内容をすべてコピー
3. Mayaのスクリプトエディタ（Python）に貼り付け
4. 実行（Ctrl+Enter または 再生ボタン）

### 実行するコマンド:
```python
import sys;sys.path.insert(0,r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner')if r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner'not in sys.path else None;exec("import importlib;[importlib.reload(sys.modules[n])for n in sorted([n for n in sys.modules.keys()if n=='Multi_Filtering_Outliner'or n.startswith('Multi_Filtering_Outliner.')],key=lambda x:x.count('.'),reverse=True)if n in sys.modules];from Multi_Filtering_Outliner import MultiFilteringOutlinerWidget;globals().update({'multi_filtering_outliner_window':MultiFilteringOutlinerWidget()});multi_filtering_outliner_window.show()")
```

---

## 方法2: カスタムパスで起動

1. **[launch_command_template.txt](launch_command_template.txt)** を開く
2. `YOUR_PATH_HERE` を自分の環境のパスに変更
3. コマンドをコピーして実行

### パスの例:

**Windows (ローカル):**
```python
import sys;sys.path.insert(0,r'C:\path\to\Multi_Filtering_Outliner')if r'C:\path\to\Multi_Filtering_Outliner'not in sys.path else None;exec("import importlib;[importlib.reload(sys.modules[n])for n in sorted([n for n in sys.modules.keys()if n=='Multi_Filtering_Outliner'or n.startswith('Multi_Filtering_Outliner.')],key=lambda x:x.count('.'),reverse=True)if n in sys.modules];from Multi_Filtering_Outliner import MultiFilteringOutlinerWidget;globals().update({'multi_filtering_outliner_window':MultiFilteringOutlinerWidget()});multi_filtering_outliner_window.show()")
```

**Mac:**
```python
import sys;sys.path.insert(0,'/Users/yourname/Multi_Filtering_Outliner')if '/Users/yourname/Multi_Filtering_Outliner'not in sys.path else None;exec("import importlib;[importlib.reload(sys.modules[n])for n in sorted([n for n in sys.modules.keys()if n=='Multi_Filtering_Outliner'or n.startswith('Multi_Filtering_Outliner.')],key=lambda x:x.count('.'),reverse=True)if n in sys.modules];from Multi_Filtering_Outliner import MultiFilteringOutlinerWidget;globals().update({'multi_filtering_outliner_window':MultiFilteringOutlinerWidget()});multi_filtering_outliner_window.show()")
```

**Linux:**
```python
import sys;sys.path.insert(0,'/home/username/Multi_Filtering_Outliner')if '/home/username/Multi_Filtering_Outliner'not in sys.path else None;exec("import importlib;[importlib.reload(sys.modules[n])for n in sorted([n for n in sys.modules.keys()if n=='Multi_Filtering_Outliner'or n.startswith('Multi_Filtering_Outliner.')],key=lambda x:x.count('.'),reverse=True)if n in sys.modules];from Multi_Filtering_Outliner import MultiFilteringOutlinerWidget;globals().update({'multi_filtering_outliner_window':MultiFilteringOutlinerWidget()});multi_filtering_outliner_window.show()")
```

---

## 方法3: シェルフボタンに登録

1. 上記のコマンドをコピー
2. Mayaのスクリプトエディタに貼り付け
3. **中クリック**でシェルフにドラッグ＆ドロップ
4. 次回からボタン1つで起動可能

---

## コマンドの説明

このコマンドは以下の処理を1行で実行します:

1. **パスを追加**: `sys.path.insert(0, ...)`
2. **モジュールをリロード**: 既存のモジュールを最新の状態に更新
3. **ウィジェットを作成**: `MultiFilteringOutlinerWidget()`
4. **表示**: `show()`

### 特徴:
- ✅ リロード機能付き - コードを修正後、再実行すれば更新される
- ✅ グローバル変数に保存 - `multi_filtering_outliner_window` でアクセス可能
- ✅ 重複パス追加の防止 - 既にパスがある場合はスキップ

---

## トラブルシューティング

### エラー: `No module named 'Multi_Filtering_Outliner'`

**原因**: パスが正しく設定されていない

**解決方法**:
1. Multi_Filtering_Outliner **リポジトリのルートディレクトリ** のパスを指定
   - 例: リポジトリが `C:\git\Multi_Filtering_Outliner\` にある場合
   - 正しい: `r'C:\git\Multi_Filtering_Outliner'`
   - 間違い: `r'C:\git'` や `r'C:\git\Multi_Filtering_Outliner\Multi_Filtering_Outliner'`
2. パスに日本語やスペースが含まれる場合は、正しくエスケープされているか確認

**構造の例**:
```
Multi_Filtering_Outliner/          <- このディレクトリをsys.pathに追加
    ├── Multi_Filtering_Outliner/  <- 実際のPythonモジュール
    │   ├── __init__.py
    │   ├── ui/
    │   └── tools/
    └── node_filter/
```

### エラー: 構文エラー

**原因**: コマンドが途中で切れている

**解決方法**:
- コマンド全体を1行でコピー（改行が入らないように）
- テキストファイルから直接コピーすることを推奨

### ウィンドウが表示されない

スクリプトエディタで以下を確認:
```python
print(multi_filtering_outliner_window)
print(multi_filtering_outliner_window.isVisible())
```

---

## 便利な補足コマンド

### ウィンドウを閉じる:
```python
multi_filtering_outliner_window.close()
```

### ウィンドウを再表示:
```python
multi_filtering_outliner_window.show()
```

### ウィンドウの状態を確認:
```python
print(multi_filtering_outliner_window.isVisible())
```

---

## 他の起動方法

より詳細な起動方法は **[LAUNCH_INSTRUCTIONS.md](LAUNCH_INSTRUCTIONS.md)** を参照してください。
