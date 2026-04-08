# -*- coding: utf-8 -*-
"""
HierarchyManagerMixin - Project and Model CRUD operations
"""

from PySide6 import QtWidgets, QtCore
import copy


class HierarchyManagerMixin:
    """プロジェクトとモデルの階層構造管理を提供するMixin"""

    # ========== Getter Methods ==========

    def get_current_project(self):
        """現在選択されているプロジェクトを取得"""
        if 0 <= self.current_project_index < len(self.projects):
            return self.projects[self.current_project_index]
        return None

    def get_current_model(self):
        """現在選択されているモデルを取得"""
        project = self.get_current_project()
        if project and 0 <= self.current_model_index < len(project.get('models', [])):
            return project['models'][self.current_model_index]
        return None

    # ========== Default Factory ==========

    def _create_default_work_preset(self, name='作業1'):
        """空の作業プリセットのデフォルト構造を生成"""
        return {
            'name': name,
            'common_filters': [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}],
            'phrase_presets': [
                {
                    'name': 'フレーズ1',
                    'phrase_data': [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}],
                    'match_mode': 'any',
                    'dag_only': False,
                    'use_common_filter': True
                }
            ]
        }

    def _create_default_model(self, name='モデル1'):
        """デフォルトの作業プリセットを1つ含む空のモデル構造を生成"""
        return {
            'name': name,
            'works': [self._create_default_work_preset()]
        }

    # ========== Project CRUD Operations ==========

    def on_add_project(self):
        """新しいプロジェクトを追加"""
        project_name, ok = QtWidgets.QInputDialog.getText(
            self, "プロジェクト追加", "プロジェクト名を入力してください:"
        )

        if not ok or not project_name:
            return

        # 新しいプロジェクトを作成（デフォルトのモデル+空の作業プリセットを1つ含む）
        new_project = {
            'name': project_name,
            'models': [self._create_default_model()]
        }

        self.projects.append(new_project)
        self.project_combo.addItem(project_name)
        self.project_combo.setCurrentIndex(len(self.projects) - 1)
        self.save_settings()

    def on_remove_project(self):
        """現在のプロジェクトを削除"""
        if self.current_project_index < 0:
            return

        if len(self.projects) <= 1:
            import maya.cmds as cmds
            cmds.warning("最低1つのプロジェクトが必要です")
            return

        project_name = self.projects[self.current_project_index]['name']
        reply = QtWidgets.QMessageBox.question(
            self, "確認",
            f"プロジェクト '{project_name}' を削除しますか？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            del self.projects[self.current_project_index]
            self.project_combo.removeItem(self.current_project_index)
            self.save_settings()

    def on_duplicate_project(self):
        """現在のプロジェクトを複製"""
        if self.current_project_index < 0:
            return

        original_project = self.projects[self.current_project_index]
        original_name = original_project['name']

        # 新しい名前を生成
        counter = 1
        new_name = f"{original_name}_copy"
        while any(p['name'] == new_name for p in self.projects):
            new_name = f"{original_name}_copy{counter}"
            counter += 1

        # プロジェクトを複製
        new_project = copy.deepcopy(original_project)
        new_project['name'] = new_name

        self.projects.append(new_project)
        self.project_combo.addItem(new_name)
        self.project_combo.setCurrentIndex(len(self.projects) - 1)
        self.save_settings()

        print(f"プロジェクト '{new_name}' を作成しました")

    def on_rename_project(self):
        """プロジェクト名を変更"""
        index = self.current_project_index
        if index < 0 or index >= len(self.projects):
            return

        current_name = self.projects[index]['name']
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "プロジェクト名変更", "新しいプロジェクト名を入力してください:",
            text=current_name
        )

        if ok and new_name and new_name != current_name:
            self.projects[index]['name'] = new_name
            self.project_combo.setItemText(index, new_name)
            self.save_settings()
            print(f"プロジェクト名を '{new_name}' に変更しました")

    # ========== Model CRUD Operations ==========

    def on_add_model(self):
        """新しいモデルを追加"""
        project = self.get_current_project()
        if not project:
            QtWidgets.QMessageBox.warning(self, "警告", "先にプロジェクトを選択してください")
            return

        model_name, ok = QtWidgets.QInputDialog.getText(
            self, "モデル追加", "モデル名を入力してください:"
        )

        if not ok or not model_name:
            return

        # 新しいモデルを作成（デフォルトで空の作業プリセットを1つ含む）
        new_model = {
            'name': model_name,
            'works': [self._create_default_work_preset()]
        }

        if 'models' not in project:
            project['models'] = []

        project['models'].append(new_model)
        self.model_combo.addItem(model_name)
        self.model_combo.setCurrentIndex(len(project['models']) - 1)
        self.save_settings()

    def on_remove_model(self):
        """現在のモデルを削除"""
        project = self.get_current_project()
        if not project or self.current_model_index < 0:
            return

        models = project.get('models', [])
        if len(models) <= 1:
            import maya.cmds as cmds
            cmds.warning("最低1つのモデルが必要です")
            return

        model_name = models[self.current_model_index]['name']
        reply = QtWidgets.QMessageBox.question(
            self, "確認",
            f"モデル '{model_name}' を削除しますか？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            del models[self.current_model_index]
            self.model_combo.removeItem(self.current_model_index)
            self.save_settings()

    def on_duplicate_model(self):
        """現在のモデルを複製"""
        print(f"[DEBUG on_duplicate_model] ========== 開始 ==========")
        project = self.get_current_project()
        if not project or self.current_model_index < 0:
            return

        original_model = project['models'][self.current_model_index]
        original_name = original_model['name']
        print(f"[DEBUG on_duplicate_model] 元のモデル: '{original_name}'")
        print(f"[DEBUG on_duplicate_model] 元のモデルのwindow_geometry: {'有' if 'window_geometry' in original_model else '無'}")

        # 新しい名前を生成
        counter = 1
        new_name = f"{original_name}_copy"
        while any(m['name'] == new_name for m in project['models']):
            new_name = f"{original_name}_copy{counter}"
            counter += 1
        print(f"[DEBUG on_duplicate_model] 新しいモデル名: '{new_name}'")

        # モデルを複製
        new_model = copy.deepcopy(original_model)
        new_model['name'] = new_name
        print(f"[DEBUG on_duplicate_model] deepcopy後のwindow_geometry: {'有' if 'window_geometry' in new_model else '無'}")

        # 注意: unique_idは意図的にコピーされます
        # 同じIDを持つフレーズプリセットは共通ダイアログで同じ内容を共有します
        # この仕様により、複数のモデルプリセット間で共通ダイアログを使用できます

        # モデル固有の情報をクリア
        # ウィンドウ配置情報を削除（複製先モデルは独自の配置を持つ）
        if 'window_geometry' in new_model:
            print(f"[DEBUG on_duplicate_model] window_geometryを削除します")
            del new_model['window_geometry']
            print(f"[DEBUG on_duplicate_model] 削除後のwindow_geometry: {'有' if 'window_geometry' in new_model else '無'}")

        # ダイアログの開閉状態とジオメトリをリセット
        for work in new_model.get('works', []):
            for phrase_preset in work.get('phrase_presets', []):
                # 複製時はダイアログを閉じた状態にする
                phrase_preset['dialog_open'] = False
                phrase_preset['common_dialog_open'] = False
                # ダイアログのジオメトリ情報も削除
                if 'dialog_geometry' in phrase_preset:
                    del phrase_preset['dialog_geometry']
                if 'common_dialog_geometry' in phrase_preset:
                    del phrase_preset['common_dialog_geometry']

        print(f"[DEBUG on_duplicate_model] モデルをプロジェクトに追加")
        project['models'].append(new_model)
        print(f"[DEBUG on_duplicate_model] プロジェクト内のモデル数: {len(project['models'])}")

        self.model_combo.addItem(new_name)

        # モデル切り替え前に現在のモデルのジオメトリを保存
        print(f"[DEBUG on_duplicate_model] 現在のモデル(index={self.current_model_index})のジオメトリを保存")
        if self.current_model_index >= 0:
            self.save_model_geometry()

        # 設定をファイルに保存（window_geometryが削除された新モデルを含む）
        print(f"[DEBUG on_duplicate_model] save_settings()を呼び出します")
        self.save_settings()

        # 新しいモデルに切り替え（on_model_changedが呼ばれる）
        new_index = len(project['models']) - 1
        print(f"[DEBUG on_duplicate_model] 新しいモデル(index={new_index})に切り替えます")
        self.model_combo.setCurrentIndex(new_index)

        print(f"[DEBUG on_duplicate_model] ========== 完了 ==========")
        print(f"モデル '{new_name}' を作成しました")

    def on_rename_model(self):
        """モデル名を変更"""
        project = self.get_current_project()
        if not project:
            return

        index = self.current_model_index
        models = project.get('models', [])
        if index < 0 or index >= len(models):
            return

        current_name = models[index]['name']
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "モデル名変更", "新しいモデル名を入力してください:",
            text=current_name
        )

        if ok and new_name and new_name != current_name:
            models[index]['name'] = new_name
            self.model_combo.setItemText(index, new_name)
            self.save_settings()
            print(f"モデル名を '{new_name}' に変更しました")

    # ========== Selection Change Handlers ==========

    def on_project_changed(self, index):
        """プロジェクトが変更された時"""
        if index < 0:
            self.current_project_index = -1
            self.model_combo.clear()
            self.clear_work_buttons()
            self.clear_phrase_preset_buttons()
            return

        # ID入力フィールドのフォーカスを外して編集内容を確定
        if self.preset_id_input.hasFocus():
            self.preset_id_input.clearFocus()
            # イベントループを処理してeditingFinishedシグナルを確実に発火
            QtCore.QCoreApplication.processEvents()

        # 現在の状態を保存
        if self.current_work_index >= 0:
            self.save_common_filters_state()
        if self.current_phrase_preset_index >= 0:
            self.save_current_phrase_preset_state()
        self.save_settings()

        self.current_project_index = index
        self.update_model_combo()

    def on_model_changed(self, index):
        """モデルが変更された時"""
        print(f"[DEBUG on_model_changed] ========== 開始 ==========")
        print(f"[DEBUG on_model_changed] 現在のインデックス={self.current_model_index}, 新規インデックス={index}")

        project = self.get_current_project()
        if project:
            current_model = project.get('models', [])[self.current_model_index] if 0 <= self.current_model_index < len(project.get('models', [])) else None
            new_model = project.get('models', [])[index] if 0 <= index < len(project.get('models', [])) else None
            print(f"[DEBUG on_model_changed] 現在のモデル名={current_model.get('name') if current_model else None}")
            print(f"[DEBUG on_model_changed] 新規モデル名={new_model.get('name') if new_model else None}")

        if index < 0:
            self.current_model_index = -1
            self.clear_work_buttons()
            self.clear_phrase_preset_buttons()
            return

        # 同じモデルが選択された場合は何もしない
        if index == self.current_model_index:
            print(f"[DEBUG on_model_changed] 同じモデルが選択されたのでスキップ")
            return

        # ID入力フィールドのフォーカスを外して編集内容を確定
        if self.preset_id_input.hasFocus():
            self.preset_id_input.clearFocus()
            # イベントループを処理してeditingFinishedシグナルを確実に発火
            QtCore.QCoreApplication.processEvents()

        # 現在のモデルのジオメトリを保存（モデル切り替え前）
        print(f"[DEBUG on_model_changed] --- ジオメトリ保存フェーズ ---")
        if self.current_model_index >= 0:
            self.save_model_geometry()
            # ジオメトリ保存直後にファイルに書き込む
            print(f"[DEBUG on_model_changed] save_settings()を呼び出します")
            self.save_settings()

        # 現在の状態を保存
        if self.current_work_index >= 0:
            self.save_common_filters_state()
        if self.current_phrase_preset_index >= 0:
            self.save_current_phrase_preset_state()

        # ダイアログを閉じる前に、現在開いているダイアログの状態とジオメトリを保存
        print(f"[DEBUG on_model_changed] --- ダイアログ状態・ジオメトリ保存フェーズ ---")
        if project and 0 <= self.current_model_index < len(project.get('models', [])):
            current_model = project['models'][self.current_model_index]
            for work_index, work in enumerate(current_model.get('works', [])):
                work_name = work.get('name', f"作業{work_index+1}")
                for phrase_index, phrase_preset in enumerate(work.get('phrase_presets', [])):
                    unique_id = phrase_preset.get('unique_id')
                    phrase_name = phrase_preset.get('name', f"フレーズ{phrase_index+1}")
                    dialog_key = f"{work_name}::{phrase_name}"

                    # 専用ダイアログの状態とジオメトリを保存
                    if dialog_key in self.node_dialogs and self.node_dialogs[dialog_key].isVisible():
                        phrase_preset['dialog_open'] = True
                        # 専用ダイアログのジオメトリを保存
                        dialog = self.node_dialogs[dialog_key]
                        geometry = dialog.geometry()
                        phrase_preset['dialog_geometry'] = {
                            'x': geometry.x(),
                            'y': geometry.y(),
                            'width': geometry.width(),
                            'height': geometry.height()
                        }
                        print(f"[DEBUG on_model_changed] 専用ダイアログ '{dialog_key}': ジオメトリ保存 x={geometry.x()}, y={geometry.y()}")
                    else:
                        phrase_preset['dialog_open'] = False

                    # 共通ダイアログの状態とジオメトリを保存
                    if unique_id and unique_id in self.common_dialogs and self.common_dialogs[unique_id].isVisible():
                        phrase_preset['common_dialog_open'] = True
                        # 共通ダイアログのジオメトリを保存（現在のモデル内のみ）
                        dialog = self.common_dialogs[unique_id]
                        geometry = dialog.geometry()
                        phrase_preset['common_dialog_geometry'] = {
                            'x': geometry.x(),
                            'y': geometry.y(),
                            'width': geometry.width(),
                            'height': geometry.height()
                        }
                        print(f"[DEBUG on_model_changed] 共通ダイアログ ID={unique_id} ('{phrase_name}'): ジオメトリ保存 x={geometry.x()}, y={geometry.y()}")
                    else:
                        phrase_preset['common_dialog_open'] = False

                    if phrase_preset['dialog_open'] or phrase_preset['common_dialog_open']:
                        print(f"[DEBUG on_model_changed] '{phrase_name}' ID={unique_id}: dialog_open={phrase_preset['dialog_open']}, common_dialog_open={phrase_preset['common_dialog_open']}")

        # 現在のモデルのダイアログをすべて閉じる
        print(f"[DEBUG on_model_changed] --- ダイアログクローズフェーズ ---")
        self.close_all_dialogs()

        # ダイアログを閉じた後、その状態を保存
        print(f"[DEBUG on_model_changed] ダイアログクローズ後にsave_settings()を呼び出します")
        self.save_settings()

        print(f"[DEBUG on_model_changed] --- インデックス更新 ---")
        print(f"[DEBUG on_model_changed] current_model_indexを {self.current_model_index} から {index} に変更")
        self.current_model_index = index
        self.update_work_buttons()

        # 新しいモデルのジオメトリとダイアログを復元
        print(f"[DEBUG on_model_changed] --- ジオメトリ復元フェーズ ---")
        self.restore_model_geometry()
        self.restore_model_dialogs()

        print(f"[DEBUG on_model_changed] ========== 完了 ==========")

    def update_model_combo(self):
        """モデルのコンボボックスを更新"""
        self.model_combo.blockSignals(True)
        self.model_combo.clear()

        project = self.get_current_project()
        if project:
            models = project.get('models', [])
            for model in models:
                self.model_combo.addItem(model['name'])

            if models:
                self.model_combo.setCurrentIndex(0)
                self.current_model_index = 0
            else:
                self.current_model_index = -1

        self.model_combo.blockSignals(False)
        self.update_work_buttons()
