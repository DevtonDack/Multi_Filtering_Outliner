# -*- coding: utf-8 -*-
"""
PresetImportExportMixin - Preset file import/export operations
"""

from PySide6 import QtWidgets
import json
import os
from ui.dialogs import PresetImportDialog


class PresetImportExportMixin:
    """プリセットのインポート/エクスポート機能を提供するMixin"""

    # ========== Export Methods ==========

    def export_preset(self):
        """現在選択中の作業プリセットをファイルに書き出し"""
        work = self.get_current_work_preset()
        if not work:
            QtWidgets.QMessageBox.warning(
                self,
                "警告",
                "作業プリセットが選択されていません"
            )
            return

        # 現在の状態を保存
        self.save_current_work_state()

        # 初期ディレクトリを決定
        initial_dir = self.last_export_path if self.last_export_path else os.path.expanduser("~")

        # デフォルトのファイル名を作業プリセット名に設定
        default_filename = f"{work.get('name', 'preset')}.json"
        initial_path = os.path.join(initial_dir, default_filename)

        # ファイルダイアログでファイルパスを取得
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "作業プリセットを書き出し",
            initial_path,
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # 現在の作業プリセットのみを保存
            export_data = {
                'version': 2,
                'work_preset': work
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            # 最後に使用したパスを保存（ディレクトリ部分のみ）
            self.last_export_path = os.path.dirname(file_path)

            print(f"作業プリセット '{work.get('name')}' を書き出しました: {file_path}")
            QtWidgets.QMessageBox.information(
                self,
                "完了",
                f"作業プリセット '{work.get('name')}' を書き出しました"
            )

        except Exception as e:
            print(f"プリセットの書き出しに失敗: {e}")
            QtWidgets.QMessageBox.warning(
                self,
                "エラー",
                f"プリセットの書き出しに失敗しました:\n{e}"
            )

    def import_preset(self):
        """ファイルから作業プリセットを読み込み"""
        model = self.get_current_model()
        if not model:
            QtWidgets.QMessageBox.warning(
                self,
                "警告",
                "先にプロジェクトとモデルを選択してください"
            )
            return

        # 初期ディレクトリを決定
        initial_dir = self.last_import_path if self.last_import_path else os.path.expanduser("~")

        # 複数ファイル選択可能なダイアログ
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "作業プリセットを読み込み（複数選択可）",
            initial_dir,
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_paths:
            return

        try:
            # 複数ファイルの場合は一括処理モードを確認
            if len(file_paths) > 1:
                self.import_multiple_presets(file_paths, model)
            else:
                self.import_single_preset(file_paths[0], model)

            self.last_import_path = os.path.dirname(file_paths[0])
            self.save_settings()

        except json.JSONDecodeError as e:
            print(f"プリセットの読み込みに失敗（JSON解析エラー）: {e}")
            QtWidgets.QMessageBox.warning(
                self,
                "エラー",
                f"JSONファイルの解析に失敗しました:\n{e}"
            )
        except Exception as e:
            print(f"プリセットの読み込みに失敗: {e}")
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.warning(
                self,
                "エラー",
                f"プリセットの読み込みに失敗しました:\n{e}"
            )

    def import_single_preset(self, file_path, model):
        """単一ファイルのインポート（現在のプリセットを更新/新規追加を選択）"""
        import copy

        with open(file_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)

        # 作業プリセットデータを取得
        work_preset = import_data.get('work_preset')
        if not work_preset:
            QtWidgets.QMessageBox.warning(
                self,
                "エラー",
                "作業プリセットデータが見つかりません"
            )
            return

        # 現在の作業プリセットがあるか確認
        current_work = self.get_current_work_preset()

        # ダイアログで選択
        dialog = QtWidgets.QMessageBox(self)
        dialog.setWindowTitle("インポート方法を選択")
        dialog.setText(f"作業プリセット '{work_preset.get('name')}' をインポートします")
        dialog.setInformativeText("インポート方法を選択してください")

        update_btn = None
        if current_work:
            update_btn = dialog.addButton(f"現在のプリセット '{current_work.get('name')}' を更新", QtWidgets.QMessageBox.AcceptRole)
        new_btn = dialog.addButton("新規プリセットとして追加", QtWidgets.QMessageBox.AcceptRole)
        cancel_btn = dialog.addButton("キャンセル", QtWidgets.QMessageBox.RejectRole)

        dialog.exec_()

        clicked = dialog.clickedButton()

        if clicked == cancel_btn or clicked is None:
            return

        if clicked == update_btn and current_work:
            # 現在のプリセットを更新
            current_work.update(copy.deepcopy(work_preset))
            # 名前は保持
            if 'name' in work_preset:
                current_work['name'] = work_preset['name']
            self.load_work_to_ui(self.current_work_index)
            QtWidgets.QMessageBox.information(
                self,
                "完了",
                f"作業プリセット '{current_work.get('name')}' を更新しました"
            )
        else:
            # 新規プリセットとして追加
            new_work = copy.deepcopy(work_preset)
            # 同名チェック
            existing_names = [w.get('name', '') for w in model.get('works', [])]
            base_name = new_work.get('name', '新規プリセット')
            counter = 1
            new_name = base_name
            while new_name in existing_names:
                new_name = f"{base_name}_{counter}"
                counter += 1
            new_work['name'] = new_name

            model.setdefault('works', []).append(new_work)
            self.update_work_buttons()
            # 新しいプリセットに切り替え
            new_index = len(model['works']) - 1
            self.switch_to_work(new_index)
            QtWidgets.QMessageBox.information(
                self,
                "完了",
                f"作業プリセット '{new_name}' を追加しました"
            )

    def import_multiple_presets(self, file_paths, model):
        """複数ファイルのインポート（同名置き換え/すべて新規を選択）"""
        import copy

        # インポート方法を選択
        dialog = QtWidgets.QMessageBox(self)
        dialog.setWindowTitle("複数ファイルのインポート")
        dialog.setText(f"{len(file_paths)}個のファイルをインポートします")
        dialog.setInformativeText("インポート方法を選択してください")

        replace_btn = dialog.addButton("同名の作業プリセットを置き換え", QtWidgets.QMessageBox.AcceptRole)
        new_all_btn = dialog.addButton("すべて新規プリセットとして追加", QtWidgets.QMessageBox.AcceptRole)
        cancel_btn = dialog.addButton("キャンセル", QtWidgets.QMessageBox.RejectRole)

        dialog.exec_()

        clicked = dialog.clickedButton()

        if clicked == cancel_btn or clicked is None:
            return

        replace_mode = (clicked == replace_btn)
        imported_count = 0
        replaced_count = 0

        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)

                work_preset = import_data.get('work_preset')
                if not work_preset:
                    continue

                preset_name = work_preset.get('name', 'プリセット')

                if replace_mode:
                    # 同名のプリセットを探す
                    found = False
                    for i, work in enumerate(model.get('works', [])):
                        if work.get('name') == preset_name:
                            # 置き換え
                            model['works'][i] = copy.deepcopy(work_preset)
                            found = True
                            replaced_count += 1
                            break

                    if not found:
                        # 同名がなければ新規追加
                        model.setdefault('works', []).append(copy.deepcopy(work_preset))
                        imported_count += 1
                else:
                    # すべて新規追加（同名の場合は番号付与）
                    existing_names = [w.get('name', '') for w in model.get('works', [])]
                    new_name = preset_name
                    counter = 1
                    while new_name in existing_names:
                        new_name = f"{preset_name}_{counter}"
                        counter += 1
                    work_preset['name'] = new_name
                    model.setdefault('works', []).append(copy.deepcopy(work_preset))
                    imported_count += 1

            except Exception as e:
                print(f"ファイル {file_path} の読み込みに失敗: {e}")

        self.update_work_buttons()

        # 結果を表示
        if replace_mode:
            message = f"{replaced_count}個のプリセットを置き換え、{imported_count}個のプリセットを新規追加しました"
        else:
            message = f"{imported_count}個のプリセットを新規追加しました"

        QtWidgets.QMessageBox.information(self, "完了", message)
