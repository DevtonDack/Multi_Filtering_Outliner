# -*- coding: utf-8 -*-
"""
Node Filter
シーン内のノードをフレーズでフィルタリングして表示
"""

import maya.cmds as cmds


def get_all_nodes():
    """
    シーン内のすべてのノードを取得（DAGノード含む）

    Returns:
        list: すべてのノードのリスト
    """
    # すべてのノードを取得（DAGノード + 依存関係ノード）
    all_nodes = cmds.ls(long=True)
    return all_nodes


def filter_nodes_by_phrases(phrases, match_mode='any', exact_token_match=False):
    """
    フレーズでノードをフィルタリング

    Args:
        phrases (list): フレーズのリスト
        match_mode (str): 'any' (いずれか一致) または 'all' (すべて一致)
        exact_token_match (bool): Trueの場合、"_"で区切られたトークン単位で完全一致

    Returns:
        list: マッチしたノードのリスト
    """
    if not phrases:
        return []

    # 空のフレーズを除外
    valid_phrases = [p for p in phrases if p.strip()]
    if not valid_phrases:
        return []

    all_nodes = get_all_nodes()
    matched_nodes = []

    for node in all_nodes:
        # ショートネームを取得
        short_name = node.split('|')[-1]

        if exact_token_match:
            # "_"で分割してトークン化
            tokens = short_name.split('_')

            if match_mode == 'all':
                # すべてのフレーズがトークンとして完全一致するかチェック
                if all(phrase in tokens for phrase in valid_phrases):
                    matched_nodes.append(node)
            else:  # 'any'
                # いずれかのフレーズがトークンとして完全一致するかチェック
                if any(phrase in tokens for phrase in valid_phrases):
                    matched_nodes.append(node)
        else:
            # 通常の部分一致検索
            if match_mode == 'all':
                # すべてのフレーズが含まれているかチェック
                if all(phrase in short_name for phrase in valid_phrases):
                    matched_nodes.append(node)
            else:  # 'any'
                # いずれかのフレーズが含まれているかチェック
                if any(phrase in short_name for phrase in valid_phrases):
                    matched_nodes.append(node)

    return matched_nodes


def filter_nodes_by_phrase_configs(phrase_configs, match_mode='any'):
    """
    フレーズ設定でノードをフィルタリング（各フレーズごとにトークン完全一致を制御）

    Args:
        phrase_configs (list): フレーズ設定のリスト [{'text': str, 'exact_token': bool}, ...]
        match_mode (str): 'any' (いずれか一致) または 'all' (すべて一致)

    Returns:
        list: マッチしたノードのリスト
    """
    if not phrase_configs:
        return []

    # 空のフレーズを除外
    valid_configs = [cfg for cfg in phrase_configs if cfg.get('text', '').strip()]
    if not valid_configs:
        return []

    all_nodes = get_all_nodes()
    matched_nodes = []

    for node in all_nodes:
        # ショートネームを取得
        short_name = node.split('|')[-1]

        # 各フレーズが一致するかチェック
        matches = []
        for config in valid_configs:
            phrase = config['text']
            exact_token = config.get('exact_token', False)

            if exact_token:
                # "_"で分割してトークン化
                tokens = short_name.split('_')
                # トークンとして完全一致するかチェック
                matches.append(phrase in tokens)
            else:
                # 通常の部分一致検索
                matches.append(phrase in short_name)

        # マッチモードに応じて判定
        if match_mode == 'all':
            if all(matches):
                matched_nodes.append(node)
        else:  # 'any'
            if any(matches):
                matched_nodes.append(node)

    return matched_nodes


def select_nodes(node_list):
    """
    ノードを選択

    Args:
        node_list (list): 選択するノードのリスト
    """
    if not node_list:
        cmds.warning("選択するノードがありません")
        return

    # 存在するノードのみを選択
    valid_nodes = []
    for node in node_list:
        if cmds.objExists(node):
            valid_nodes.append(node)

    if valid_nodes:
        cmds.select(valid_nodes, replace=True)
        print(f"{len(valid_nodes)}個のノードを選択しました")
    else:
        cmds.warning("有効なノードがありません")
