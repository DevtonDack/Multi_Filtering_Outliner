# -*- coding: utf-8 -*-
"""
PresetIDManagerMixin - Preset unique ID validation and management
"""


class PresetIDManagerMixin:
    """プリセットのユニークID管理を提供するMixin"""

    # ========== ID Validation and Duplicate Checking ==========

    def check_id_duplicate(self):
        """IDの重複をチェックして視覚的フィードバックを提供"""
        current_id = self.preset_id_input.text().strip()
        if not current_id:
            self.preset_id_input.setStyleSheet("")
            return

        work = self.get_current_work_preset()
        if not work:
            self.preset_id_input.setStyleSheet("")
            return

        # 重複チェック
        duplicate_found = False
        for i, preset in enumerate(work.get('phrase_presets', [])):
            if i != self.current_phrase_preset_index and preset.get('unique_id') == current_id:
                duplicate_found = True
                break

        # 視覚的フィードバック
        if duplicate_found:
            self.preset_id_input.setStyleSheet("QLineEdit { background-color: rgb(100, 70, 70); }")
        else:
            self.preset_id_input.setStyleSheet("")

    # ========== ID Change Handlers ==========

    def on_preset_id_changed(self):
        """プリセットID変更時の処理"""
        if self._is_loading:
            return

        new_id = self.preset_id_input.text().strip()
        phrase_preset = self.get_current_phrase_preset()
        if not phrase_preset:
            return

        # IDが空の場合は新規生成
        if not new_id:
            new_id = self.get_next_available_id()
            self.preset_id_input.setText(new_id)
            return

        # 数字以外が含まれている場合（バリデーターを通過していないはずだが念のため）
        if not new_id.isdigit():
            print(f"警告: 数字以外のID '{new_id}' が検出されました。数字形式に変換します。")
            new_id = self.get_next_available_id()
            self.preset_id_input.setText(new_id)
            return

        # IDの重複チェック
        work = self.get_current_work_preset()
        if work:
            duplicate_found = False
            for i, preset in enumerate(work.get('phrase_presets', [])):
                if i != self.current_phrase_preset_index and preset.get('unique_id') == new_id:
                    duplicate_found = True
                    break

            # 重複警告（視覚的フィードバック）
            if duplicate_found:
                self.preset_id_input.setStyleSheet("QLineEdit { background-color: rgb(100, 70, 70); }")
            else:
                self.preset_id_input.setStyleSheet("")

        # IDを更新
        old_id = phrase_preset.get('unique_id')
        phrase_preset['unique_id'] = new_id

        # 共通ダイアログが開いている場合は更新
        if old_id and old_id in self.common_dialogs:
            dialog = self.common_dialogs[old_id]
            if new_id != old_id:
                # IDが変わった場合、ダイアログを移動
                del self.common_dialogs[old_id]
                dialog.unique_id = new_id
                self.common_dialogs[new_id] = dialog
                dialog.on_refresh()

        self.save_settings()

    def on_preset_id_editing_finished(self):
        """ID入力フィールドの編集が完了した時（フォーカスが外れた時やEnterキーを押した時）"""
        # on_preset_id_changed で既に処理されているので、追加の処理は不要
        # このシグナルは主にフォーカスが外れたときに確実に処理を完了させるため
        pass

    # ========== Global Unique ID Generation ==========

    def get_globally_unique_id(self):
        """すべてのプロジェクト・モデル・作業プリセットを通してグローバルにユニークな番号IDを取得"""
        used_ids = set()

        # すべてのプロジェクト・モデル・作業プリセットからIDを収集
        for project in self.projects:
            for model in project.get('models', []):
                for work in model.get('works', []):
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
