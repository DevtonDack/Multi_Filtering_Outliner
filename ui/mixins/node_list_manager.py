# -*- coding: utf-8 -*-
"""
NodeListManagerMixin - Node filtering and selection logic
"""

from PySide6 import QtWidgets, QtCore
from ui.widgets import DraggablePhraseWidget
from tools import multi_filtering_outliner


class NodeListManagerMixin:
    """ノードリストのフィルタリングと選択を管理するMixin"""

    def on_refresh(self):
        """ノードリストを更新"""
        import maya.cmds as cmds

        # 共通フィルター設定を収集（有効なもののみ、包含/除外を分ける）
        common_include_configs = []
        common_exclude_configs = []

        for i in range(self.common_filter_container_layout.count()):
            widget_item = self.common_filter_container_layout.itemAt(i)
            if widget_item and widget_item.widget():
                filter_widget = widget_item.widget()
                if isinstance(filter_widget, DraggablePhraseWidget):
                    if filter_widget.enabled_check.isChecked():
                        text = filter_widget.phrase_input.text().strip()
                        if text:
                            config = {
                                'text': text,
                                'exact_token': filter_widget.exact_token_check.isChecked()
                            }
                            if filter_widget.exclude_check.isChecked():
                                common_exclude_configs.append(config)
                            else:
                                common_include_configs.append(config)

        # フレーズプリセット設定を収集（有効なもののみ、包含/除外を分ける）
        include_configs = []
        exclude_configs = []

        for i in range(self.phrase_container_layout.count()):
            widget_item = self.phrase_container_layout.itemAt(i)
            if widget_item and widget_item.widget():
                phrase_widget = widget_item.widget()
                if isinstance(phrase_widget, DraggablePhraseWidget):
                    # チェックボックスが有効な場合のみフレーズを追加
                    if phrase_widget.enabled_check.isChecked():
                        text = phrase_widget.phrase_input.text().strip()
                        if text:
                            config = {
                                'text': text,
                                'exact_token': phrase_widget.exact_token_check.isChecked()
                            }
                            if phrase_widget.exclude_check.isChecked():
                                exclude_configs.append(config)
                            else:
                                include_configs.append(config)

        # マッチモードを取得
        match_mode = self.match_mode_combo.currentData()

        # 共通フィルター使用チェックボックスの状態を確認
        use_common_filter = self.use_common_filter_check.isChecked()

        # 包含フレーズと共通フィルターの両方がない場合はリストをクリア
        if not include_configs and not (use_common_filter and common_include_configs):
            self.node_list.clear()
            self.current_nodes = []
            return

        # 1. まず共通フィルターを適用（共通フィルター使用が有効な場合のみ）
        if use_common_filter and common_include_configs:
            # 共通フィルターで最初のフィルタリング（常に'all'モード - すべての共通フィルターに一致）
            matched_nodes = multi_filtering_outliner.filter_nodes_by_phrase_configs(common_include_configs, 'all')
        else:
            # 共通フィルターがない、または使用しない場合はすべてのノードから開始
            matched_nodes = multi_filtering_outliner.get_all_nodes()

        # 2. 共通フィルターの除外を適用（共通フィルター使用が有効な場合のみ）
        if use_common_filter and common_exclude_configs:
            common_excluded_nodes = multi_filtering_outliner.filter_nodes_by_phrase_configs(common_exclude_configs, 'any')
            matched_nodes = [node for node in matched_nodes if node not in common_excluded_nodes]

        # 3. フレーズプリセットフィルターを適用（共通フィルター結果をさらにフィルター）
        # 包含フィルタリング実行（フレーズごとの設定を使用）
        # 共通フィルターで絞り込まれたノードのみを対象にする
        if include_configs:
            # 一時的にすべてのノードを取得する関数を上書き
            original_get_all = multi_filtering_outliner.get_all_nodes
            multi_filtering_outliner.get_all_nodes = lambda: matched_nodes

            matched_nodes = multi_filtering_outliner.filter_nodes_by_phrase_configs(include_configs, match_mode)

            # 元に戻す
            multi_filtering_outliner.get_all_nodes = original_get_all

        # 4. フレーズプリセットの除外フィルタリング実行（除外フレーズがある場合）
        if exclude_configs:
            # 除外フレーズに一致するノードを取得（除外は常に'any'モード）
            excluded_nodes = multi_filtering_outliner.filter_nodes_by_phrase_configs(exclude_configs, 'any')
            # 包含リストから除外リストを削除
            matched_nodes = [node for node in matched_nodes if node not in excluded_nodes]

        # DAGオブジェクトのみフィルタリング
        if self.dag_only_check.isChecked():
            import maya.cmds as cmds
            matched_nodes = [node for node in matched_nodes if cmds.objectType(node, isAType='dagNode')]

        # ノードをアルファベット順でソート（ショートネーム基準）
        matched_nodes_sorted = sorted(matched_nodes, key=lambda x: x.split('|')[-1].lower())

        # 現在のノードを保存
        self.current_nodes = matched_nodes_sorted

        # 現在の選択状態を保存（フルパスで）
        selected_nodes = []
        for item in self.node_list.selectedItems():
            node_path = item.data(QtCore.Qt.UserRole)
            if node_path:
                selected_nodes.append(node_path)

        # 選択変更シグナルをブロック（更新中のMaya選択を防ぐ）
        self.node_list.blockSignals(True)

        # リストを更新
        self.node_list.clear()
        for node in matched_nodes_sorted:
            short_name = node.split('|')[-1]
            item = QtWidgets.QListWidgetItem(short_name)
            item.setData(QtCore.Qt.UserRole, node)  # フルパスを保存
            self.node_list.addItem(item)

            # 選択状態を復元
            if node in selected_nodes:
                item.setSelected(True)

        # シグナルのブロックを解除
        self.node_list.blockSignals(False)

        print(f"{len(matched_nodes_sorted)}個のノードが見つかりました")

    def on_select_nodes(self):
        """選択されたノードをMayaで選択"""
        import maya.cmds as cmds

        selected_items = self.node_list.selectedItems()
        if not selected_items:
            # 選択がない場合はすべて選択
            selected_items = [self.node_list.item(i) for i in range(self.node_list.count())]

        if not selected_items:
            cmds.warning("選択するノードがありません")
            return

        # フルパスを取得
        nodes = [item.data(QtCore.Qt.UserRole) for item in selected_items]

        # 選択実行
        multi_filtering_outliner.select_nodes(nodes)

    def on_selection_changed(self):
        """リストの選択が変更された時、Mayaシーンの選択を更新"""
        import maya.cmds as cmds

        selected_items = self.node_list.selectedItems()
        if not selected_items:
            return

        # フルパスを取得
        nodes = []
        for item in selected_items:
            node = item.data(QtCore.Qt.UserRole)
            if cmds.objExists(node):
                nodes.append(node)

        if nodes:
            cmds.select(nodes, replace=True)
