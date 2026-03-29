# -*- coding: utf-8 -*-
"""
Node Filter Shelf Button Script
Mayaのシェルフボタンから Node Filter を起動するためのスクリプト
"""
import sys
import importlib

# スクリプトパスを追加
script_path = r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts'
if script_path not in sys.path:
    sys.path.insert(0, script_path)

# 既存のウィンドウを閉じる（リロード前に）
try:
    if 'node_filter_window' in globals() and node_filter_window is not None:
        # リロード時はダイアログを復元しないよう、すべてのdialog_openフラグをFalseにする
        if hasattr(node_filter_window, 'projects'):
            for project in node_filter_window.projects:
                for model in project.get('models', []):
                    for work in model.get('works', []):
                        for phrase_preset in work.get('phrase_presets', []):
                            phrase_preset['dialog_open'] = False

        # すべてのダイアログを明示的に閉じる
        if hasattr(node_filter_window, 'node_dialogs'):
            dialogs_to_close = list(node_filter_window.node_dialogs.values())
            node_filter_window.node_dialogs.clear()

            for dialog in dialogs_to_close:
                try:
                    # タイマーを停止
                    if hasattr(dialog, 'update_timer'):
                        dialog.update_timer.stop()
                    # 親ウィジェットの参照を削除
                    dialog.parent_widget = None
                    # ダイアログを非表示にして完全に削除
                    dialog.hide()
                    dialog.close()
                    dialog.setParent(None)
                    dialog.deleteLater()
                except Exception as e:
                    print(f"ダイアログクローズエラー: {e}")

        # 設定を保存（dialog_openフラグをFalseで保存）
        if hasattr(node_filter_window, 'save_settings'):
            try:
                node_filter_window.save_settings()
            except:
                pass

        # メインウィンドウを閉じる
        node_filter_window.hide()
        node_filter_window.close()
        node_filter_window.setParent(None)
        node_filter_window.deleteLater()
        del node_filter_window

        # Qtイベントループを処理して削除を確実にする
        from PySide6 import QtWidgets, QtCore
        QtCore.QCoreApplication.processEvents()
        QtCore.QCoreApplication.processEvents()  # 2回実行して確実に処理
except Exception as e:
    print(f"ウィンドウクローズエラー: {e}")

# Node Filterモジュールをリロード
modules_to_reload = [
    name for name in sorted(sys.modules.keys())
    if name == 'EZ_ModelingTools.node_filter' or name.startswith('EZ_ModelingTools.node_filter.')
]
modules_to_reload.sort(key=lambda x: x.count('.'), reverse=True)
for module_name in modules_to_reload:
    try:
        importlib.reload(sys.modules[module_name])
    except:
        pass

# Node Filter UIを起動
from EZ_ModelingTools.node_filter import NodeFilterWidget

# 新しいウィンドウを作成
node_filter_window = NodeFilterWidget()
node_filter_window.show()
