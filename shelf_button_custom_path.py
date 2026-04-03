# -*- coding: utf-8 -*-
"""
Multi Filtering Outliner Shelf Button Script (Custom Path)
パスを指定して Multi Filtering Outliner を起動

使用方法:
    1. スクリプトエディタにこのファイルの内容をコピー
    2. script_path 変数を自分の環境に合わせて変更
    3. Pythonタブで実行するか、シェルフボタンに保存
"""
import sys
import importlib

# ========================================
# ここを自分の環境に合わせて変更してください
# ========================================
script_path = r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner'
# 例:
# script_path = r'C:\path\to\Multi_Filtering_Outliner'  (リポジトリのルート)
# script_path = r'D:\MayaScripts\Multi_Filtering_Outliner'
# ========================================

if script_path not in sys.path:
    sys.path.insert(0, script_path)

# 既存のウィンドウを閉じてリロード
try:
    if 'multi_filtering_outliner_window' in globals() and multi_filtering_outliner_window is not None:
        if hasattr(multi_filtering_outliner_window, 'projects'):
            for project in multi_filtering_outliner_window.projects:
                for model in project.get('models', []):
                    for work in model.get('works', []):
                        for phrase_preset in work.get('phrase_presets', []):
                            phrase_preset['dialog_open'] = False

        if hasattr(multi_filtering_outliner_window, 'node_dialogs'):
            dialogs_to_close = list(multi_filtering_outliner_window.node_dialogs.values())
            multi_filtering_outliner_window.node_dialogs.clear()
            for dialog in dialogs_to_close:
                try:
                    if hasattr(dialog, 'update_timer'):
                        dialog.update_timer.stop()
                    dialog.parent_widget = None
                    dialog.hide()
                    dialog.close()
                    dialog.setParent(None)
                    dialog.deleteLater()
                except:
                    pass

        if hasattr(multi_filtering_outliner_window, 'save_settings'):
            try:
                multi_filtering_outliner_window.save_settings()
            except:
                pass

        multi_filtering_outliner_window.hide()
        multi_filtering_outliner_window.close()
        multi_filtering_outliner_window.setParent(None)
        multi_filtering_outliner_window.deleteLater()
        del multi_filtering_outliner_window

        from PySide6 import QtCore
        QtCore.QCoreApplication.processEvents()
        QtCore.QCoreApplication.processEvents()
except:
    pass

# モジュールをリロード
modules_to_reload = [
    name for name in sorted(sys.modules.keys())
    if name in ['ui', 'tools'] or name.startswith('ui.') or name.startswith('tools.')
]
modules_to_reload.sort(key=lambda x: x.count('.'), reverse=True)
for module_name in modules_to_reload:
    try:
        importlib.reload(sys.modules[module_name])
    except:
        pass

# Multi Filtering Outlinerを起動
from ui.multi_filtering_outliner_ui import MultiFilteringOutlinerWidget
multi_filtering_outliner_window = MultiFilteringOutlinerWidget()
multi_filtering_outliner_window.show()
