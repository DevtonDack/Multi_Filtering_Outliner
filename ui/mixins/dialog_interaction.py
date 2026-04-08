# -*- coding: utf-8 -*-
"""
DialogInteractionMixin - Dialog and node interaction operations
"""

from PySide6 import QtWidgets, QtCore
from ui.dialogs import NodeListDialog, CommonNodeListDialog


class DialogInteractionMixin:
    """ダイアログとノード操作のインタラクションを提供するMixin"""

    # ========== Dialog Opening Methods ==========

    def on_open_dialog(self):
        """ノードリストをダイアログで開く（プリセットごとに独立）"""
        # 現在のフレーズプリセットの状態を保存（最新の設定をダイアログに反映させるため）
        if self.current_phrase_preset_index >= 0:
            self.save_current_phrase_preset_state()

        if not self.current_nodes:
            import maya.cmds as cmds
            cmds.warning("表示するノードがありません")
            return

        # 現在の作業プリセット名とインデックスを取得
        work_preset = self.get_current_work_preset()
        if work_preset:
            work_name = work_preset.get('name', 'Unknown')
            # 階層インデックスを保存（プロジェクト、モデル、作業）
            work_indices = (self.current_project_index, self.current_model_index, self.current_work_index)
        else:
            work_name = "Unknown"
            work_indices = (-1, -1, -1)

        # 現在のフレーズプリセット名を取得
        phrase_preset = self.get_current_phrase_preset()
        if phrase_preset:
            phrase_name = phrase_preset.get('name', 'Unknown')
            phrase_index = self.current_phrase_preset_index
        else:
            phrase_name = "Unknown"
            phrase_index = -1

        # ダイアログの一意なキーを作成（作業プリセット + フレーズプリセット）
        dialog_key = f"{work_name}::{phrase_name}"
        # ダイアログのタイトルを作成
        dialog_title = f"{work_name} - {phrase_name}"

        # 既存のダイアログがあれば、それを前面に表示するか更新
        if dialog_key in self.node_dialogs and self.node_dialogs[dialog_key].isVisible():
            # 既存のダイアログを更新して前面に表示
            self.node_dialogs[dialog_key].nodes = self.current_nodes
            self.node_dialogs[dialog_key].update_nodes()
            self.node_dialogs[dialog_key].raise_()
            self.node_dialogs[dialog_key].activateWindow()
        else:
            # 新しいダイアログを作成してモードレス表示
            dialog = NodeListDialog(
                self.current_nodes,
                list_name=dialog_title,
                work_indices=work_indices,
                phrase_index=phrase_index,
                dialog_key=dialog_key,
                parent_widget=self,
                parent=self
            )
            self.node_dialogs[dialog_key] = dialog

            # ダイアログが開かれたことを記録
            if phrase_preset:
                phrase_preset['dialog_open'] = True

            dialog.show()

    def on_open_common_dialog(self):
        """共通ノードリストダイアログで開く（作業プリセット間で共有）"""
        # 現在のフレーズプリセットの状態を保存
        if self.current_phrase_preset_index >= 0:
            self.save_current_phrase_preset_state()

        phrase_preset = self.get_current_phrase_preset()
        if not phrase_preset:
            QtWidgets.QMessageBox.warning(self, "警告", "フレーズプリセットが選択されていません")
            return

        unique_id = phrase_preset.get('unique_id')
        if not unique_id:
            QtWidgets.QMessageBox.warning(self, "警告", "このフレーズプリセットにはユニークIDが設定されていません")
            return

        # 既存の共通ダイアログがあれば、それを前面に表示
        if unique_id in self.common_dialogs:
            try:
                # ダイアログが有効かチェック
                dialog = self.common_dialogs[unique_id]
                dialog.windowTitle()  # 削除されていたらRuntimeErrorが発生

                if dialog.isVisible():
                    # 既存のダイアログを前面に表示
                    dialog.on_refresh()
                    dialog.raise_()
                    dialog.activateWindow()

                    # アクティブにならない場合は強制的に表示
                    if not dialog.isActiveWindow():
                        dialog.show()
                        dialog.raise_()
                        dialog.activateWindow()
                    return
                else:
                    # 非表示のダイアログは削除して再作成
                    del self.common_dialogs[unique_id]
            except (RuntimeError, AttributeError):
                # 無効なダイアログは削除
                del self.common_dialogs[unique_id]

        # 新しい共通ダイアログを作成
        try:
            dialog = CommonNodeListDialog(
                unique_id=unique_id,
                parent_widget=self,
                parent=self
            )
            self.common_dialogs[unique_id] = dialog
            phrase_preset['use_common_dialog'] = True
            phrase_preset['common_dialog_open'] = True
            self.save_settings()
            dialog.show()
        except Exception as e:
            print(f"[ERROR] 共通ダイアログの作成中にエラー: {e}")
            import traceback
            traceback.print_exc()

    # ========== Node Interaction Methods ==========

    def on_node_double_clicked(self, item):
        """ノードがダブルクリックされた時（ノード名をクリップボードにコピー）"""
        import maya.cmds as cmds
        node_name = item.text()
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(node_name)
        # 画面中央に通知を表示
        cmds.inViewMessage(amg=f'<span style="color:#00ff00;">ノード名をコピーしました: {node_name}</span>',
                          pos='topCenter', fade=True, fadeStayTime=1000, fadeOutTime=500)
        print(f"ノード名をコピーしました: {node_name}")

    def show_context_menu(self, position):
        """コンテキストメニューを表示"""
        item = self.node_list.itemAt(position)
        if not item:
            return

        menu = QtWidgets.QMenu()

        # コピーアクション
        copy_action = menu.addAction("ノード名をコピー")
        copy_action.triggered.connect(lambda: self.copy_node_name(item))

        # 選択アクション
        select_action = menu.addAction("Mayaで選択")
        select_action.triggered.connect(lambda: self.select_node_in_maya(item))

        # メニューを表示
        menu.exec_(self.node_list.mapToGlobal(position))

    def copy_node_name(self, item):
        """ノード名をクリップボードにコピー"""
        node_name = item.text()
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(node_name)
        print(f"ノード名をコピーしました: {node_name}")

    def select_node_in_maya(self, item):
        """Mayaでノードを選択"""
        import maya.cmds as cmds
        node_path = item.data(QtCore.Qt.UserRole)
        if cmds.objExists(node_path):
            cmds.select(node_path, replace=True)
            print(f"選択しました: {item.text()}")
