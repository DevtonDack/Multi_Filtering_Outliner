# -*- coding: utf-8 -*-
"""
NodeListManagerMixin - Node filtering and selection logic
"""

from PySide6 import QtWidgets, QtCore, QtGui
from ui.widgets import DraggablePhraseWidget
from tools import multi_filtering_outliner
from ui.dialogs.node_type_filter_dialog import NODE_TYPE_ENTRIES, DEFAULT_NODE_TYPE_FILTER


def _expand_with_hierarchy(nodes, cmds):
    """nodes の各ノードとその子孫をすべて含むリストを返す（重複なし、順序保持）"""
    seen = set()
    result = []
    for node in nodes:
        if node not in seen:
            seen.add(node)
            result.append(node)
        try:
            descendants = cmds.listRelatives(node, allDescendents=True, fullPath=True) or []
        except Exception:
            descendants = []
        for desc in descendants:
            if desc not in seen:
                seen.add(desc)
                result.append(desc)
    return result


class NodeListManagerMixin:
    """ノードリストのフィルタリングと選択を管理するMixin"""

    def on_refresh(self):
        """ノードリストを更新"""
        import maya.cmds as cmds

        # 登録ノード表示モードの状態を取得
        show_registered_only = (
            self.show_registered_only_check.isChecked()
            if hasattr(self, 'show_registered_only_check') else False
        )
        apply_filter_to_registered = (
            self.apply_filter_to_registered_check.isChecked()
            if hasattr(self, 'apply_filter_to_registered_check') else False
        )

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

        # 登録ノードモード: 母集団を「登録ノード集合」に置き換える
        include_hierarchy = (
            self.include_hierarchy_check.isChecked()
            if hasattr(self, 'include_hierarchy_check') else False
        )

        skip_phrase_filter = False
        if show_registered_only:
            preset = self.get_current_phrase_preset()
            registered_uuids = preset.get('registered_node_uuids', []) if preset else []
            base_population = self.uuids_to_node_paths(registered_uuids)

            # 子階層を含む場合は各登録ノードの子孫を追加
            if include_hierarchy and base_population:
                base_population = _expand_with_hierarchy(base_population, cmds)

            if not apply_filter_to_registered:
                # フィルタは適用せず、登録ノードをそのまま表示する
                matched_nodes = list(base_population)
                skip_phrase_filter = True
            else:
                # 登録ノード集合を「全ノード」とみなして以降のフィルター処理に渡す
                if use_common_filter and common_include_configs:
                    original_get_all = multi_filtering_outliner.get_all_nodes
                    multi_filtering_outliner.get_all_nodes = lambda: list(base_population)
                    try:
                        matched_nodes = multi_filtering_outliner.filter_nodes_by_phrase_configs(
                            common_include_configs, 'all'
                        )
                    finally:
                        multi_filtering_outliner.get_all_nodes = original_get_all
                else:
                    matched_nodes = list(base_population)
        else:
            # 1. まず共通フィルターを適用（共通フィルター使用が有効な場合のみ）
            if use_common_filter and common_include_configs:
                # 共通フィルターで最初のフィルタリング（常に'all'モード - すべての共通フィルターに一致）
                matched_nodes = multi_filtering_outliner.filter_nodes_by_phrase_configs(common_include_configs, 'all')
            else:
                # 共通フィルターがない、または使用しない場合はすべてのノードから開始
                matched_nodes = multi_filtering_outliner.get_all_nodes()

        # 2. 共通フィルターの除外を適用（共通フィルター使用が有効な場合のみ）
        if not skip_phrase_filter and use_common_filter and common_exclude_configs:
            common_excluded_nodes = multi_filtering_outliner.filter_nodes_by_phrase_configs(common_exclude_configs, 'any')
            matched_nodes = [node for node in matched_nodes if node not in common_excluded_nodes]

        # 3. フレーズプリセットフィルターを適用（共通フィルター結果をさらにフィルター）
        # 包含フィルタリング実行（フレーズごとの設定を使用）
        # 共通フィルターで絞り込まれたノードのみを対象にする
        if not skip_phrase_filter and include_configs:
            # 一時的にすべてのノードを取得する関数を上書き
            original_get_all = multi_filtering_outliner.get_all_nodes
            multi_filtering_outliner.get_all_nodes = lambda: matched_nodes

            matched_nodes = multi_filtering_outliner.filter_nodes_by_phrase_configs(include_configs, match_mode)

            # 元に戻す
            multi_filtering_outliner.get_all_nodes = original_get_all

        # 4. フレーズプリセットの除外フィルタリング実行（除外フレーズがある場合）
        if not skip_phrase_filter and exclude_configs:
            # 除外フレーズに一致するノードを取得（除外は常に'any'モード）
            excluded_nodes = multi_filtering_outliner.filter_nodes_by_phrase_configs(exclude_configs, 'any')
            # 包含リストから除外リストを削除
            matched_nodes = [node for node in matched_nodes if node not in excluded_nodes]

        # DAGオブジェクトのみフィルタリング
        if self.dag_only_check.isChecked():
            import maya.cmds as cmds
            matched_nodes = [node for node in matched_nodes if cmds.objectType(node, isAType='dagNode')]

        # フィルターが一切ない場合は全ノードを上限 1000 件に制限
        _NO_FILTER_LIMIT = 1000
        has_any_filter = (
            include_configs or exclude_configs
            or (use_common_filter and (common_include_configs or common_exclude_configs))
            or skip_phrase_filter  # 登録ノードモードは件数制限なし
        )
        no_filter_truncated = False
        if not has_any_filter and len(matched_nodes) > _NO_FILTER_LIMIT:
            matched_nodes = matched_nodes[:_NO_FILTER_LIMIT]
            no_filter_truncated = True

        # ノードタイプフィルターを適用
        matched_nodes = self._apply_node_type_filter(matched_nodes)

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

        # フィルターなし上限超過時の警告アイテムを先頭に追加
        if no_filter_truncated:
            warn_item = QtWidgets.QListWidgetItem(
                f"⚠ フィルターなし: 先頭 {_NO_FILTER_LIMIT} 件のみ表示"
            )
            warn_item.setForeground(QtGui.QColor(255, 220, 0))
            warn_item.setFlags(warn_item.flags() & ~QtCore.Qt.ItemIsSelectable)
            warn_item.setData(QtCore.Qt.UserRole, None)
            self.node_list.addItem(warn_item)

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

    def _apply_node_type_filter(self, nodes):
        """現在のフレーズプリセットのノードタイプフィルターを適用して nodes を絞り込む"""
        import maya.cmds as cmds

        preset = self.get_current_phrase_preset() if hasattr(self, 'get_current_phrase_preset') else None
        node_type_filter = preset.get('node_type_filter', None) if preset else None

        # フィルター未設定またはすべて True の場合はそのまま返す
        if not node_type_filter:
            return nodes
        from ui.dialogs.node_type_filter_dialog import NodeTypeFilterDialog
        if NodeTypeFilterDialog.is_default(node_type_filter):
            return nodes

        # 「その他」が有効かどうか
        other_enabled = node_type_filter.get("その他", True)

        # 有効なタイプのフラットセットを構築
        allowed_types = set()
        for display_name, maya_types in NODE_TYPE_ENTRIES:
            if display_name == "その他":
                continue
            if node_type_filter.get(display_name, True):
                allowed_types.update(maya_types)

        # 既知の全タイプセット（「その他」判定用）
        all_known_types = set()
        for _, maya_types in NODE_TYPE_ENTRIES:
            all_known_types.update(maya_types)

        # nodeType の一括取得でループ内の cmds 呼び出しを削減
        try:
            node_types = {n: cmds.nodeType(n) for n in nodes}
        except Exception:
            node_types = {}
            for n in nodes:
                try:
                    node_types[n] = cmds.nodeType(n)
                except Exception:
                    pass

        result = []
        for node in nodes:
            nt = node_types.get(node)
            if nt is None:
                continue

            # 直接タイプが許可リストに含まれる
            if nt in allowed_types:
                result.append(node)
                continue

            # 継承チェック（例: directionalLight は light のサブタイプ）
            matched_allowed = False
            for t in allowed_types:
                try:
                    if cmds.objectType(node, isAType=t):
                        matched_allowed = True
                        break
                except Exception:
                    pass
            if matched_allowed:
                result.append(node)
                continue

            # 「その他」が有効なら、既知タイプに非該当のノードを通す
            if other_enabled:
                is_known = nt in all_known_types
                if not is_known:
                    for t in all_known_types:
                        try:
                            if cmds.objectType(node, isAType=t):
                                is_known = True
                                break
                        except Exception:
                            pass
                if not is_known:
                    result.append(node)

        return result

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
