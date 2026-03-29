# -*- coding: utf-8 -*-
"""
Node Filter Launcher
パスを引数として受け取ってNode Filterを起動する関数

使用例:
    import launch_node_filter
    launch_node_filter.launch(r'C:\path\to\your\scripts')

    # または、デフォルトパスで起動
    launch_node_filter.launch()
"""
import sys
import importlib


def launch(script_path=None):
    """
    Node Filterを起動

    Args:
        script_path (str, optional): スクリプトのパス。
                                     Noneの場合はデフォルトパスを使用
    """
    # デフォルトパス
    if script_path is None:
        script_path = r'\\wsl.localhost\Ubuntu-24.04\home\devton_dack_lts'

    # スクリプトパスを追加
    if script_path and script_path not in sys.path:
        sys.path.insert(0, script_path)
        print(f"Node Filter: スクリプトパスを追加しました: {script_path}")

    # 既存のウィンドウを閉じる
    try:
        if 'node_filter_window' in globals() and node_filter_window is not None:
            node_filter_window.close()
            node_filter_window.deleteLater()
            del node_filter_window
    except:
        pass

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

    # グローバル変数として保持
    global node_filter_window
    node_filter_window = NodeFilterWidget()
    node_filter_window.show()

    print("Node Filter: 起動しました")
    return node_filter_window


# スクリプトとして直接実行された場合
if __name__ == "__main__":
    launch()
