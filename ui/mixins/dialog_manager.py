"""
DialogManagerMixin - ダイアログの開閉・復元管理
"""

from tools import multi_filtering_outliner
from ui.dialogs import NodeListDialog, CommonNodeListDialog


class DialogManagerMixin:
    """ダイアログの管理を行うMixin"""

    def close_all_dialogs(self):
        """すべてのダイアログを閉じる（フラグは保持）"""
        # 専用ダイアログを閉じる
        dialogs_to_close = list(self.node_dialogs.values())
        for dialog in dialogs_to_close:
            if dialog.isVisible():
                dialog._closing_from_main = True
                dialog.close()
        self.node_dialogs.clear()

        # 共通ダイアログを閉じる
        common_dialogs_to_close = list(self.common_dialogs.values())
        for dialog in common_dialogs_to_close:
            if dialog.isVisible():
                dialog._closing_from_main = True
                dialog.update_timer.stop()
                dialog.close()
        self.common_dialogs.clear()

    def restore_model_dialogs(self):
        """現在のモデルプリセットのダイアログを復元"""

        if self.current_model_index < 0:
            return

        project = self.get_current_project()
        if not project:
            return

        models = project.get('models', [])
        if self.current_model_index >= len(models):
            return

        model = models[self.current_model_index]

        # このモデル内のすべての作業プリセットをチェック
        for work_index, work_data in enumerate(model.get('works', [])):
            work_name = work_data.get('name', f"作業{work_index+1}")

            # 各フレーズプリセットをチェック
            for phrase_index, phrase_preset in enumerate(work_data.get('phrase_presets', [])):
                unique_id = phrase_preset.get('unique_id', '')
                dialog_open = phrase_preset.get('dialog_open', False)
                common_dialog_open = phrase_preset.get('common_dialog_open', False)


                # 専用ダイアログが開いていた場合
                if phrase_preset.get('dialog_open', False):
                    phrase_name = phrase_preset.get('name', f"フレーズ{phrase_index+1}")

                    # 共通フィルターを取得
                    common_filter_configs = []
                    use_common_filter = phrase_preset.get('use_common_filter', True)
                    if use_common_filter:
                        for data in work_data.get('common_filters', []):
                            if isinstance(data, dict) and data.get('enabled', True):
                                text = data.get('text', '').strip()
                                if text:
                                    common_filter_configs.append({
                                        'text': text,
                                        'exact_token': data.get('exact_token', False)
                                    })

                    # フレーズ設定を収集
                    include_configs = []
                    exclude_configs = []

                    phrase_data = phrase_preset.get('phrase_data', [])
                    for data in phrase_data:
                        if isinstance(data, dict) and data.get('enabled', True):
                            text = data.get('text', '').strip()
                            if text:
                                config = {
                                    'text': text,
                                    'exact_token': data.get('exact_token', False)
                                }
                                if data.get('exclude', False):
                                    exclude_configs.append(config)
                                else:
                                    include_configs.append(config)

                    # 共通フィルターを含めたフィルタリング実行
                    all_include_configs = common_filter_configs + include_configs

                    if all_include_configs:
                        match_mode = phrase_preset.get('match_mode', 'any')
                        matched_nodes = multi_filtering_outliner.filter_nodes_by_phrase_configs(all_include_configs, match_mode)

                        # 除外フィルタリング
                        if exclude_configs:
                            excluded_nodes = multi_filtering_outliner.filter_nodes_by_phrase_configs(exclude_configs, 'any')
                            matched_nodes = [node for node in matched_nodes if node not in excluded_nodes]

                        # DAGオブジェクトのみフィルタリング
                        dag_only = phrase_preset.get('dag_only', False)
                        if dag_only:
                            import maya.cmds as cmds
                            matched_nodes = [node for node in matched_nodes if cmds.objectType(node, isAType='dagNode')]

                        # アルファベット順でソート
                        nodes = sorted(matched_nodes, key=lambda x: x.split('|')[-1].lower())
                    else:
                        nodes = []

                    # ダイアログの一意なキーとタイトルを作成
                    dialog_key = f"{work_name}::{phrase_name}"
                    dialog_title = f"{work_name} - {phrase_name}"

                    # ダイアログを作成
                    dialog = NodeListDialog(
                        nodes,
                        list_name=dialog_title,
                        work_indices=(self.current_project_index, self.current_model_index, work_index),
                        phrase_index=phrase_index,
                        dialog_key=dialog_key,
                        parent_widget=self,
                        parent=self
                    )
                    self.node_dialogs[dialog_key] = dialog

                    # ジオメトリを復元
                    if 'dialog_geometry' in phrase_preset:
                        geometry = phrase_preset['dialog_geometry']
                        dialog.setGeometry(geometry['x'], geometry['y'], geometry['width'], geometry['height'])
                        print(f"専用ダイアログを復元しました: {dialog_title}, 位置 x={geometry['x']}, y={geometry['y']}")
                    else:
                        print(f"専用ダイアログを復元しました: {dialog_title} (ジオメトリなし)")

                    dialog.show()

                # 共通ダイアログが開いていた場合
                common_dialog_open = phrase_preset.get('common_dialog_open', False)
                if common_dialog_open and unique_id:
                    # 既に同じIDのダイアログが作成済みでないかチェック
                    if unique_id not in self.common_dialogs:
                        # 共通ダイアログを作成
                        dialog = CommonNodeListDialog(
                            unique_id=unique_id,
                            parent_widget=self,
                            parent=self
                        )
                        self.common_dialogs[unique_id] = dialog
                        dialog.show()
                        print(f"共通ダイアログを新規作成: ID={unique_id}")
                    else:
                        # 既存のダイアログを取得
                        dialog = self.common_dialogs[unique_id]
                        if not dialog.isVisible():
                            dialog.show()
                        print(f"共通ダイアログを再表示: ID={unique_id}")

                    # ジオメトリを復元（このモデルのフレーズプリセットのジオメトリを使用）
                    if 'common_dialog_geometry' in phrase_preset:
                        geometry = phrase_preset['common_dialog_geometry']
                        dialog.setGeometry(geometry['x'], geometry['y'], geometry['width'], geometry['height'])
                        print(f"共通ダイアログのジオメトリを復元: ID={unique_id}, 位置 x={geometry['x']}, y={geometry['y']}")
                    else:
                        print(f"共通ダイアログのジオメトリなし: ID={unique_id}")

    def restore_dialogs(self):
        """前回開いていたダイアログを復元（初回起動時用）"""
        # 現在のモデルプリセットのダイアログのみを復元
        self.restore_model_dialogs()

    def refresh_common_dialogs(self):
        """開いている共通ダイアログをすべて更新"""
        for unique_id, dialog in list(self.common_dialogs.items()):
            if dialog.isVisible():
                dialog.on_refresh()
