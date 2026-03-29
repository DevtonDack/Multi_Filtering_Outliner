# Node Filter 起動方法

Node Filterを異なるパスから起動するための複数の方法を提供します。

## 方法1: カスタムパス版シェルフボタン（推奨）

### 使用方法

1. `shelf_button_custom_path.py` を開く
2. 以下の行を編集して、任意のパスを指定：
   ```python
   SCRIPT_PATH = r'C:\your\custom\path\to\scripts'
   ```
3. ファイルの内容をコピー
4. Mayaのシェルフに新しいPythonボタンを作成
5. コピーした内容を貼り付けて保存
6. シェルフボタンをクリックして起動

### パスの例

- Windows: `r'C:\Users\YourName\Documents\maya\scripts'`
- Windows (ネットワーク): `r'\\server\share\scripts'`
- Windows (WSL): `r'\\wsl.localhost\Ubuntu-24.04\home\username'`
- Linux/Mac: `r'/home/username/scripts'`

## 方法2: Pythonスクリプトから起動

### 基本的な使用方法

Mayaのスクリプトエディタまたはシェルフボタンから以下を実行：

```python
# launch_node_filter.pyがあるディレクトリをパスに追加
import sys
sys.path.insert(0, r'C:\path\to\EZ_ModelingTools\node_filter')

# launch_node_filterをインポートして起動
import launch_node_filter
launch_node_filter.launch(r'C:\your\custom\path')
```

### デフォルトパスで起動

```python
import sys
sys.path.insert(0, r'C:\path\to\EZ_ModelingTools\node_filter')

import launch_node_filter
launch_node_filter.launch()  # デフォルトパスを使用
```

### 短縮版（1行）

パスを直接指定する場合：

```python
exec(open(r'C:\path\to\EZ_ModelingTools\node_filter\launch_node_filter.py').read())
```

## 方法3: 環境変数を使用

### Windows

1. 環境変数 `NODE_FILTER_PATH` を設定：
   ```
   setx NODE_FILTER_PATH "C:\your\custom\path"
   ```

2. 以下のスクリプトを使用：
   ```python
   import os
   import sys

   script_path = os.environ.get('NODE_FILTER_PATH', r'デフォルトパス')
   sys.path.insert(0, script_path)

   from EZ_ModelingTools.node_filter import NodeFilterWidget
   node_filter_window = NodeFilterWidget()
   node_filter_window.show()
   ```

## 方法4: Maya.env ファイルを使用

1. Maya.env ファイル（通常 `Documents/maya/<version>/Maya.env`）に以下を追加：
   ```
   PYTHONPATH = C:\your\custom\path;$PYTHONPATH
   ```

2. 通常の `shelf_button.py` を使用して起動

## トラブルシューティング

### パスが見つからない

- パスの区切り文字を確認：
  - Windows: `\` または `\\` または `/`
  - Linux/Mac: `/`
- パスの前に `r` を付けて raw string にする（推奨）

### モジュールが見つからない

- `sys.path` にパスが追加されているか確認：
  ```python
  import sys
  print(sys.path)
  ```

### 既存のウィンドウが閉じない

- Mayaを再起動して試してください

## ファイル一覧

- `shelf_button.py` - 標準版シェルフボタン（固定パス）
- `shelf_button_custom_path.py` - カスタムパス版シェルフボタン（編集可能）
- `launch_node_filter.py` - Python関数として起動（プログラマティック起動）
- `LAUNCH_INSTRUCTIONS.md` - このファイル
