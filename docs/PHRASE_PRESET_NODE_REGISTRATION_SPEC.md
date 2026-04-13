# フレーズプリセット ノード登録機能 仕様

## 概要

各フレーズプリセットに対し、特定の Maya ノードを「登録」しておき、
通常のフィルタリング結果の代わりに（または併用して）登録ノード集合を
表示できるようにする機能。

ノード名の変更やリネームに耐えるため、登録は **Maya UUID** で管理する。

## データモデル

各フレーズプリセット (`work['phrase_presets'][i]`) に以下のフィールドを追加する。

| キー | 型 | デフォルト | 説明 |
|---|---|---|---|
| `registered_node_uuids` | `list[str]` | `[]` | 登録されたノードの Maya UUID。`cmds.ls(uuid=True)` の戻り値を保存する。順序は登録順 |
| `show_registered_only` | `bool` | `False` | チェックボックス A の状態。True の場合、リストの母集団が「シーン全体」から「登録ノード集合」に切り替わる |
| `apply_filter_to_registered` | `bool` | `False` | チェックボックス B の状態。`show_registered_only=True` のときのみ有効。True の場合、登録ノード集合に対してフレーズプリセットのフィルタを適用する |

UUID → ノードパスの解決は実行時に `cmds.ls(<uuid>)` で都度行う。
解決できない UUID（削除済みなど）は単に表示から除外し、データからは消さない
（シーンを開き直すと復活し得るため）。

## UI 仕様

メインウィンドウのノードリストエリアの **直上** に、以下の 2 段構成で配置する
（フレーズ入力エリアではなくノードリスト側に置くことで、リストへの作用と
視覚的に対応させる）。

**1 段目: チェックボックス行**

- **チェックボックス A**: 「登録ノードのみ表示」
  - オン: ノードリストの母集団が登録ノードに切り替わる
- **チェックボックス B**: 「フィルタを適用」
  - **A がオフのときは無効化（グレーアウト）** され、状態のみ保存される
  - A がオンかつ B がオンのとき、登録ノードに対してフレーズプリセットのフィルタが適用される
  - A がオンかつ B がオフのとき、登録ノードがフィルタを通さずすべて表示される

**2 段目: 登録操作ボタン行 (チェックボックスの直下)**

A がオンの場合のみ表示する（A がオフのときはボタン行ごと非表示）。

- **「+ 登録」** ボタン
  - 現在 Maya で選択されているノードを登録する
  - 既に登録されている UUID は重複追加しない
- **「- 登録解除」** ボタン
  - メインウィンドウのノードリストで選択中のアイテムに対応する UUID を `registered_node_uuids` から取り除く
- **「一括クリア」** ボタン
  - 確認ダイアログを表示してから `registered_node_uuids` を空にする

## フィルタリングロジック

`on_refresh()` の挙動は以下の通り変化する。

```
if show_registered_only:
    base_nodes = uuids_to_paths(registered_node_uuids)
    if apply_filter_to_registered:
        # 登録ノードに対してフレーズプリセットのフィルタを適用
        # 共通フィルター使用フラグも従来通り尊重する
        result = apply_phrase_filter(base_nodes)
    else:
        # フィルタは適用せず、登録ノードをそのまま表示
        result = base_nodes
else:
    # 従来通り: シーン全体に対して共通フィルター + フレーズフィルター
    result = apply_phrase_filter(get_all_nodes())
```

`dag_only` チェックは `show_registered_only` と独立に常に最後に適用する。

## 反映範囲

以下の 3 箇所すべてで同じロジックを適用する（同一プリセットを参照するため一貫させる）。

1. メインウィンドウのノードリスト ([ui/mixins/node_list_manager.py](../ui/mixins/node_list_manager.py))
2. 共通ダイアログ ([ui/dialogs/common_node_list_dialog.py](../ui/dialogs/common_node_list_dialog.py))
3. 統合ダイアログのセル ([ui/dialogs/integrated_node_list_dialog.py](../ui/dialogs/integrated_node_list_dialog.py))

## 永続化

`registered_node_uuids` / `show_registered_only` / `apply_filter_to_registered` は
他のフレーズプリセット項目と同様 `multi_filtering_outliner_settings.json` に
JSON シリアライズして保存される。
プリセットの複製 (`on_duplicate_phrase_preset`) では `copy.deepcopy` により
登録 UUID 一覧もそのまま複製される。

## マイグレーション

既存設定ファイルのフレーズプリセットにこれらのフィールドが無い場合、
読み込み時 / `load_phrase_preset_to_ui` 内で以下のデフォルト値を補完する。

```python
preset.setdefault('registered_node_uuids', [])
preset.setdefault('show_registered_only', False)
preset.setdefault('apply_filter_to_registered', False)
```

これにより既存のプリセットは何もしない限り従来通り動作する。
