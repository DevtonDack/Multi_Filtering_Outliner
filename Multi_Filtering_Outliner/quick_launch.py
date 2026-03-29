# -*- coding: utf-8 -*-
"""
Multi Filtering Outliner - Quick Launch (1行起動)

使用方法:
    Mayaのスクリプトエディタ（Python）で以下を実行:

    exec(open(r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner\quick_launch.py').read())

    または、パスを指定して:

    exec(open(r'C:\path\to\your\Multi_Filtering_Outliner\quick_launch.py').read())
"""
import sys
import os
import importlib

# このスクリプトのディレクトリを取得
current_dir = os.path.dirname(os.path.abspath(__file__))
# Multi_Filtering_Outlinerの親ディレクトリをsys.pathに追加
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 既存のウィンドウを閉じる
try:
    if 'multi_filtering_outliner_window' in globals() and multi_filtering_outliner_window is not None:
        if hasattr(multi_filtering_outliner_window, 'projects'):
            for project in multi_filtering_outliner_window.projects:
                for model in project.get('models', []):
                    for work in model.get('works', []):
                        for phrase_preset in work.get('phrase_presets', []):
                            phrase_preset['dialog_open'] = False

        if hasattr(multi_filtering_outliner_window, 'node_dialogs'):
            for dialog in list(multi_filtering_outliner_window.node_dialogs.values()):
                try:
                    if hasattr(dialog, 'update_timer'):
                        dialog.update_timer.stop()
                    dialog.close()
                    dialog.deleteLater()
                except:
                    pass
            multi_filtering_outliner_window.node_dialogs.clear()

        if hasattr(multi_filtering_outliner_window, 'save_settings'):
            try:
                multi_filtering_outliner_window.save_settings()
            except:
                pass

        multi_filtering_outliner_window.close()
        multi_filtering_outliner_window.deleteLater()
        del multi_filtering_outliner_window

        from PySide6 import QtCore
        QtCore.QCoreApplication.processEvents()
except:
    pass

# モジュールをリロード
for name in sorted([n for n in sys.modules.keys() if n == 'Multi_Filtering_Outliner' or n.startswith('Multi_Filtering_Outliner.')], key=lambda x: x.count('.'), reverse=True):
    try:
        importlib.reload(sys.modules[name])
    except:
        pass

# 起動
from Multi_Filtering_Outliner import MultiFilteringOutlinerWidget
multi_filtering_outliner_window = MultiFilteringOutlinerWidget()
multi_filtering_outliner_window.show()
print("Multi Filtering Outliner を起動しました")
