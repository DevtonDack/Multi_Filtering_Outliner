# Multi Filtering Outliner - 起動方法

Multi Filtering Outlinerを起動する方法は複数あります。用途に応じて選択してください。

## 方法1: 1行起動（最もシンプル）

Mayaのスクリプトエディタ（Python）で以下を実行:

```python
exec(open(r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner\Multi_Filtering_Outliner\quick_launch.py').read())
```

**環境に合わせてパスを変更:**
```python
# Windows の例
exec(open(r'C:\path\to\Multi_Filtering_Outliner\Multi_Filtering_Outliner\quick_launch.py').read())

# Mac/Linux の例
exec(open('/path/to/Multi_Filtering_Outliner/Multi_Filtering_Outliner/quick_launch.py').read())
```

---

## 方法2: ランチャー関数を使用

```python
import sys
sys.path.insert(0, r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner')

import Multi_Filtering_Outliner.launch_multi_filtering_outliner as launcher
launcher.launch()
```

**パスを指定する場合:**
```python
# リポジトリのルートパスを指定
launcher.launch(r'C:\path\to\Multi_Filtering_Outliner')
```

---

## 方法3: 直接インポート

```python
import sys
sys.path.insert(0, r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner')

from Multi_Filtering_Outliner import MultiFilteringOutlinerWidget

window = MultiFilteringOutlinerWidget()
window.show()
```

---

## 方法4: シェルフボタン（推奨）

### A. デフォルトパスを使用

1. [shelf_button.py](shelf_button.py) をテキストエディタで開く
2. 内容をすべてコピー
3. Mayaのスクリプトエディタ（Python）に貼り付け
4. 中クリックでシェルフにドラッグ＆ドロップ

### B. カスタムパスを使用

1. [shelf_button_custom_path.py](shelf_button_custom_path.py) をテキストエディタで開く
2. 11行目の `script_path` を自分の環境に合わせて編集:
   ```python
   script_path = r'C:\Users\YourName\Documents\maya\scripts'
   ```
3. 内容をすべてコピー
4. Mayaのスクリプトエディタ（Python）に貼り付け
5. 中クリックでシェルフにドラッグ＆ドロップ

---

## パスの例

### Windows (WSL経由)
```python
r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner'
```

### Windows (ローカル)
```python
r'C:\path\to\Multi_Filtering_Outliner'
r'D:\MayaScripts\Multi_Filtering_Outliner'
```

### Mac
```python
'/Users/yourname/Multi_Filtering_Outliner'
'/Applications/maya/Multi_Filtering_Outliner'
```

### Linux
```python
'/home/username/Multi_Filtering_Outliner'
'/usr/local/maya/Multi_Filtering_Outliner'
```

**注意**: パスは Multi_Filtering_Outliner リポジトリのルートディレクトリを指定してください。

---

## トラブルシューティング

### モジュールが見つからないエラー
```
ImportError: No module named 'Multi_Filtering_Outliner'
```

**解決方法:**
- `sys.path.insert(0, ...)` でMulti_Filtering_Outlinerの**リポジトリのルートディレクトリ**を指定してください
- 例: リポジトリが `C:\git\Multi_Filtering_Outliner` にある場合
  → `sys.path.insert(0, r'C:\git\Multi_Filtering_Outliner')` と指定
  （間違い例: `r'C:\git'` ← これは親ディレクトリ過ぎ）

### 既存のウィンドウが閉じない

スクリプトエディタで以下を実行:
```python
try:
    multi_filtering_outliner_window.close()
    multi_filtering_outliner_window.deleteLater()
    del multi_filtering_outliner_window
except:
    pass
```

### 設定がリセットされる

設定ファイルの場所を確認:
```python
import os
print(os.path.expanduser("~/.multi_filtering_outliner/multi_filtering_outliner_settings.json"))
```

---

## おすすめの起動方法

**開発中:** 方法1（1行起動）- 最速で起動できる
**本番運用:** 方法4（シェルフボタン）- ボタン1つで起動できる
