# -*- coding: utf-8 -*-
"""
PhrasePresetManagerMixin - Phrase preset management operations
"""

from PySide6 import QtWidgets, QtCore
from ui.widgets import EditableButton, DraggablePhraseWidget
import copy


class PhrasePresetManagerMixin:
    """フレーズプリセットの管理を提供するMixin"""

    # ========== Getter Methods ==========

    def get_current_phrase_preset(self):
        """現在選択されているフレーズプリセットを取得"""
        work = self.get_current_work_preset()
        if work and 0 <= self.current_phrase_preset_index < len(work.get('phrase_presets', [])):
            return work['phrase_presets'][self.current_phrase_preset_index]
        return None

    def get_next_available_id(self, work=None):
        """次に利用可能な番号IDを取得"""
        if work is None:
            work = self.get_current_work_preset()

        if not work:
            return "1"

        used_ids = set()
        for preset in work.get('phrase_presets', []):
            preset_id = preset.get('unique_id', '')
            # 数字に変換できる場合のみ追加
            if preset_id and preset_id.isdigit():
                used_ids.add(int(preset_id))

        # 次に利用可能な番号を見つける
        next_id = 1
        while next_id in used_ids:
            next_id += 1

        return str(next_id)

    # ========== Phrase Preset Button Management ==========

    def update_phrase_preset_buttons(self):
        """フレーズプリセットボタンを更新"""
        self.clear_phrase_preset_buttons()

        work = self.get_current_work_preset()
        if not work:
            return

        # phrase_presetsがない場合は、既存のphrase_dataから作成
        if 'phrase_presets' not in work:
            work['phrase_presets'] = [{
                'name': 'フレーズ1',
                'phrase_data': work.get('phrase_data', [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}]),
                'match_mode': work.get('match_mode', 'any'),
                'dag_only': work.get('dag_only', False)
            }]

        # 共通フィルターをUIに読み込み
        self.load_common_filters_to_ui()

        phrase_presets = work.get('phrase_presets', [])
        # 既存のプリセットにユニークIDがない場合は追加、UUID形式の場合は数字形式に変換
        for preset in phrase_presets:
            if 'unique_id' not in preset:
                preset['unique_id'] = self.get_next_available_id(work)
            else:
                # UUID形式（数字以外を含む）の場合は数字形式に変換
                unique_id = preset.get('unique_id', '')
                if unique_id and not unique_id.isdigit():
                    preset['unique_id'] = self.get_next_available_id(work)
            if 'use_common_dialog' not in preset:
                preset['use_common_dialog'] = False

        for i, preset in enumerate(phrase_presets):
            self.create_phrase_preset_button(i)

        if phrase_presets and self.current_phrase_preset_index < 0:
            self.switch_to_phrase_preset(0)

    def clear_phrase_preset_buttons(self):
        """フレーズプリセットボタンをクリア"""
        for btn in self.phrase_preset_buttons:
            self.phrase_preset_buttons_layout.removeWidget(btn)
            btn.deleteLater()
        self.phrase_preset_buttons.clear()
        self.current_phrase_preset_index = -1

    def create_phrase_preset_button(self, index):
        """フレーズプリセットボタンを作成"""
        work = self.get_current_work_preset()
        if not work:
            return

        phrase_presets = work.get('phrase_presets', [])
        if index < 0 or index >= len(phrase_presets):
            return

        preset_data = phrase_presets[index]
        btn = EditableButton(preset_data['name'])
        btn.clicked.connect(lambda: self.switch_to_phrase_preset(index))
        btn.name_changed.connect(lambda new_name: self.on_phrase_preset_name_changed(index, new_name))

        # ドラッグ&ドロップ後の処理をインストール
        original_drop = btn.dropEvent
        def drop_with_swap(event):
            original_drop(event)
            if hasattr(event.source(), 'swap_with') and event.source().swap_with == btn:
                self.swap_phrase_preset_buttons(event.source(), btn)
                delattr(event.source(), 'swap_with')
        btn.dropEvent = drop_with_swap

        self.phrase_preset_buttons_layout.addWidget(btn)
        self.phrase_preset_buttons.append(btn)
        btn.show()

    def swap_phrase_preset_buttons(self, source_btn, target_btn):
        """フレーズプリセットボタンを入れ替え"""
        work = self.get_current_work_preset()
        if not work:
            return

        # ボタンのインデックスを取得
        try:
            source_index = self.phrase_preset_buttons.index(source_btn)
            target_index = self.phrase_preset_buttons.index(target_btn)
        except ValueError:
            return

        # データを入れ替え
        phrase_presets = work.get('phrase_presets', [])
        phrase_presets[source_index], phrase_presets[target_index] = phrase_presets[target_index], phrase_presets[source_index]

        # 現在選択中のインデックスを更新
        if self.current_phrase_preset_index == source_index:
            self.current_phrase_preset_index = target_index
        elif self.current_phrase_preset_index == target_index:
            self.current_phrase_preset_index = source_index

        # ボタンを再構築
        self.update_phrase_preset_buttons()
        self.save_settings()
        print(f"フレーズプリセットの順序を変更しました")

    # ========== Phrase Preset Switching ==========

    def switch_to_phrase_preset(self, index):
        """指定したフレーズプリセットに切り替え"""

        work = self.get_current_work_preset()
        if not work:
            return

        phrase_presets = work.get('phrase_presets', [])

        if index < 0 or index >= len(phrase_presets):
            return


        # ID入力フィールドのフォーカスを外して編集内容を確定
        if self.preset_id_input.hasFocus():
            self.preset_id_input.clearFocus()
            # イベントループを処理してeditingFinishedシグナルを確実に発火
            QtCore.QCoreApplication.processEvents()

        # 現在の状態を保存（切り替え前のプリセットが有効な場合）
        # インデックスが異なる場合のみ保存（同じプリセットをクリックした場合はスキップ）
        if self.current_phrase_preset_index >= 0 and self.current_phrase_preset_index != index:
            self.save_current_phrase_preset_state()
        elif self.current_phrase_preset_index == index:
            pass

        # インデックスを更新
        self.current_phrase_preset_index = index

        # ボタンの状態を更新
        for i, btn in enumerate(self.phrase_preset_buttons):
            btn.setChecked(i == index)

        # UIを更新
        self.load_phrase_preset_to_ui(index)

    # ========== Phrase Management (UI) ==========

    def _get_phrase_columns(self):
        """1 行あたりのフレーズ列数（デフォルト 2）"""
        return getattr(self, 'phrase_columns', 2)

    def _collect_phrase_widgets(self):
        """phrase_container_layout に現在存在するフレーズウィジェットを
        挿入順(= グリッドの row-major 順)で返す。"""
        widgets = []
        for i in range(self.phrase_container_layout.count()):
            item = self.phrase_container_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), DraggablePhraseWidget):
                widgets.append(item.widget())
        return widgets

    def _repack_phrase_widgets(self, widgets=None):
        """フレーズウィジェットを 2 列グリッドへ再配置する。
        widgets を指定しない場合は現在レイアウト内のものを使用。"""
        if widgets is None:
            widgets = self._collect_phrase_widgets()
        # いったんレイアウトから外す
        for w in widgets:
            self.phrase_container_layout.removeWidget(w)
        cols = self._get_phrase_columns()
        for i, w in enumerate(widgets):
            self.phrase_container_layout.addWidget(w, i // cols, i % cols)

    def add_phrase_row(self, text='', enabled=True, exclude=False, exact_token=False):
        """フレーズ入力行を追加（2 列グリッドへ row-major で配置）"""
        phrase_widget = DraggablePhraseWidget(text, enabled, exclude, exact_token, self.phrase_container)
        phrase_widget.phrase_input.textChanged.connect(self.on_filter_changed)
        phrase_widget.enabled_check.stateChanged.connect(self.on_filter_changed)
        phrase_widget.exclude_check.stateChanged.connect(self.on_filter_changed)
        phrase_widget.exact_token_check.stateChanged.connect(self.on_filter_changed)
        phrase_widget.remove_btn.clicked.connect(lambda: self.on_remove_phrase(phrase_widget))

        cols = self._get_phrase_columns()
        count = self.phrase_container_layout.count()
        self.phrase_container_layout.addWidget(phrase_widget, count // cols, count % cols)

    def on_add_phrase(self):
        """フレーズ入力を追加"""
        self.add_phrase_row()
        # フレーズ追加時に自動保存
        self.save_settings()

    def on_remove_phrase(self, phrase_widget):
        """特定のフレーズ入力を削除"""
        if self.phrase_container_layout.count() <= 1:
            # 最低1つは残す
            return

        # ウィジェットを削除してからグリッドを詰める
        self.phrase_container_layout.removeWidget(phrase_widget)
        phrase_widget.deleteLater()
        self._repack_phrase_widgets()

        # リストを更新
        self.on_filter_changed()

    def on_remove_last_phrase(self):
        """最後のフレーズ入力を削除"""
        if self.phrase_container_layout.count() > 1:
            widgets = self._collect_phrase_widgets()
            if widgets:
                self.on_remove_phrase(widgets[-1])

    def swap_phrase_rows(self, source_widget, target_widget):
        """フレーズ行を入れ替え（2 列グリッド対応）"""
        widgets = self._collect_phrase_widgets()
        try:
            s = widgets.index(source_widget)
            t = widgets.index(target_widget)
        except ValueError:
            return
        if s == t:
            return
        widgets[s], widgets[t] = widgets[t], widgets[s]
        self._repack_phrase_widgets(widgets)

        # リストを更新
        self.on_filter_changed()

    # ========== Phrase Preset State Management ==========

    def save_current_phrase_preset_state(self):
        """現在のフレーズプリセットの状態を保存"""
        # 読み込み中は保存しない
        if getattr(self, '_is_loading', False):
            return

        phrase_preset = self.get_current_phrase_preset()
        if not phrase_preset:
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

        phrase_preset['phrase_data'] = phrase_data if phrase_data else [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}]
        phrase_preset['match_mode'] = self.match_mode_combo.currentData()
        phrase_preset['dag_only'] = self.dag_only_check.isChecked()
        phrase_preset['use_common_filter'] = self.use_common_filter_check.isChecked()
        phrase_preset['unique_id'] = self.preset_id_input.text().strip()

        # dialog_open と common_dialog_open は既存の値を保持（削除しない）
        # これらはダイアログの開閉状態を管理するフィールドなので、UIから読み取るものではない


    def load_phrase_preset_to_ui(self, index):
        """フレーズプリセットのデータをUIに読み込み"""

        work = self.get_current_work_preset()
        if not work:
            return

        phrase_presets = work.get('phrase_presets', [])
        if index < 0 or index >= len(phrase_presets):
            return

        preset_data = phrase_presets[index]

        # 読み込み中フラグをセット（シグナルによる自動保存を防ぐ）
        self._is_loading = True

        try:
            # フレーズ入力をクリア
            while self.phrase_container_layout.count():
                item = self.phrase_container_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # フレーズを復元
            phrase_data = preset_data.get('phrase_data', [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}])
            for data in phrase_data:
                if isinstance(data, dict):
                    self.add_phrase_row(
                        data.get('text', ''),
                        data.get('enabled', True),
                        data.get('exclude', False),
                        data.get('exact_token', False)
                    )

            # マッチモードを復元
            match_mode = preset_data.get('match_mode', 'any')
            index_to_set = 0 if match_mode == 'any' else 1
            self.match_mode_combo.setCurrentIndex(index_to_set)

            # DAGオブジェクトのみチェックを復元
            dag_only = preset_data.get('dag_only', False)
            self.dag_only_check.setChecked(dag_only)

            # 共通フィルター使用チェックを復元
            use_common_filter = preset_data.get('use_common_filter', True)
            self.use_common_filter_check.setChecked(use_common_filter)

            # プリセットIDを復元
            unique_id = preset_data.get('unique_id', '')

            if not unique_id:
                unique_id = self.get_next_available_id()
                preset_data['unique_id'] = unique_id
            else:
                # UUID形式（数字以外を含む）の場合は数字形式に変換
                if not unique_id.isdigit():
                    old_id = unique_id
                    unique_id = self.get_next_available_id()
                    preset_data['unique_id'] = unique_id


            # ID入力フィールドのシグナルを一時的にブロック
            self.preset_id_input.blockSignals(True)
            self.preset_id_input.setText(unique_id)
            self.preset_id_input.blockSignals(False)

            # リストを更新
            self.on_refresh()

        finally:
            # 読み込み中フラグを解除
            self._is_loading = False

        # 読み込み完了後、重複チェックを実行（視覚的フィードバック）
        self.check_id_duplicate()

    def on_phrase_preset_name_changed(self, index, new_name):
        """フレーズプリセット名が変更された時"""
        work = self.get_current_work_preset()
        if work and 0 <= index < len(work.get('phrase_presets', [])):
            work['phrase_presets'][index]['name'] = new_name
            self.save_settings()

    # ========== Phrase Preset CRUD Operations ==========

    def on_add_phrase_preset(self):
        """新しいフレーズプリセットを追加"""
        work = self.get_current_work_preset()
        if not work:
            QtWidgets.QMessageBox.warning(self, "警告", "先に作業プリセットを選択してください")
            return

        # プリセット名を入力
        preset_name, ok = QtWidgets.QInputDialog.getText(
            self, "フレーズプリセット追加", "フレーズプリセット名を入力してください:"
        )

        if not ok or not preset_name:
            return

        # 新しいフレーズプリセットを作成
        new_preset = {
            'name': preset_name,
            'unique_id': self.get_next_available_id(work),  # 次に利用可能な番号IDを追加
            'phrase_data': [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}],
            'match_mode': 'any',
            'dag_only': False,
            'use_common_filter': True,
            'use_common_dialog': False,  # 共通ダイアログを使用するかのフラグ
            'dialog_open': False,  # 専用ダイアログの開閉状態
            'common_dialog_open': False  # 共通ダイアログの開閉状態
        }

        if 'phrase_presets' not in work:
            work['phrase_presets'] = []

        work['phrase_presets'].append(new_preset)

        # ボタンを作成
        self.create_phrase_preset_button(len(work['phrase_presets']) - 1)

        # 新しいプリセットに切り替え
        self.switch_to_phrase_preset(len(work['phrase_presets']) - 1)

        # 設定を保存
        self.save_settings()

    def on_remove_phrase_preset(self):
        """現在のフレーズプリセットを削除"""
        work = self.get_current_work_preset()
        if not work or self.current_phrase_preset_index < 0:
            return

        phrase_presets = work.get('phrase_presets', [])
        if len(phrase_presets) <= 1:
            import maya.cmds as cmds
            cmds.warning("最低1つのフレーズプリセットが必要です")
            return

        preset_name = phrase_presets[self.current_phrase_preset_index]['name']
        reply = QtWidgets.QMessageBox.question(
            self, "確認",
            f"フレーズプリセット '{preset_name}' を削除しますか？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # フレーズプリセットを削除
            del phrase_presets[self.current_phrase_preset_index]

            # ボタンを削除
            btn = self.phrase_preset_buttons[self.current_phrase_preset_index]
            self.phrase_preset_buttons_layout.removeWidget(btn)
            btn.deleteLater()
            del self.phrase_preset_buttons[self.current_phrase_preset_index]

            # インデックスを調整
            if self.current_phrase_preset_index >= len(phrase_presets):
                self.current_phrase_preset_index = len(phrase_presets) - 1

            # 別のプリセットに切り替え
            self.switch_to_phrase_preset(self.current_phrase_preset_index)

            # 設定を保存
            self.save_settings()

            print(f"フレーズプリセット '{preset_name}' を削除しました")

    def on_duplicate_phrase_preset(self):
        """現在のフレーズプリセットを複製"""
        work = self.get_current_work_preset()
        if not work or self.current_phrase_preset_index < 0:
            return

        phrase_presets = work.get('phrase_presets', [])
        original_preset = phrase_presets[self.current_phrase_preset_index]
        original_name = original_preset['name']

        # 新しい名前を生成
        counter = 1
        new_name = f"{original_name}_copy"
        while any(p['name'] == new_name for p in phrase_presets):
            new_name = f"{original_name}_copy{counter}"
            counter += 1

        # フレーズプリセットを複製
        new_preset = copy.deepcopy(original_preset)
        new_preset['name'] = new_name

        phrase_presets.append(new_preset)

        # ボタンを作成
        self.create_phrase_preset_button(len(phrase_presets) - 1)

        # 新しいフレーズプリセットに切り替え
        self.switch_to_phrase_preset(len(phrase_presets) - 1)

        # 設定を保存
        self.save_settings()

        print(f"フレーズプリセット '{new_name}' を作成しました")
