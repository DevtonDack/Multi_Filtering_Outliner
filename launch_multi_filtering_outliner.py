# -*- coding: utf-8 -*-
"""
Multi Filtering Outliner Launcher
パスを引数として受け取ってMulti Filtering Outlinerを起動する関数

使用例:
    import launch_multi_filtering_outliner
    launch_multi_filtering_outliner.launch(r'C:\path\to\your\scripts')

    # または、デフォルトパスで起動
    launch_multi_filtering_outliner.launch()
"""
import sys
import importlib


def launch(script_path=None):
    """
    Multi Filtering Outlinerを起動

    Args:
        script_path (str, optional): スクリプトのパス。
                                     Noneの場合はデフォルトパスを使用
    """
    # デフォルトパス
    if script_path is None:
        script_path = r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts\Multi_Filtering_Outliner'

    # スクリプトパスを追加
    if script_path and script_path not in sys.path:
        sys.path.insert(0, script_path)
        print(f"Multi Filtering Outliner: スクリプトパスを追加しました: {script_path}")

    # 既存のウィンドウを閉じる
    try:
        if 'multi_filtering_outliner_window' in globals() and multi_filtering_outliner_window is not None:
            multi_filtering_outliner_window.close()
            multi_filtering_outliner_window.deleteLater()
            del multi_filtering_outliner_window
    except:
        pass

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

    # グローバル変数として保持
    global multi_filtering_outliner_window
    multi_filtering_outliner_window = MultiFilteringOutlinerWidget()
    multi_filtering_outliner_window.show()

    print("Multi Filtering Outliner: 起動しました")
    return multi_filtering_outliner_window


# スクリプトとして直接実行された場合
if __name__ == "__main__":
    launch()
