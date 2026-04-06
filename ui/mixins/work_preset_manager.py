# -*- coding: utf-8 -*-
"""
WorkPresetManagerMixin - Work preset management operations
"""

from PySide6 import QtWidgets, QtCore
from ui.widgets import EditableButton, DraggablePhraseWidget
import copy


class WorkPresetManagerMixin:
    """作業プリセットの管理を提供するMixin"""

    # ========== Getter Methods ==========

    def get_current_work_preset(self):
        """現在選択されている作業プリセットを取得"""
        if (0 <= self.current_project_index < len(self.projects) and
            0 <= self.current_model_index < len(self.projects[self.current_project_index].get('models', [])) and
            0 <= self.current_work_index < len(self.projects[self.current_project_index]['models'][self.current_model_index].get('works', []))):
            return self.projects[self.current_project_index]['models'][self.current_model_index]['works'][self.current_work_index]
        return None

    # ========== Work Preset Button Management ==========

    def update_work_buttons(self):
        """作業プリセットボタンを更新"""
        # 既存のボタンをクリア
        self.clear_work_buttons()

        model = self.get_current_model()
        if not model:
            return

        works = model.get('works', [])
        for i, work in enumerate(works):
            self.create_work_button(i)

        if works and self.current_work_index < 0:
            self.switch_to_work(0)

    def clear_work_buttons(self):
        """作業プリセットボタンをクリア"""
        for btn in self.list_buttons:
            self.buttons_layout.removeWidget(btn)
            btn.deleteLater()
        self.list_buttons.clear()
        self.current_work_index = -1

    def create_work_button(self, index):
        """作業プリセットボタンを作成"""
        model = self.get_current_model()
        if not model:
            return

        work_data = model['works'][index]
        btn = EditableButton(work_data['name'])
        btn.clicked.connect(lambda: self.switch_to_work(index))
        btn.name_changed.connect(lambda new_name: self.on_work_name_changed(index, new_name))

        # ドラッグ&ドロップ後の処理をインストール
        original_drop = btn.dropEvent
        def drop_with_swap(event):
            original_drop(event)
            if hasattr(event.source(), 'swap_with') and event.source().swap_with == btn:
                self.swap_work_buttons(event.source(), btn)
                delattr(event.source(), 'swap_with')
        btn.dropEvent = drop_with_swap

        self.buttons_layout.addWidget(btn)
        self.list_buttons.append(btn)
        btn.show()

    def swap_work_buttons(self, source_btn, target_btn):
        """作業プリセットボタンを入れ替え"""
        model = self.get_current_model()
        if not model:
            return

        # ボタンのインデックスを取得
        try:
            source_index = self.list_buttons.index(source_btn)
            target_index = self.list_buttons.index(target_btn)
        except ValueError:
            return

        # データを入れ替え
        works = model.get('works', [])
        works[source_index], works[target_index] = works[target_index], works[source_index]

        # 現在選択中のインデックスを更新
        if self.current_work_index == source_index:
            self.current_work_index = target_index
        elif self.current_work_index == target_index:
            self.current_work_index = source_index

        # ボタンを再構築
        self.update_work_buttons()
        self.save_settings()
        print(f"作業プリセットの順序を変更しました")

    # ========== Work Preset Switching ==========

    def switch_to_work(self, index):
        """指定した作業プリセットに切り替え"""
        model = self.get_current_model()
        if not model or index < 0 or index >= len(model.get('works', [])):
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

        # インデックスを更新
        self.current_work_index = index

        # ボタンの状態を更新
        for i, btn in enumerate(self.list_buttons):
            btn.setChecked(i == index)

        # フレーズプリセットボタンを更新
        self.update_phrase_preset_buttons()

        # 共通ダイアログを更新
        self.refresh_common_dialogs()

    # ========== Work Preset State Management ==========

    def save_current_work_state(self):
        """現在の作業プリセットの状態を保存"""
        work_preset = self.get_current_work_preset()
        if not work_preset:
            return

        # フレーズを収集
        phrase_data = []
        for i in range(self.phrase_container_layout.count()):
            widget_item = self.phrase_container_layout.itemAt(i)
            if widget_item and widget_item.widget():
                phrase_widget = widget_item.widget()
                if isinstance(phrase_widget, DraggablePhraseWidget):
                    phrase_data.append({
                        'text': phrase_widget.phrase_input.text(),
                        'enabled': phrase_widget.enabled_check.isChecked(),
                        'exclude': phrase_widget.exclude_check.isChecked(),
                        'exact_token': phrase_widget.exact_token_check.isChecked()
                    })

        work_preset['phrase_data'] = phrase_data if phrase_data else [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}]
        work_preset['match_mode'] = self.match_mode_combo.currentData()
        work_preset['dag_only'] = self.dag_only_check.isChecked()

    def load_work_to_ui(self, index):
        """作業プリセットのデータをUIに読み込み"""
        model = self.get_current_model()
        if not model or index < 0 or index >= len(model.get('works', [])):
            return

        work_data = model['works'][index]

        # フレーズ入力をクリア
        while self.phrase_container_layout.count():
            item = self.phrase_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # フレーズを復元
        phrase_data = work_data.get('phrase_data', [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}])
        for data in phrase_data:
            if isinstance(data, dict):
                self.add_phrase_row(
                    data.get('text', ''),
                    data.get('enabled', True),
                    data.get('exclude', False),
                    data.get('exact_token', False)
                )

        # マッチモードを復元
        match_mode = work_data.get('match_mode', 'any')
        index_to_set = 0 if match_mode == 'any' else 1
        self.match_mode_combo.setCurrentIndex(index_to_set)

        # DAGオブジェクトのみチェックを復元
        dag_only = work_data.get('dag_only', False)
        self.dag_only_check.setChecked(dag_only)

        # リストを更新
        self.on_refresh()

    def on_work_name_changed(self, index, new_name):
        """作業プリセット名が変更された時"""
        model = self.get_current_model()
        if model and 0 <= index < len(model.get('works', [])):
            model['works'][index]['name'] = new_name
            self.save_settings()

    # ========== Work Preset CRUD Operations ==========

    def on_add_list(self):
        """新しい作業プリセットを追加"""
        model = self.get_current_model()
        if not model:
            QtWidgets.QMessageBox.warning(self, "警告", "先にプロジェクトとモデルを選択してください")
            return

        # プリセット名を入力
        work_name, ok = QtWidgets.QInputDialog.getText(
            self, "作業プリセット追加", "作業プリセット名を入力してください:"
        )

        if not ok or not work_name:
            return

        # 新しい作業プリセットを作成（共通フィルターとフレーズプリセットを含む）
        new_work = {
            'name': work_name,
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

        if 'works' not in model:
            model['works'] = []

        model['works'].append(new_work)

        # ボタンを作成
        self.create_work_button(len(model['works']) - 1)

        # 新しいプリセットに切り替え
        self.switch_to_work(len(model['works']) - 1)

        # 設定を保存
        self.save_settings()

    def on_remove_current_list(self):
        """現在の作業プリセットを削除"""
        model = self.get_current_model()
        if not model or self.current_work_index < 0:
            return

        works = model.get('works', [])
        if len(works) <= 1:
            import maya.cmds as cmds
            cmds.warning("最低1つの作業プリセットが必要です")
            return

        # 確認ダイアログ
        work_name = works[self.current_work_index]['name']
        reply = QtWidgets.QMessageBox.question(
            self, "確認",
            f"作業プリセット '{work_name}' を削除しますか?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        # 作業プリセットを削除
        del works[self.current_work_index]

        # ボタンを削除
        btn = self.list_buttons[self.current_work_index]
        self.buttons_layout.removeWidget(btn)
        btn.deleteLater()
        del self.list_buttons[self.current_work_index]

        # インデックスを調整
        if self.current_work_index >= len(works):
            self.current_work_index = len(works) - 1

        # 別のプリセットに切り替え
        self.switch_to_work(self.current_work_index)

        # 設定を保存
        self.save_settings()

        print(f"作業プリセット '{work_name}' を削除しました")

    def on_duplicate_work(self):
        """現在の作業プリセットを複製"""
        model = self.get_current_model()
        if not model or self.current_work_index < 0:
            return

        works = model.get('works', [])
        original_work = works[self.current_work_index]
        original_name = original_work['name']

        # 新しい名前を生成
        counter = 1
        new_name = f"{original_name}_copy"
        while any(w['name'] == new_name for w in works):
            new_name = f"{original_name}_copy{counter}"
            counter += 1

        # 作業プリセットを複製
        new_work = copy.deepcopy(original_work)
        new_work['name'] = new_name

        # 注意: unique_idは意図的にコピーされます
        # 同じIDを持つフレーズプリセットは共通ダイアログで同じ内容を共有します
        # この仕様により、複数の作業プリセット間で共通ダイアログを使用できます

        works.append(new_work)

        # ボタンを作成
        self.create_work_button(len(works) - 1)

        # 新しい作業プリセットに切り替え
        self.switch_to_work(len(works) - 1)

        # 設定を保存
        self.save_settings()

        print(f"作業プリセット '{new_name}' を作成しました")

    # ========== Legacy Compatibility Methods ==========

    def create_list_button(self, index):
        """リスト選択ボタンを作成（旧形式互換、非推奨）"""
        # 階層構造では create_work_button を使用
        pass

    def switch_to_list(self, index):
        """指定したリストに切り替え（旧形式互換、非推奨）"""
        # 階層構造では switch_to_work を使用
        pass

    def save_current_list_state(self):
        """現在のリストの状態を保存（旧形式互換、非推奨）"""
        # 階層構造では save_current_work_state を使用
        pass

    def load_list_to_ui(self, index):
        """リストのデータをUIに読み込み（旧形式互換、非推奨）"""
        # 階層構造では load_work_to_ui を使用
        pass

    def on_list_name_changed(self, index, new_name):
        """リスト名が変更された時（旧形式互換、現在は使用されていない）"""
        # 階層構造では on_work_name_changed を使用
        pass
