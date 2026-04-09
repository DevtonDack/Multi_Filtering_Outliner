"""
DialogManagerMixin - ダイアログの開閉・復元管理
"""

from tools import multi_filtering_outliner
from ui.dialogs import NodeListDialog, CommonNodeListDialog, IntegratedNodeListDialog


class DialogManagerMixin:
    """ダイアログの管理を行うMixin"""

    def clamp_to_screen(self, x, y, width, height):
        """ダイアログの位置を画面内に収める"""
        try:
            from PySide6 import QtWidgets, QtGui

            # 利用可能なすべてのスクリーンを取得
            app = QtWidgets.QApplication.instance()
            screens = app.screens()

            # 少なくとも1つのスクリーンに一部が表示されるかチェック
            for screen in screens:
                screen_geometry = screen.availableGeometry()
                # ウィンドウの右下が画面内にあるか、または画面の左上がウィンドウ内にあるかチェック
                if (screen_geometry.x() <= x + width and
                    screen_geometry.y() <= y + height and
                    screen_geometry.x() + screen_geometry.width() >= x and
                    screen_geometry.y() + screen_geometry.height() >= y):
                    # 画面内に一部が表示されている
                    return x, y

            # どの画面にも表示されていない場合、プライマリスクリーンの中央に配置
            primary_screen = app.primaryScreen()
            screen_geometry = primary_screen.availableGeometry()
            x = screen_geometry.x() + (screen_geometry.width() - width) // 2
            y = screen_geometry.y() + (screen_geometry.height() - height) // 2
            print(f"[clamp_to_screen] 画面外の位置を補正: プライマリスクリーン中央に配置 x={x}, y={y}")
            return x, y
        except Exception as e:
            print(f"[clamp_to_screen] エラー: {e}")
            return x, y

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

        # 統合ダイアログを閉じる（状態は model['integrated_dialog'] に保持）
        if hasattr(self, 'integrated_dialogs'):
            integrated_to_close = list(self.integrated_dialogs.values())
            for dialog in integrated_to_close:
                if dialog.isVisible():
                    dialog._closing_from_main = True
                    if hasattr(dialog, 'update_timer'):
                        dialog.update_timer.stop()
                    # 閉じる前に分割構成とジオメトリを保存
                    try:
                        dialog.save_layout_to_data()
                    except Exception as e:
                        print(f"[close_all_dialogs] 統合ダイアログ保存失敗: {e}")
                    dialog.close()
            self.integrated_dialogs.clear()

    # ========== 統合ダイアログ ==========

    def open_integrated_dialog(self):
        """現在のモデルに対応する統合ダイアログを開く"""
        if self.current_project_index < 0 or self.current_model_index < 0:
            return None
        if not hasattr(self, 'integrated_dialogs'):
            self.integrated_dialogs = {}

        key = (self.current_project_index, self.current_model_index)
        dialog = self.integrated_dialogs.get(key)
        if dialog is not None:
            try:
                dialog.windowTitle()  # 有効性チェック
                if not dialog.isVisible():
                    dialog.show()
                dialog.raise_()
                dialog.activateWindow()
                return dialog
            except RuntimeError:
                del self.integrated_dialogs[key]

        dialog = IntegratedNodeListDialog(
            project_index=self.current_project_index,
            model_index=self.current_model_index,
            parent_widget=self,
            parent=self,
        )
        self.integrated_dialogs[key] = dialog

        # model データ上の open フラグを True にする
        model = self.get_current_model()
        if model is not None:
            data = model.get('integrated_dialog')
            if not isinstance(data, dict):
                data = {'open': True, 'rows': [{'cells': [{'unique_id': ''}]}]}
                model['integrated_dialog'] = data
            else:
                data['open'] = True

        dialog.restore_geometry()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self.save_settings()
        return dialog

    def refresh_integrated_dialogs(self):
        """開いている統合ダイアログを更新（作業プリセット切替時などから呼ぶ）"""
        if not hasattr(self, 'integrated_dialogs'):
            return
        for dialog in list(self.integrated_dialogs.values()):
            try:
                if dialog.isVisible():
                    dialog.on_refresh()
            except RuntimeError:
                pass

    def save_integrated_dialog_states(self):
        """モデル切替前などに現在の統合ダイアログの構成/ジオメトリを保存"""
        if not hasattr(self, 'integrated_dialogs'):
            return
        for dialog in self.integrated_dialogs.values():
            try:
                dialog.save_layout_to_data()
            except RuntimeError:
                pass

    def restore_model_dialogs(self):
        """現在のモデルプリセットのダイアログを復元"""
        print(f"[DEBUG restore_model_dialogs] 開始 (current_model_index={self.current_model_index})")

        if self.current_model_index < 0:
            print(f"[DEBUG restore_model_dialogs] current_model_indexが無効({self.current_model_index})のため終了")
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
                        # 画面境界チェック
                        x, y = self.clamp_to_screen(geometry['x'], geometry['y'], geometry['width'], geometry['height'])
                        dialog.setGeometry(x, y, geometry['width'], geometry['height'])
                        print(f"専用ダイアログを復元しました: {dialog_title}, 位置 x={x}, y={y}")
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
                        # 画面境界チェック
                        x, y = self.clamp_to_screen(geometry['x'], geometry['y'], geometry['width'], geometry['height'])
                        dialog.setGeometry(x, y, geometry['width'], geometry['height'])
                        print(f"共通ダイアログのジオメトリを復元: ID={unique_id}, 位置 x={x}, y={y}")
                    else:
                        print(f"共通ダイアログのジオメトリなし: ID={unique_id}")

        # 統合ダイアログの復元
        integrated_data = model.get('integrated_dialog')
        if isinstance(integrated_data, dict) and integrated_data.get('open', False):
            if not hasattr(self, 'integrated_dialogs'):
                self.integrated_dialogs = {}
            key = (self.current_project_index, self.current_model_index)
            if key not in self.integrated_dialogs:
                try:
                    dialog = IntegratedNodeListDialog(
                        project_index=self.current_project_index,
                        model_index=self.current_model_index,
                        parent_widget=self,
                        parent=self,
                    )
                    self.integrated_dialogs[key] = dialog
                    dialog.restore_geometry()
                    dialog.show()
                    print(f"統合ダイアログを復元しました: model={model.get('name')}")
                except Exception as e:
                    print(f"[restore_model_dialogs] 統合ダイアログ復元失敗: {e}")

    def restore_dialogs(self):
        """前回開いていたダイアログを復元（初回起動時用）"""
        print(f"[DEBUG restore_dialogs] ダイアログ復元開始 (current_model_index={self.current_model_index})")
        # 現在のモデルプリセットのダイアログのみを復元
        self.restore_model_dialogs()
        print(f"[DEBUG restore_dialogs] ダイアログ復元完了")

    def refresh_common_dialogs(self):
        """開いている共通ダイアログをすべて更新"""
        for unique_id, dialog in list(self.common_dialogs.items()):
            if dialog.isVisible():
                dialog.on_refresh()
