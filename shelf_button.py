# -*- coding: utf-8 -*-
"""
Multi Filtering Outliner Shelf Button Script
Mayaのシェルフボタンから Multi Filtering Outliner を起動するためのスクリプト
"""
import sys
import importlib

# スクリプトパスを追加
script_path = r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner'
if script_path not in sys.path:
    sys.path.insert(0, script_path)

# 既存のウィンドウを閉じる（リロード前に）
try:
    if 'multi_filtering_outliner_window' in globals() and multi_filtering_outliner_window is not None:
        # リロード時はダイアログを復元しないよう、すべてのdialog_openフラグをFalseにする
        if hasattr(multi_filtering_outliner_window, 'projects'):
            for project in multi_filtering_outliner_window.projects:
                for model in project.get('models', []):
                    for work in model.get('works', []):
                        for phrase_preset in work.get('phrase_presets', []):
                            phrase_preset['dialog_open'] = False

        # すべてのダイアログを明示的に閉じる
        if hasattr(multi_filtering_outliner_window, 'node_dialogs'):
            dialogs_to_close = list(multi_filtering_outliner_window.node_dialogs.values())
            multi_filtering_outliner_window.node_dialogs.clear()

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
        if hasattr(multi_filtering_outliner_window, 'save_settings'):
            try:
                multi_filtering_outliner_window.save_settings()
            except:
                pass

        # メインウィンドウを閉じる
        multi_filtering_outliner_window.hide()
        multi_filtering_outliner_window.close()
        multi_filtering_outliner_window.setParent(None)
        multi_filtering_outliner_window.deleteLater()
        del multi_filtering_outliner_window

        # Qtイベントループを処理して削除を確実にする
        from PySide6 import QtWidgets, QtCore
        QtCore.QCoreApplication.processEvents()
        QtCore.QCoreApplication.processEvents()  # 2回実行して確実に処理
except Exception as e:
    print(f"ウィンドウクローズエラー: {e}")

# Multi Filtering Outlinerモジュールをリロード
modules_to_reload = [
    name for name in sorted(sys.modules.keys())
    if name in ['ui', 'tools'] or name.startswith('ui.') or name.startswith('tools.')
]
modules_to_reload.sort(key=lambda x: x.count('.'), reverse=True)
for module_name in modules_to_reload:
    try:
        # モジュールが実際に存在するか確認
        module = sys.modules.get(module_name)
        if module is not None and hasattr(module, '__file__') and module.__file__:
            importlib.reload(module)
    except Exception as e:
        # リロードに失敗したモジュールは削除
        if module_name in sys.modules:
            del sys.modules[module_name]

# Multi Filtering Outliner UIを起動
from ui.multi_filtering_outliner_ui import MultiFilteringOutlinerWidget

# 新しいウィンドウを作成
multi_filtering_outliner_window = MultiFilteringOutlinerWidget()
multi_filtering_outliner_window.show()
