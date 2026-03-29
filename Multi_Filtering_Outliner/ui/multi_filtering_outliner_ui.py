# -*- coding: utf-8 -*-
"""
Multi Filtering Outliner UI - PySide6版
シーン内のノードをフレーズでフィルタリングして表示
"""

from PySide6 import QtWidgets, QtCore, QtGui
import json
import os
from ..tools import multi_filtering_outliner
import sys


# 設定ファイルのパス
SETTINGS_DIR = os.path.expanduser("~/.multi_filtering_outliner")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "multi_filtering_outliner_settings.json")


# main.pyのFlowLayoutをインポート
try:
    # EZ_ModelingTools.mainから絶対インポート
    from EZ_ModelingTools.main import FlowLayout
except ImportError:
    # フォールバック: シンプルなHBoxLayoutを使用
    FlowLayout = None
    print("Warning: FlowLayout could not be imported from main.py")




class EditableButton(QtWidgets.QPushButton):
    """ダブルクリックで編集可能、ドラッグ&ドロップで並べ替え可能なボタン"""

    name_changed = QtCore.Signal(str)  # 名前変更シグナル

    def __init__(self, text, parent=None):
        super(EditableButton, self).__init__(text, parent)
        self.setCheckable(True)
        self.setMinimumHeight(30)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.setAcceptDrops(True)

        # ドラッグ開始位置を記録
        self._drag_start_position = None

        # スタイルシートを設定（選択時は青色、未選択時は濃いグレー）
        self.setStyleSheet("""
            QPushButton {
                background-color: rgb(60, 60, 70);
                color: white;
                border: 1px solid rgb(80, 80, 90);
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgb(70, 70, 80);
            }
            QPushButton:checked {
                background-color: rgb(50, 100, 180);
                border: 2px solid rgb(70, 120, 200);
            }
            QPushButton:checked:hover {
                background-color: rgb(60, 110, 190);
            }
        """)

        self._adjust_width()

    def _adjust_width(self):
        """テキストに合わせて幅を調整"""
        fm = QtGui.QFontMetrics(self.font())
        text_width = fm.horizontalAdvance(self.text())
        # パディングを含めた幅を設定
        self.setMinimumWidth(text_width + 20)
        self.setMaximumWidth(text_width + 20)

    def mousePressEvent(self, event):
        """マウス押下時にドラッグ開始位置を記録"""
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_position = event.pos()
        super(EditableButton, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """マウス移動時にドラッグを開始"""
        if not (event.buttons() & QtCore.Qt.LeftButton):
            return
        if self._drag_start_position is None:
            return
        if (event.pos() - self._drag_start_position).manhattanLength() < QtWidgets.QApplication.startDragDistance():
            return

        # ドラッグ開始
        drag = QtGui.QDrag(self)
        mime_data = QtCore.QMimeData()
        mime_data.setText(self.text())
        drag.setMimeData(mime_data)

        # ドラッグ中の表示
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())

        drag.exec_(QtCore.Qt.MoveAction)

    def dragEnterEvent(self, event):
        """ドラッグエンター時"""
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """ドロップ時にボタンを入れ替え"""
        if event.mimeData().hasText():
            event.accept()
            # 親ウィジェットに通知（実際の入れ替え処理は親で行う）
            event.source().swap_with = self
        else:
            event.ignore()

    def mouseDoubleClickEvent(self, event):
        """ダブルクリックで名前編集"""
        if event.button() == QtCore.Qt.LeftButton:
            new_name, ok = QtWidgets.QInputDialog.getText(
                self, "リスト名編集", "新しいリスト名を入力してください:",
                text=self.text()
            )

            if ok and new_name and new_name != self.text():
                self.setText(new_name)
                self._adjust_width()
                self.name_changed.emit(new_name)

        super(EditableButton, self).mouseDoubleClickEvent(event)


class DraggablePhraseWidget(QtWidgets.QWidget):
    """ドラッグ&ドロップ可能なフレーズ行ウィジェット"""

    def __init__(self, text='', enabled=True, exclude=False, exact_token=False, parent=None):
        super(DraggablePhraseWidget, self).__init__(parent)
        self.setAcceptDrops(True)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)

        # チェックボックス（有効/無効）
        self.enabled_check = QtWidgets.QCheckBox()
        self.enabled_check.setChecked(enabled)
        self.enabled_check.setFixedWidth(20)
        self.enabled_check.setToolTip("フィルターに使用")
        layout.addWidget(self.enabled_check)

        # 除外チェックボックス
        self.exclude_check = QtWidgets.QCheckBox()
        self.exclude_check.setChecked(exclude)
        self.exclude_check.setFixedWidth(20)
        self.exclude_check.setToolTip("除外フィルター")
        layout.addWidget(self.exclude_check)

        # トークン完全一致チェックボックス
        self.exact_token_check = QtWidgets.QCheckBox()
        self.exact_token_check.setChecked(exact_token)
        self.exact_token_check.setFixedWidth(20)
        self.exact_token_check.setToolTip("_区切りで完全一致")
        layout.addWidget(self.exact_token_check)

        # ドラッグハンドル
        drag_label = QtWidgets.QLabel("⋮⋮")
        drag_label.setStyleSheet("color: gray; font-weight: bold;")
        drag_label.setFixedWidth(20)
        drag_label.setCursor(QtCore.Qt.OpenHandCursor)
        layout.addWidget(drag_label)

        # フレーズ入力
        self.phrase_input = QtWidgets.QLineEdit()
        self.phrase_input.setPlaceholderText("フレーズを入力")
        self.phrase_input.setText(text)
        layout.addWidget(self.phrase_input)

        # 削除ボタン
        self.remove_btn = QtWidgets.QPushButton("✕")
        self.remove_btn.setFixedWidth(30)
        layout.addWidget(self.remove_btn)

        self.drag_start_position = None

        # 除外モード時の背景色を更新
        self.exclude_check.stateChanged.connect(self.update_background_color)
        self.update_background_color()

    def update_background_color(self):
        """除外モードに応じて背景色を更新"""
        if self.exclude_check.isChecked():
            self.phrase_input.setStyleSheet("background-color: rgb(120, 60, 60);")
        else:
            self.phrase_input.setStyleSheet("")

    def mousePressEvent(self, event):
        """マウスプレスイベント"""
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_start_position = event.pos()
        super(DraggablePhraseWidget, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """マウス移動イベント - ドラッグ開始"""
        if not (event.buttons() & QtCore.Qt.LeftButton):
            return
        if not self.drag_start_position:
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QtWidgets.QApplication.startDragDistance():
            return

        drag = QtGui.QDrag(self)
        mime_data = QtCore.QMimeData()
        mime_data.setText("phrase_widget")
        drag.setMimeData(mime_data)

        # ドラッグ中の見た目
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())

        drag.exec_(QtCore.Qt.MoveAction)

    def dragEnterEvent(self, event):
        """ドラッグエンターイベント"""
        if event.mimeData().hasText() and event.mimeData().text() == "phrase_widget":
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """ドロップイベント"""
        if event.mimeData().hasText() and event.mimeData().text() == "phrase_widget":
            event.setDropAction(QtCore.Qt.MoveAction)
            event.accept()

            # 親ウィジェット（NodeFilterWidget）に通知
            source_widget = event.source()
            if source_widget and source_widget != self:
                parent_widget = self.parent()
                while parent_widget and not isinstance(parent_widget, NodeFilterWidget):
                    parent_widget = parent_widget.parent()
                if parent_widget:
                    parent_widget.swap_phrase_rows(source_widget, self)
        else:
            event.ignore()


class PresetImportDialog(QtWidgets.QDialog):
    """プリセットインポート時の選択ダイアログ（リスト形式）"""

    def __init__(self, presets_to_import, existing_names, parent=None):
        super(PresetImportDialog, self).__init__(parent)
        self.presets_to_import = presets_to_import
        self.existing_names = existing_names
        self.preset_rows = []  # {name, overwrite_check, rename_check, skip_check}のリスト
        self.setWindowTitle("プリセットの読み込み")
        self.setMinimumSize(500, 400)
        self.create_ui()

    def create_ui(self):
        """UIを作成"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # メッセージ
        message = QtWidgets.QLabel(
            f"{len(self.presets_to_import)}個のプリセットが見つかりました。\n"
            f"各プリセットの読み込み方法を選択してください。"
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        # スクロールエリア
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(200)

        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(5)
        scroll_layout.setContentsMargins(5, 5, 5, 5)

        # ヘッダー
        header_layout = QtWidgets.QHBoxLayout()
        header_name = QtWidgets.QLabel("プリセット名")
        header_name.setMinimumWidth(150)
        header_name.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(header_name)

        header_overwrite = QtWidgets.QLabel("上書き")
        header_overwrite.setFixedWidth(60)
        header_overwrite.setAlignment(QtCore.Qt.AlignCenter)
        header_overwrite.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(header_overwrite)

        header_rename = QtWidgets.QLabel("増分")
        header_rename.setFixedWidth(60)
        header_rename.setAlignment(QtCore.Qt.AlignCenter)
        header_rename.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(header_rename)

        header_skip = QtWidgets.QLabel("スキップ")
        header_skip.setFixedWidth(70)
        header_skip.setAlignment(QtCore.Qt.AlignCenter)
        header_skip.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(header_skip)

        scroll_layout.addLayout(header_layout)

        # 区切り線
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        scroll_layout.addWidget(line)

        # 各プリセットの行を作成
        for preset_data in self.presets_to_import:
            preset_name = preset_data.get('name', 'Unknown')
            is_existing = preset_name in self.existing_names

            row_layout = QtWidgets.QHBoxLayout()
            row_layout.setSpacing(5)

            # プリセット名
            name_label = QtWidgets.QLabel(preset_name)
            name_label.setMinimumWidth(150)
            if is_existing:
                name_label.setStyleSheet("color: orange;")
            row_layout.addWidget(name_label)

            # ラジオボタングループ
            button_group = QtWidgets.QButtonGroup(self)

            # 上書きチェックボックス
            overwrite_check = QtWidgets.QRadioButton()
            overwrite_check.setFixedWidth(60)
            overwrite_check.setEnabled(is_existing)
            button_group.addButton(overwrite_check)
            row_layout.addWidget(overwrite_check, 0, QtCore.Qt.AlignCenter)

            # 増分チェックボックス
            rename_check = QtWidgets.QRadioButton()
            rename_check.setFixedWidth(60)
            rename_check.setChecked(True)  # デフォルト
            button_group.addButton(rename_check)
            row_layout.addWidget(rename_check, 0, QtCore.Qt.AlignCenter)

            # スキップチェックボックス
            skip_check = QtWidgets.QRadioButton()
            skip_check.setFixedWidth(70)
            button_group.addButton(skip_check)
            row_layout.addWidget(skip_check, 0, QtCore.Qt.AlignCenter)

            scroll_layout.addLayout(row_layout)

            # 行情報を保存
            self.preset_rows.append({
                'name': preset_name,
                'data': preset_data,
                'overwrite': overwrite_check,
                'rename': rename_check,
                'skip': skip_check,
                'is_existing': is_existing
            })

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # ボタンエリア
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QtWidgets.QPushButton("キャンセル")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = QtWidgets.QPushButton("OK")
        ok_btn.setFixedWidth(100)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

    def get_import_choices(self):
        """各プリセットの読み込み方法を取得"""
        choices = []
        for row in self.preset_rows:
            if row['overwrite'].isChecked():
                mode = 'overwrite'
            elif row['rename'].isChecked():
                mode = 'rename'
            elif row['skip'].isChecked():
                mode = 'skip'
            else:
                mode = 'rename'  # デフォルト

            choices.append({
                'name': row['name'],
                'data': row['data'],
                'mode': mode
            })
        return choices


class NodeListDialog(QtWidgets.QDialog):
    """ノードリスト表示用のダイアログ"""

    def __init__(self, nodes, list_name="", work_indices=None, phrase_index=-1, dialog_key="", parent_widget=None, parent=None):
        # Mayaのメインウィンドウを親として取得
        if parent is None:
            try:
                from maya import OpenMayaUI as omui
                from shiboken6 import wrapInstance
                maya_main_window_ptr = omui.MQtUtil.mainWindow()
                parent = wrapInstance(int(maya_main_window_ptr), QtWidgets.QWidget)
            except:
                pass

        super(NodeListDialog, self).__init__(parent)

        self.nodes = nodes
        self.list_name = list_name  # リスト名（表示用タイトル）
        # 階層インデックス (project_index, model_index, work_index)
        self.work_indices = work_indices if work_indices else (-1, -1, -1)
        self.phrase_index = phrase_index  # フレーズプリセットインデックス
        self.dialog_key = dialog_key  # ダイアログの一意なキー
        self.parent_widget = parent_widget  # NodeFilterWidgetへの参照

        # ウィンドウフラグを設定（タイトルの前に設定する必要がある）
        self.setWindowFlags(QtCore.Qt.Window)

        # ウィンドウタイトルを設定（setWindowFlagsの後に設定）
        # list_nameには既に完全なタイトル（"作業名 - フレーズ名"）が入っている
        window_title = list_name if list_name else "ノードリスト"
        self.setWindowTitle(window_title)
        self.setMinimumWidth(400)
        # モードレスダイアログに設定（他の操作を可能にする）
        self.setWindowModality(QtCore.Qt.NonModal)
        self.create_ui()

        # ジオメトリを復元
        self.restore_geometry()

        # 初回のリフレッシュを実行（フレーズプリセットの設定でフィルタリング）
        # これにより、メインウィンドウから渡されたノードではなく、
        # このダイアログ専用のフレーズプリセット設定でノードを表示する
        self.on_refresh()

        # 自動更新タイマーを設定（1秒ごとにチェック）
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.timeout.connect(self.auto_refresh)
        self.update_timer.start(1000)  # 1秒ごと

    def create_ui(self):
        """UIを作成"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # タイトル
        self.title_label = QtWidgets.QLabel(f"ノードリスト ({len(self.nodes)}個)")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(self.title_label)

        # ノードリスト
        self.node_list = QtWidgets.QListWidget()
        self.node_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.node_list.itemDoubleClicked.connect(self.on_node_double_clicked)
        self.node_list.itemSelectionChanged.connect(self.on_selection_changed)
        # コンテキストメニューを有効化
        self.node_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.node_list.customContextMenuRequested.connect(self.show_context_menu)

        # ノードをアルファベット順で追加
        for node in self.nodes:
            short_name = node.split('|')[-1]
            item = QtWidgets.QListWidgetItem(short_name)
            item.setData(QtCore.Qt.UserRole, node)  # フルパスを保存
            self.node_list.addItem(item)

        layout.addWidget(self.node_list)

    def on_node_double_clicked(self, item):
        """ノードをダブルクリックした時（ノード名をクリップボードにコピー）"""
        import maya.cmds as cmds
        node_name = item.text()
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(node_name)
        # 画面中央に通知を表示
        cmds.inViewMessage(amg=f'<span style="color:#00ff00;">ノード名をコピーしました: {node_name}</span>',
                          pos='topCenter', fade=True, fadeStayTime=1000, fadeOutTime=500)
        print(f"ノード名をコピーしました: {node_name}")

    def on_selection_changed(self):
        """リストの選択が変更された時"""
        import maya.cmds as cmds
        selected_items = self.node_list.selectedItems()
        if not selected_items:
            return

        nodes = []
        for item in selected_items:
            node_path = item.data(QtCore.Qt.UserRole)
            if cmds.objExists(node_path):
                nodes.append(node_path)

        if nodes:
            cmds.select(nodes, replace=True)

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

    def on_refresh(self):
        """ノードリストを更新（このダイアログのフレーズプリセットで再フィルタリング）"""
        if not self.parent_widget:
            return

        project_idx, model_idx, work_idx = self.work_indices

        if project_idx < 0 or model_idx < 0 or work_idx < 0:
            return

        if self.phrase_index < 0:
            return

        # このダイアログの作業プリセットを取得
        if project_idx >= len(self.parent_widget.projects):
            return

        project = self.parent_widget.projects[project_idx]
        models = project.get('models', [])

        if model_idx >= len(models):
            return

        model = models[model_idx]
        works = model.get('works', [])

        if work_idx >= len(works):
            return

        work_data = works[work_idx]

        # このダイアログのフレーズプリセットを取得
        phrase_presets = work_data.get('phrase_presets', [])
        if self.phrase_index >= len(phrase_presets):
            return

        phrase_preset = phrase_presets[self.phrase_index]

        # フレーズ設定を収集
        from ..tools import multi_filtering_outliner as nf

        # 共通フィルターを取得（包含/除外を分ける）
        common_include_configs = []
        common_exclude_configs = []
        use_common_filter = phrase_preset.get('use_common_filter', True)
        if use_common_filter:
            for data in work_data.get('common_filters', []):
                if isinstance(data, dict) and data.get('enabled', True):
                    text = data.get('text', '').strip()
                    if text:
                        config = {
                            'text': text,
                            'exact_token': data.get('exact_token', False)
                        }
                        if data.get('exclude', False):
                            common_exclude_configs.append(config)
                        else:
                            common_include_configs.append(config)

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

        # メインウィンドウと同じフィルタリングロジックを適用
        # 1. まず共通フィルターを適用（共通フィルター使用が有効な場合のみ）
        if use_common_filter and common_include_configs:
            # 共通フィルターで最初のフィルタリング（常に'all'モード - すべての共通フィルターに一致）
            matched_nodes = nf.filter_nodes_by_phrase_configs(common_include_configs, 'all')
        else:
            # 共通フィルターがない、または使用しない場合はすべてのノードから開始
            matched_nodes = nf.get_all_nodes()

        # 2. 共通フィルターの除外を適用（共通フィルター使用が有効な場合のみ）
        if use_common_filter and common_exclude_configs:
            common_excluded_nodes = nf.filter_nodes_by_phrase_configs(common_exclude_configs, 'any')
            matched_nodes = [node for node in matched_nodes if node not in common_excluded_nodes]

        # 3. フレーズプリセットフィルターを適用（共通フィルター結果をさらにフィルター）
        if include_configs:
            # 一時的にすべてのノードを取得する関数を上書き
            original_get_all = nf.get_all_nodes
            nf.get_all_nodes = lambda: matched_nodes

            match_mode = phrase_preset.get('match_mode', 'any')
            matched_nodes = nf.filter_nodes_by_phrase_configs(include_configs, match_mode)

            # 元に戻す
            nf.get_all_nodes = original_get_all

        # 4. フレーズプリセットの除外フィルタリング実行（除外フレーズがある場合）
        if exclude_configs:
            excluded_nodes = nf.filter_nodes_by_phrase_configs(exclude_configs, 'any')
            matched_nodes = [node for node in matched_nodes if node not in excluded_nodes]

        # DAGオブジェクトのみフィルタリング
        dag_only = phrase_preset.get('dag_only', False)
        if dag_only:
            import maya.cmds as cmds
            matched_nodes = [node for node in matched_nodes if cmds.objectType(node, isAType='dagNode')]

        # アルファベット順でソート
        self.nodes = sorted(matched_nodes, key=lambda x: x.split('|')[-1].lower())

        # UIを更新
        self.update_nodes()

    def update_nodes(self):
        """ノードリストを再構築"""
        # 現在の選択状態を保存（フルパスで）
        selected_nodes = []
        for item in self.node_list.selectedItems():
            node_path = item.data(QtCore.Qt.UserRole)
            if node_path:
                selected_nodes.append(node_path)

        # 選択変更シグナルをブロック（更新中のMaya選択を防ぐ）
        self.node_list.blockSignals(True)

        # リストをクリア
        self.node_list.clear()

        # タイトルを更新
        self.title_label.setText(f"ノードリスト ({len(self.nodes)}個)")

        # ノードを追加
        for node in self.nodes:
            short_name = node.split('|')[-1]
            item = QtWidgets.QListWidgetItem(short_name)
            item.setData(QtCore.Qt.UserRole, node)  # フルパスを保存
            self.node_list.addItem(item)

            # 選択状態を復元
            if node in selected_nodes:
                item.setSelected(True)

        # シグナルのブロックを解除
        self.node_list.blockSignals(False)

    def auto_refresh(self):
        """自動更新（定期的に呼ばれる）"""
        # ダイアログが表示されている場合のみ更新
        if not self.isVisible():
            return

        # 自分のプリセット設定で再フィルタリング
        self.on_refresh()

        # Mayaシーン内の選択状態を確認して、ダイアログの選択を同期
        self.sync_selection_with_maya()

    def sync_selection_with_maya(self):
        """Mayaシーン内の選択状態とダイアログの選択を同期"""
        import maya.cmds as cmds

        # Mayaで現在選択されているノードを取得
        maya_selected = set(cmds.ls(selection=True, long=True) or [])

        # シグナルをブロックして選択を更新
        self.node_list.blockSignals(True)

        # ダイアログ内の各アイテムをチェック
        for i in range(self.node_list.count()):
            item = self.node_list.item(i)
            node_path = item.data(QtCore.Qt.UserRole)

            # Mayaで選択されているかどうかで選択状態を設定
            if node_path in maya_selected:
                item.setSelected(True)
            else:
                item.setSelected(False)

        # シグナルのブロックを解除
        self.node_list.blockSignals(False)

    def restore_geometry(self):
        """ダイアログのジオメトリを復元"""
        if not self.parent_widget or self.phrase_index < 0:
            self.resize(400, 500)
            return

        project_idx, model_idx, work_idx = self.work_indices

        if project_idx < 0 or model_idx < 0 or work_idx < 0:
            self.resize(400, 500)
            return

        # 階層をたどって作業プリセットを取得
        try:
            project = self.parent_widget.projects[project_idx]
            model = project['models'][model_idx]
            work_data = model['works'][work_idx]
            phrase_presets = work_data.get('phrase_presets', [])

            if self.phrase_index < len(phrase_presets):
                phrase_preset = phrase_presets[self.phrase_index]
                dialog_geometry = phrase_preset.get('dialog_geometry')

                if dialog_geometry:
                    # 位置とサイズを復元
                    x = dialog_geometry.get('x')
                    y = dialog_geometry.get('y')
                    width = dialog_geometry.get('width', 400)
                    height = dialog_geometry.get('height', 500)

                    if x is not None and y is not None:
                        self.setGeometry(x, y, width, height)
                    else:
                        self.resize(width, height)
                else:
                    self.resize(400, 500)
            else:
                self.resize(400, 500)
        except (IndexError, KeyError):
            self.resize(400, 500)

    def save_geometry(self):
        """ダイアログのジオメトリを保存"""
        if not self.parent_widget or self.phrase_index < 0:
            return

        project_idx, model_idx, work_idx = self.work_indices

        if project_idx < 0 or model_idx < 0 or work_idx < 0:
            return

        # 階層をたどって作業プリセットを取得
        try:
            project = self.parent_widget.projects[project_idx]
            model = project['models'][model_idx]
            work_data = model['works'][work_idx]
            phrase_presets = work_data.get('phrase_presets', [])

            if self.phrase_index < len(phrase_presets):
                phrase_preset = phrase_presets[self.phrase_index]

                # 位置とサイズを保存
                geometry = self.geometry()
                phrase_preset['dialog_geometry'] = {
                    'x': geometry.x(),
                    'y': geometry.y(),
                    'width': geometry.width(),
                    'height': geometry.height()
                }
        except (IndexError, KeyError):
            pass  # エラーは無視

    def closeEvent(self, event):
        """ダイアログが閉じられる時に親から参照を削除"""
        # タイマーを停止
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()

        # ジオメトリを保存
        self.save_geometry()

        # メインウィンドウから閉じられた場合はdialog_openフラグを変更しない
        if not hasattr(self, '_closing_from_main') or not self._closing_from_main:
            # ユーザーが直接閉じた場合のみdialog_openをFalseに設定
            if self.parent_widget and self.phrase_index >= 0:
                project_idx, model_idx, work_idx = self.work_indices
                if project_idx >= 0 and model_idx >= 0 and work_idx >= 0:
                    try:
                        project = self.parent_widget.projects[project_idx]
                        model = project['models'][model_idx]
                        work_data = model['works'][work_idx]
                        phrase_presets = work_data.get('phrase_presets', [])
                        if self.phrase_index < len(phrase_presets):
                            phrase_presets[self.phrase_index]['dialog_open'] = False
                    except (IndexError, KeyError):
                        pass  # エラーは無視

        if self.parent_widget and self.dialog_key:
            # 親ウィジェットの辞書から自分を削除
            if self.dialog_key in self.parent_widget.node_dialogs:
                del self.parent_widget.node_dialogs[self.dialog_key]
        super().closeEvent(event)


class MultiFilteringOutlinerWidget(QtWidgets.QWidget):
    """Multi Filtering Outliner ツールウィジェット"""

    def __init__(self, parent=None):
        # Mayaのメインウィンドウを親として取得
        if parent is None:
            try:
                from maya import OpenMayaUI as omui
                from shiboken6 import wrapInstance
                maya_main_window_ptr = omui.MQtUtil.mainWindow()
                parent = wrapInstance(int(maya_main_window_ptr), QtWidgets.QWidget)
            except:
                pass

        super(MultiFilteringOutlinerWidget, self).__init__(parent)

        # ウィンドウフラグを設定
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Multi Filtering Outliner")

        # 初期化フラグ（初期化中は自動保存を無効化）
        self._is_loading = True

        # 階層構造データ（5階層）
        self.projects = []  # プロジェクトのリスト
        self.current_project_index = -1
        self.current_model_index = -1
        self.current_work_index = -1
        self.current_phrase_preset_index = -1  # 新規：フレーズプリセットのインデックス

        # ボタンリスト
        self.list_buttons = []  # 作業プリセット選択ボタンのリスト
        self.phrase_preset_buttons = []  # フレーズプリセット選択ボタンのリスト

        # 旧データ構造（互換性のため）
        self.outliner_lists = []  # リスト設定データのリスト
        self.current_list_index = -1  # 現在表示中のリストインデックス（-1は未初期化）

        self.current_nodes = []  # 現在表示中のノードリスト
        self.node_dialogs = {}  # プリセットごとのノードリストダイアログ {list_name: dialog}
        self.last_import_path = ""  # 最後に使用した読み込みパス
        self.last_export_path = ""  # 最後に使用した書き出しパス
        self.main_window_geometry = {}  # メインウィンドウのジオメトリ
        self.create_ui()
        self.load_settings()  # 設定を読み込み
        self.restore_main_window_geometry()  # ウィンドウ位置を復元

        # 初期化完了
        self._is_loading = False

    def create_ui(self):
        """UIを作成"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # タイトル
        title = QtWidgets.QLabel("Node Filter")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("background-color: rgb(76, 76, 89); padding: 5px;")
        title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        font = title.font()
        font.setBold(True)
        font.setPointSize(10)
        title.setFont(font)
        main_layout.addWidget(title, 0)  # ストレッチファクター0（固定）

        # プロジェクト選択エリア（プルダウン）
        project_layout = QtWidgets.QHBoxLayout()
        project_layout.addWidget(QtWidgets.QLabel("プロジェクト:"))

        self.project_combo = QtWidgets.QComboBox()
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        project_layout.addWidget(self.project_combo)

        add_project_btn = QtWidgets.QPushButton("+")
        add_project_btn.setFixedSize(25, 25)
        add_project_btn.clicked.connect(self.on_add_project)
        project_layout.addWidget(add_project_btn)

        remove_project_btn = QtWidgets.QPushButton("-")
        remove_project_btn.setFixedSize(25, 25)
        remove_project_btn.setStyleSheet("background-color: rgb(100, 70, 70);")
        remove_project_btn.clicked.connect(self.on_remove_project)
        project_layout.addWidget(remove_project_btn)

        rename_project_btn = QtWidgets.QPushButton("名前変更")
        rename_project_btn.setFixedHeight(25)
        rename_project_btn.setMinimumWidth(80)
        rename_project_btn.clicked.connect(self.on_rename_project)
        project_layout.addWidget(rename_project_btn)

        duplicate_project_btn = QtWidgets.QPushButton("複製")
        duplicate_project_btn.setFixedHeight(25)
        duplicate_project_btn.setMinimumWidth(80)
        duplicate_project_btn.clicked.connect(self.on_duplicate_project)
        project_layout.addWidget(duplicate_project_btn)

        main_layout.addLayout(project_layout, 0)  # ストレッチファクター0（固定）

        # モデル選択エリア（プルダウン）
        model_layout = QtWidgets.QHBoxLayout()
        model_layout.addWidget(QtWidgets.QLabel("モデル:"))

        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        model_layout.addWidget(self.model_combo)

        add_model_btn = QtWidgets.QPushButton("+")
        add_model_btn.setFixedSize(25, 25)
        add_model_btn.clicked.connect(self.on_add_model)
        model_layout.addWidget(add_model_btn)

        remove_model_btn = QtWidgets.QPushButton("-")
        remove_model_btn.setFixedSize(25, 25)
        remove_model_btn.setStyleSheet("background-color: rgb(100, 70, 70);")
        remove_model_btn.clicked.connect(self.on_remove_model)
        model_layout.addWidget(remove_model_btn)

        rename_model_btn = QtWidgets.QPushButton("名前変更")
        rename_model_btn.setFixedHeight(25)
        rename_model_btn.setMinimumWidth(80)
        rename_model_btn.clicked.connect(self.on_rename_model)
        model_layout.addWidget(rename_model_btn)

        duplicate_model_btn = QtWidgets.QPushButton("複製")
        duplicate_model_btn.setFixedHeight(25)
        duplicate_model_btn.setMinimumWidth(80)
        duplicate_model_btn.clicked.connect(self.on_duplicate_model)
        model_layout.addWidget(duplicate_model_btn)

        main_layout.addLayout(model_layout, 0)  # ストレッチファクター0（固定）

        # 作業プリセット選択ボタンエリア（グループボックス内にFlowLayout）
        buttons_group = QtWidgets.QGroupBox("作業プリセット")
        buttons_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        buttons_group.setStyleSheet("""
            QGroupBox {
                background-color: rgba(90, 90, 90, 180);
                border: 1px solid rgba(100, 100, 100, 100);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 5px;
                background-color: transparent;
            }
        """)
        buttons_group_layout = QtWidgets.QVBoxLayout(buttons_group)
        buttons_group_layout.setContentsMargins(5, 5, 5, 5)
        buttons_group_layout.setSpacing(5)

        # FlowLayoutで段組み対応
        buttons_container = QtWidgets.QWidget()
        buttons_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        buttons_container.setStyleSheet("QWidget { background-color: rgba(100, 100, 100, 150); border-radius: 3px; }")

        if FlowLayout:
            self.buttons_layout = FlowLayout(buttons_container)
        else:
            # FlowLayoutが利用できない場合のフォールバック
            self.buttons_layout = QtWidgets.QHBoxLayout(buttons_container)

        self.buttons_layout.setSpacing(5)
        self.buttons_layout.setContentsMargins(5, 5, 5, 5)

        buttons_group_layout.addWidget(buttons_container)

        # 作業プリセット追加/削除/複製ボタン
        list_control_layout = QtWidgets.QHBoxLayout()

        add_list_btn = QtWidgets.QPushButton("+ 作業追加")
        add_list_btn.setFixedHeight(25)
        add_list_btn.clicked.connect(self.on_add_list)
        list_control_layout.addWidget(add_list_btn)

        remove_list_btn = QtWidgets.QPushButton("- 作業削除")
        remove_list_btn.setFixedHeight(25)
        remove_list_btn.setStyleSheet("background-color: rgb(100, 70, 70);")
        remove_list_btn.clicked.connect(self.on_remove_current_list)
        list_control_layout.addWidget(remove_list_btn)

        duplicate_work_btn = QtWidgets.QPushButton("作業複製")
        duplicate_work_btn.setFixedHeight(25)
        duplicate_work_btn.clicked.connect(self.on_duplicate_work)
        list_control_layout.addWidget(duplicate_work_btn)

        list_control_layout.addStretch()

        import_btn = QtWidgets.QPushButton("読み込み")
        import_btn.setFixedHeight(25)
        import_btn.setFixedWidth(80)
        import_btn.clicked.connect(self.import_preset)
        list_control_layout.addWidget(import_btn)

        export_btn = QtWidgets.QPushButton("書き出し")
        export_btn.setFixedHeight(25)
        export_btn.setFixedWidth(80)
        export_btn.clicked.connect(self.export_preset)
        list_control_layout.addWidget(export_btn)

        save_btn = QtWidgets.QPushButton("保存")
        save_btn.setFixedHeight(25)
        save_btn.setFixedWidth(60)
        save_btn.clicked.connect(self.save_settings)
        list_control_layout.addWidget(save_btn)

        buttons_group_layout.addLayout(list_control_layout)

        # 作業プリセット内のコンテンツコンテナ（入れ子構造の親）
        work_content_container = QtWidgets.QWidget()
        work_content_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        work_content_layout = QtWidgets.QVBoxLayout(work_content_container)
        work_content_layout.setContentsMargins(10, 5, 5, 5)
        work_content_layout.setSpacing(5)
        buttons_group_layout.addWidget(work_content_container, 1)  # ストレッチファクター1（拡縮可能）

        main_layout.addWidget(buttons_group, 1)  # ストレッチファクター1（拡縮可能）

        # 共通フィルター入力エリア（作業プリセット全体に適用）
        common_filter_group = QtWidgets.QGroupBox("共通フィルター（全フレーズプリセットに適用）")
        common_filter_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        common_filter_group.setStyleSheet("""
            QGroupBox {
                background-color: rgba(75, 75, 75, 190);
                border: 1px solid rgba(100, 100, 100, 100);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 5px;
                background-color: transparent;
            }
        """)
        common_filter_layout = QtWidgets.QVBoxLayout()
        common_filter_layout.setSpacing(5)

        # 共通フィルター入力コンテナ（スクロール可能）
        common_filter_scroll = QtWidgets.QScrollArea()
        common_filter_scroll.setWidgetResizable(True)
        common_filter_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        common_filter_scroll.setMinimumHeight(80)
        common_filter_scroll.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.common_filter_container = QtWidgets.QWidget()
        self.common_filter_container_layout = QtWidgets.QVBoxLayout(self.common_filter_container)
        self.common_filter_container_layout.setSpacing(3)
        self.common_filter_container_layout.setContentsMargins(0, 0, 0, 0)
        self.common_filter_container_layout.setAlignment(QtCore.Qt.AlignTop)

        common_filter_scroll.setWidget(self.common_filter_container)
        common_filter_layout.addWidget(common_filter_scroll)

        # 共通フィルター追加/削除ボタン
        common_filter_buttons_layout = QtWidgets.QHBoxLayout()

        add_common_filter_btn = QtWidgets.QPushButton("+ フィルター追加")
        add_common_filter_btn.setFixedHeight(25)
        add_common_filter_btn.clicked.connect(self.on_add_common_filter)
        common_filter_buttons_layout.addWidget(add_common_filter_btn)

        remove_common_filter_btn = QtWidgets.QPushButton("- フィルター削除")
        remove_common_filter_btn.setFixedHeight(25)
        remove_common_filter_btn.setStyleSheet("background-color: rgb(100, 70, 70);")
        remove_common_filter_btn.clicked.connect(self.on_remove_last_common_filter)
        common_filter_buttons_layout.addWidget(remove_common_filter_btn)

        common_filter_layout.addLayout(common_filter_buttons_layout)

        common_filter_group.setLayout(common_filter_layout)
        work_content_layout.addWidget(common_filter_group, 1)  # ストレッチファクター1（拡縮可能、低優先度）

        # フレーズプリセット選択ボタンエリア（グループボックス内にFlowLayout）
        phrase_preset_group = QtWidgets.QGroupBox("フレーズプリセット")
        phrase_preset_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        phrase_preset_group.setStyleSheet("""
            QGroupBox {
                background-color: rgba(70, 70, 70, 195);
                border: 1px solid rgba(100, 100, 100, 100);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 5px;
                background-color: transparent;
            }
        """)
        phrase_preset_group_layout = QtWidgets.QVBoxLayout(phrase_preset_group)
        phrase_preset_group_layout.setContentsMargins(5, 5, 5, 5)
        phrase_preset_group_layout.setSpacing(5)

        # FlowLayoutで段組み対応
        phrase_preset_buttons_container = QtWidgets.QWidget()
        phrase_preset_buttons_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        phrase_preset_buttons_container.setStyleSheet("QWidget { background-color: rgba(85, 85, 85, 150); border-radius: 3px; }")

        if FlowLayout:
            self.phrase_preset_buttons_layout = FlowLayout(phrase_preset_buttons_container)
        else:
            self.phrase_preset_buttons_layout = QtWidgets.QHBoxLayout(phrase_preset_buttons_container)

        self.phrase_preset_buttons_layout.setSpacing(5)
        self.phrase_preset_buttons_layout.setContentsMargins(5, 5, 5, 5)

        phrase_preset_group_layout.addWidget(phrase_preset_buttons_container)

        # フレーズプリセット追加/削除/複製ボタン
        phrase_preset_control_layout = QtWidgets.QHBoxLayout()

        add_phrase_preset_btn = QtWidgets.QPushButton("+ フレーズプリセット追加")
        add_phrase_preset_btn.setFixedHeight(25)
        add_phrase_preset_btn.clicked.connect(self.on_add_phrase_preset)
        phrase_preset_control_layout.addWidget(add_phrase_preset_btn)

        remove_phrase_preset_btn = QtWidgets.QPushButton("- フレーズプリセット削除")
        remove_phrase_preset_btn.setFixedHeight(25)
        remove_phrase_preset_btn.setStyleSheet("background-color: rgb(100, 70, 70);")
        remove_phrase_preset_btn.clicked.connect(self.on_remove_phrase_preset)
        phrase_preset_control_layout.addWidget(remove_phrase_preset_btn)

        duplicate_phrase_preset_btn = QtWidgets.QPushButton("フレーズプリセット複製")
        duplicate_phrase_preset_btn.setFixedHeight(25)
        duplicate_phrase_preset_btn.clicked.connect(self.on_duplicate_phrase_preset)
        phrase_preset_control_layout.addWidget(duplicate_phrase_preset_btn)

        phrase_preset_control_layout.addStretch()
        phrase_preset_group_layout.addLayout(phrase_preset_control_layout)

        # フレーズプリセット内のコンテンツコンテナ（さらに入れ子）
        phrase_preset_content_container = QtWidgets.QWidget()
        phrase_preset_content_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        phrase_preset_content_layout = QtWidgets.QVBoxLayout(phrase_preset_content_container)
        phrase_preset_content_layout.setContentsMargins(10, 5, 5, 5)
        phrase_preset_content_layout.setSpacing(5)
        phrase_preset_group_layout.addWidget(phrase_preset_content_container, 1)  # ストレッチファクター1

        work_content_layout.addWidget(phrase_preset_group, 3)  # ストレッチファクター3（高優先度）

        # フレーズ入力エリア（ウィンドウに合わせて拡縮）
        phrase_group = QtWidgets.QGroupBox("フレーズ設定")
        phrase_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        phrase_group.setStyleSheet("""
            QGroupBox {
                background-color: rgba(60, 60, 60, 200);
                border: 1px solid rgba(100, 100, 100, 100);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 5px;
                background-color: transparent;
            }
        """)
        phrase_layout = QtWidgets.QVBoxLayout()
        phrase_layout.setSpacing(5)

        # マッチモード選択
        match_mode_layout = QtWidgets.QHBoxLayout()
        match_mode_layout.addWidget(QtWidgets.QLabel("マッチモード:"))

        self.match_mode_combo = QtWidgets.QComboBox()
        self.match_mode_combo.addItem("いずれか一致", "any")
        self.match_mode_combo.addItem("すべて一致", "all")
        self.match_mode_combo.currentIndexChanged.connect(self.on_filter_changed)
        match_mode_layout.addWidget(self.match_mode_combo)

        match_mode_layout.addSpacing(20)

        # DAGオブジェクトのみチェックボックス
        self.dag_only_check = QtWidgets.QCheckBox("DAGオブジェクトのみ")
        self.dag_only_check.setChecked(False)
        self.dag_only_check.stateChanged.connect(self.on_filter_changed)
        match_mode_layout.addWidget(self.dag_only_check)

        match_mode_layout.addSpacing(20)

        # 共通フィルター使用チェックボックス
        self.use_common_filter_check = QtWidgets.QCheckBox("共通フィルター使用")
        self.use_common_filter_check.setChecked(True)
        self.use_common_filter_check.stateChanged.connect(self.on_filter_changed)
        match_mode_layout.addWidget(self.use_common_filter_check)

        match_mode_layout.addStretch()
        phrase_layout.addLayout(match_mode_layout)

        # フレーズ入力コンテナ（スクロール可能、拡縮対応）
        phrase_scroll = QtWidgets.QScrollArea()
        phrase_scroll.setWidgetResizable(True)
        phrase_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        phrase_scroll.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.phrase_container = QtWidgets.QWidget()
        self.phrase_container_layout = QtWidgets.QVBoxLayout(self.phrase_container)
        self.phrase_container_layout.setSpacing(3)
        self.phrase_container_layout.setContentsMargins(0, 0, 0, 0)
        self.phrase_container_layout.setAlignment(QtCore.Qt.AlignTop)

        phrase_scroll.setWidget(self.phrase_container)
        phrase_layout.addWidget(phrase_scroll)

        # フレーズ追加/削除ボタン
        phrase_buttons_layout = QtWidgets.QHBoxLayout()

        add_phrase_btn = QtWidgets.QPushButton("+ フレーズ追加")
        add_phrase_btn.setFixedHeight(25)
        add_phrase_btn.clicked.connect(self.on_add_phrase)
        phrase_buttons_layout.addWidget(add_phrase_btn)

        remove_phrase_btn = QtWidgets.QPushButton("- フレーズ削除")
        remove_phrase_btn.setFixedHeight(25)
        remove_phrase_btn.setStyleSheet("background-color: rgb(100, 70, 70);")
        remove_phrase_btn.clicked.connect(self.on_remove_last_phrase)
        phrase_buttons_layout.addWidget(remove_phrase_btn)

        phrase_layout.addLayout(phrase_buttons_layout)

        phrase_group.setLayout(phrase_layout)
        phrase_preset_content_layout.addWidget(phrase_group, 2)  # ストレッチファクター2

        # ノードリスト表示エリア（最優先で拡縮）
        list_group = QtWidgets.QGroupBox("ノードリスト")
        list_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        list_group.setStyleSheet("""
            QGroupBox {
                background-color: rgba(55, 55, 55, 205);
                border: 1px solid rgba(100, 100, 100, 100);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 5px;
                background-color: transparent;
            }
        """)
        list_layout = QtWidgets.QVBoxLayout()
        list_layout.setSpacing(5)

        self.node_list = QtWidgets.QListWidget()
        self.node_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.node_list.itemDoubleClicked.connect(self.on_node_double_clicked)
        self.node_list.itemSelectionChanged.connect(self.on_selection_changed)
        # コンテキストメニューを有効化
        self.node_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.node_list.customContextMenuRequested.connect(self.show_context_menu)
        list_layout.addWidget(self.node_list)

        list_group.setLayout(list_layout)
        phrase_preset_content_layout.addWidget(list_group, 3)  # ストレッチファクター3（最優先）

        # 更新・選択・ダイアログボタン
        action_buttons_layout = QtWidgets.QHBoxLayout()

        refresh_btn = QtWidgets.QPushButton("更新")
        refresh_btn.setMinimumHeight(30)
        refresh_btn.setStyleSheet("background-color: rgb(102, 153, 179);")
        refresh_btn.clicked.connect(self.on_refresh)
        action_buttons_layout.addWidget(refresh_btn)

        select_btn = QtWidgets.QPushButton("選択")
        select_btn.setMinimumHeight(30)
        select_btn.setStyleSheet("background-color: rgb(102, 153, 204);")
        select_btn.clicked.connect(self.on_select_nodes)
        action_buttons_layout.addWidget(select_btn)

        dialog_btn = QtWidgets.QPushButton("ダイアログで開く")
        dialog_btn.setMinimumHeight(30)
        dialog_btn.setStyleSheet("background-color: rgb(102, 179, 153);")
        dialog_btn.clicked.connect(self.on_open_dialog)
        action_buttons_layout.addWidget(dialog_btn)

        phrase_preset_content_layout.addLayout(action_buttons_layout)

    def closeEvent(self, event):
        """ウィジェットが閉じられる時に設定を保存"""
        # 開いているダイアログの状態を保存（閉じる前に）
        for list_name, dialog in self.node_dialogs.items():
            if dialog.isVisible() and dialog.list_index >= 0:
                if dialog.list_index < len(self.outliner_lists):
                    # ダイアログが開いている状態を記録
                    self.outliner_lists[dialog.list_index]['dialog_open'] = True
                    # ジオメトリも保存
                    dialog.save_geometry()

        # すべてのダイアログを閉じる（dialog_openフラグを変更しないように）
        for dialog in list(self.node_dialogs.values()):
            try:
                # closeEventでdialog_openがFalseに設定されないようにフラグを立てる
                dialog._closing_from_main = True
                dialog.close()
            except:
                pass
        self.node_dialogs.clear()

        # メインウィンドウの位置とサイズを保存
        self.save_main_window_geometry()

        # 設定を保存
        self.save_settings()
        super().closeEvent(event)

    # ========== 階層構造管理メソッド ==========

    def get_current_work_preset(self):
        """現在選択されている作業プリセットを取得"""
        if (0 <= self.current_project_index < len(self.projects) and
            0 <= self.current_model_index < len(self.projects[self.current_project_index].get('models', [])) and
            0 <= self.current_work_index < len(self.projects[self.current_project_index]['models'][self.current_model_index].get('works', []))):
            return self.projects[self.current_project_index]['models'][self.current_model_index]['works'][self.current_work_index]
        return None

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

    def on_add_project(self):
        """新しいプロジェクトを追加"""
        project_name, ok = QtWidgets.QInputDialog.getText(
            self, "プロジェクト追加", "プロジェクト名を入力してください:"
        )

        if not ok or not project_name:
            return

        # 新しいプロジェクトを作成
        new_project = {
            'name': project_name,
            'models': []
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

        import copy
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

        # 新しいモデルを作成
        new_model = {
            'name': model_name,
            'works': []
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
        project = self.get_current_project()
        if not project or self.current_model_index < 0:
            return

        import copy
        original_model = project['models'][self.current_model_index]
        original_name = original_model['name']

        # 新しい名前を生成
        counter = 1
        new_name = f"{original_name}_copy"
        while any(m['name'] == new_name for m in project['models']):
            new_name = f"{original_name}_copy{counter}"
            counter += 1

        # モデルを複製
        new_model = copy.deepcopy(original_model)
        new_model['name'] = new_name

        project['models'].append(new_model)
        self.model_combo.addItem(new_name)
        self.model_combo.setCurrentIndex(len(project['models']) - 1)
        self.save_settings()

        print(f"モデル '{new_name}' を作成しました")

    def on_project_changed(self, index):
        """プロジェクトが変更された時"""
        if index < 0:
            self.current_project_index = -1
            self.model_combo.clear()
            self.clear_work_buttons()
            self.clear_phrase_preset_buttons()
            return

        # 現在の状態を保存
        if self.current_work_index >= 0:
            self.save_common_filters_state()
        if self.current_phrase_preset_index >= 0:
            self.save_current_phrase_preset_state()
        self.save_settings()

        self.current_project_index = index
        self.update_model_combo()

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

    def on_model_changed(self, index):
        """モデルが変更された時"""
        if index < 0:
            self.current_model_index = -1
            self.clear_work_buttons()
            self.clear_phrase_preset_buttons()
            return

        # 現在の状態を保存
        if self.current_work_index >= 0:
            self.save_common_filters_state()
        if self.current_phrase_preset_index >= 0:
            self.save_current_phrase_preset_state()
        self.save_settings()

        self.current_model_index = index
        self.update_work_buttons()

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

    def switch_to_work(self, index):
        """指定した作業プリセットに切り替え"""
        model = self.get_current_model()
        if not model or index < 0 or index >= len(model.get('works', [])):
            return

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

    # ========== 旧形式互換メソッド（作業プリセット） ==========

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

    def add_phrase_row(self, text='', enabled=True, exclude=False, exact_token=False):
        """フレーズ入力行を追加"""
        phrase_widget = DraggablePhraseWidget(text, enabled, exclude, exact_token, self.phrase_container)
        phrase_widget.phrase_input.textChanged.connect(self.on_filter_changed)
        phrase_widget.enabled_check.stateChanged.connect(self.on_filter_changed)
        phrase_widget.exclude_check.stateChanged.connect(self.on_filter_changed)
        phrase_widget.exact_token_check.stateChanged.connect(self.on_filter_changed)
        phrase_widget.remove_btn.clicked.connect(lambda: self.on_remove_phrase(phrase_widget))

        self.phrase_container_layout.addWidget(phrase_widget)

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

        # ウィジェットを削除
        self.phrase_container_layout.removeWidget(phrase_widget)
        phrase_widget.deleteLater()

        # リストを更新
        self.on_filter_changed()

    def on_remove_last_phrase(self):
        """最後のフレーズ入力を削除"""
        if self.phrase_container_layout.count() > 1:
            last_item = self.phrase_container_layout.itemAt(self.phrase_container_layout.count() - 1)
            if last_item and last_item.widget():
                self.on_remove_phrase(last_item.widget())

    def swap_phrase_rows(self, source_widget, target_widget):
        """フレーズ行を入れ替え"""
        source_index = self.phrase_container_layout.indexOf(source_widget)
        target_index = self.phrase_container_layout.indexOf(target_widget)

        if source_index == -1 or target_index == -1:
            return

        # ウィジェットを入れ替え
        self.phrase_container_layout.removeWidget(source_widget)
        self.phrase_container_layout.insertWidget(target_index, source_widget)

        # リストを更新
        self.on_filter_changed()

    def on_list_name_changed(self, index, new_name):
        """リスト名が変更された時（旧形式互換、現在は使用されていない）"""
        # 階層構造では on_work_name_changed を使用
        pass

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

        import copy
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

        works.append(new_work)

        # ボタンを作成
        self.create_work_button(len(works) - 1)

        # 新しい作業プリセットに切り替え
        self.switch_to_work(len(works) - 1)

        # 設定を保存
        self.save_settings()

        print(f"作業プリセット '{new_name}' を作成しました")

    # ========== フレーズプリセット管理メソッド ==========

    def get_current_phrase_preset(self):
        """現在選択されているフレーズプリセットを取得"""
        work = self.get_current_work_preset()
        if work and 0 <= self.current_phrase_preset_index < len(work.get('phrase_presets', [])):
            return work['phrase_presets'][self.current_phrase_preset_index]
        return None

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

    def switch_to_phrase_preset(self, index):
        """指定したフレーズプリセットに切り替え"""
        work = self.get_current_work_preset()
        if not work:
            return

        phrase_presets = work.get('phrase_presets', [])
        if index < 0 or index >= len(phrase_presets):
            return

        # 現在の状態を保存
        if self.current_phrase_preset_index >= 0:
            self.save_current_phrase_preset_state()

        # インデックスを更新
        self.current_phrase_preset_index = index

        # ボタンの状態を更新
        for i, btn in enumerate(self.phrase_preset_buttons):
            btn.setChecked(i == index)

        # UIを更新
        self.load_phrase_preset_to_ui(index)

    def save_current_phrase_preset_state(self):
        """現在のフレーズプリセットの状態を保存"""
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

    def load_phrase_preset_to_ui(self, index):
        """フレーズプリセットのデータをUIに読み込み"""
        work = self.get_current_work_preset()
        if not work:
            return

        phrase_presets = work.get('phrase_presets', [])
        if index < 0 or index >= len(phrase_presets):
            return

        preset_data = phrase_presets[index]

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

        # リストを更新
        self.on_refresh()

    def on_phrase_preset_name_changed(self, index, new_name):
        """フレーズプリセット名が変更された時"""
        work = self.get_current_work_preset()
        if work and 0 <= index < len(work.get('phrase_presets', [])):
            work['phrase_presets'][index]['name'] = new_name
            self.save_settings()

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
            'phrase_data': [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}],
            'match_mode': 'any',
            'dag_only': False,
            'use_common_filter': True
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

        import copy
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

    # ========== 共通フィルター管理メソッド ==========

    def load_common_filters_to_ui(self):
        """共通フィルターをUIに読み込み"""
        work = self.get_current_work_preset()
        if not work:
            print("[load_common_filters_to_ui] 作業プリセットが見つかりません")
            return

        # 既存の共通フィルター入力をクリア
        while self.common_filter_container_layout.count():
            item = self.common_filter_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 共通フィルターを復元
        common_filters = work.get('common_filters', [])
        print(f"[load_common_filters_to_ui] 読み込み: {len(common_filters)}個のフィルター")
        if common_filters:
            print(f"[load_common_filters_to_ui] 内容: {common_filters}")

        if not common_filters:
            # デフォルトで1つ追加
            common_filters = [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}]
            work['common_filters'] = common_filters

        for filter_data in common_filters:
            if isinstance(filter_data, dict):
                self.add_common_filter_row(
                    filter_data.get('text', ''),
                    filter_data.get('enabled', True),
                    filter_data.get('exclude', False),
                    filter_data.get('exact_token', False)
                )

    def save_common_filters_state(self):
        """共通フィルターの状態を保存"""
        # 初期化中は保存しない
        if getattr(self, '_is_loading', False):
            print("[save_common_filters_state] 初期化中のため保存をスキップ")
            return

        # UIが破棄されている場合は保存しない
        if not hasattr(self, 'common_filter_container_layout') or self.common_filter_container_layout is None:
            print("[save_common_filters_state] UI が破棄されているため保存をスキップ")
            return

        work = self.get_current_work_preset()
        if not work:
            print("[save_common_filters_state] work が None - 保存できません")
            return

        # 共通フィルターを収集
        common_filters = []
        for i in range(self.common_filter_container_layout.count()):
            widget_item = self.common_filter_container_layout.itemAt(i)
            if widget_item and widget_item.widget():
                filter_widget = widget_item.widget()
                if isinstance(filter_widget, DraggablePhraseWidget):
                    common_filters.append({
                        'text': filter_widget.phrase_input.text(),
                        'enabled': filter_widget.enabled_check.isChecked(),
                        'exclude': filter_widget.exclude_check.isChecked(),
                        'exact_token': filter_widget.exact_token_check.isChecked()
                    })

        work['common_filters'] = common_filters if common_filters else [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}]
        print(f"[save_common_filters_state] 保存しました: {len(common_filters)}個のフィルター")
        if common_filters:
            print(f"[save_common_filters_state] 内容: {common_filters}")

    def add_common_filter_row(self, text='', enabled=True, exclude=False, exact_token=False):
        """共通フィルター入力行を追加"""
        filter_widget = DraggablePhraseWidget(text, enabled, exclude, exact_token, self.common_filter_container)
        filter_widget.phrase_input.textChanged.connect(self.on_common_filter_changed)
        filter_widget.enabled_check.stateChanged.connect(self.on_common_filter_changed)
        filter_widget.exclude_check.stateChanged.connect(self.on_common_filter_changed)
        filter_widget.exact_token_check.stateChanged.connect(self.on_common_filter_changed)
        filter_widget.remove_btn.clicked.connect(lambda: self.on_remove_common_filter(filter_widget))

        self.common_filter_container_layout.addWidget(filter_widget)

    def on_add_common_filter(self):
        """共通フィルター入力を追加"""
        self.add_common_filter_row()
        # フィルター追加時に自動保存
        self.save_common_filters_state()
        self.save_settings()

    def on_remove_common_filter(self, filter_widget):
        """特定の共通フィルター入力を削除"""
        if self.common_filter_container_layout.count() <= 1:
            # 最低1つは残す
            return

        # ウィジェットを削除
        self.common_filter_container_layout.removeWidget(filter_widget)
        filter_widget.deleteLater()

        # フィルターを更新
        self.on_common_filter_changed()

    def on_remove_last_common_filter(self):
        """最後の共通フィルター入力を削除"""
        if self.common_filter_container_layout.count() > 1:
            last_item = self.common_filter_container_layout.itemAt(self.common_filter_container_layout.count() - 1)
            if last_item and last_item.widget():
                self.on_remove_common_filter(last_item.widget())

    def on_common_filter_changed(self):
        """共通フィルターが変更された時"""
        # 初期化中は保存しない
        if getattr(self, '_is_loading', False):
            return
        self.save_common_filters_state()
        self.on_filter_changed()

    def on_filter_changed(self):
        """フィルタが変更された時（自動更新）"""
        # 現在のフレーズプリセットの状態を保存（ダイアログが最新の設定を参照できるように）
        if self.current_phrase_preset_index >= 0:
            self.save_current_phrase_preset_state()

        self.on_refresh()

        # フレーズ変更時に自動保存
        self.save_settings()

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

        # 包含フレーズがない場合はリストをクリア
        if not include_configs:
            self.node_list.clear()
            self.current_nodes = []
            return

        # マッチモードを取得
        match_mode = self.match_mode_combo.currentData()

        # 共通フィルター使用チェックボックスの状態を確認
        use_common_filter = self.use_common_filter_check.isChecked()

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

    def export_preset(self):
        """すべてのプリセットをファイルに書き出し"""
        if not self.projects:
            print("書き出すプリセットがありません")
            return

        # 現在の状態を保存
        self.save_current_work_state()

        # 初期ディレクトリを決定
        initial_dir = self.last_export_path if self.last_export_path else os.path.expanduser("~")

        # ファイルダイアログでファイルパスを取得
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "プリセットを書き出し",
            initial_dir,
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # すべてのプリセットを保存（階層構造）
            export_data = {
                'version': 2,
                'projects': self.projects
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            # 最後に使用したパスを保存（ディレクトリ部分のみ）
            self.last_export_path = os.path.dirname(file_path)

            print(f"{len(self.projects)}個のプロジェクトを書き出しました: {file_path}")

        except Exception as e:
            print(f"プリセットの書き出しに失敗: {e}")
            QtWidgets.QMessageBox.warning(
                self,
                "エラー",
                f"プリセットの書き出しに失敗しました:\n{e}"
            )

    def import_preset(self):
        """ファイルからプリセットを読み込み"""
        # 初期ディレクトリを決定
        initial_dir = self.last_import_path if self.last_import_path else os.path.expanduser("~")

        # ファイルダイアログでファイルパスを取得
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "プリセットを読み込み",
            initial_dir,
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # JSONファイルを読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            version = import_data.get('version', 1)

            if version == 2:
                # 新形式（階層構造）のインポート
                self.import_hierarchical_preset(import_data, file_path)
            else:
                # 旧形式（フラットリスト）のインポート
                self.import_flat_preset(import_data, file_path)

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

    def import_hierarchical_preset(self, import_data, file_path):
        """階層構造プリセットをインポート"""
        import copy

        imported_projects = import_data.get('projects', [])
        if not imported_projects:
            print("インポートするプロジェクトがありません")
            return

        # 単純に全プロジェクトをマージ（同名プロジェクトは番号付与）
        for project in imported_projects:
            project_name = project.get('name', 'プロジェクト')

            # 同名プロジェクトがあれば番号を付ける
            counter = 1
            new_name = project_name
            existing_names = [p['name'] for p in self.projects]
            while new_name in existing_names:
                new_name = f"{project_name}_{counter}"
                counter += 1

            project['name'] = new_name
            self.projects.append(copy.deepcopy(project))
            self.project_combo.addItem(new_name)

        # 最初にインポートしたプロジェクトに切り替え
        if self.projects:
            self.project_combo.setCurrentIndex(len(self.projects) - len(imported_projects))

        self.last_import_path = os.path.dirname(file_path)
        print(f"{len(imported_projects)}個のプロジェクトを読み込みました: {file_path}")
        self.save_settings()

    def import_flat_preset(self, import_data, file_path):
        """旧形式（フラット）プリセットをインポート - 現在のモデルの作業プリセットとして追加"""
        import copy

        # 現在のモデルを取得
        model = self.get_current_model()
        if not model:
            QtWidgets.QMessageBox.warning(
                self,
                "警告",
                "旧形式のプリセットをインポートするには、先にプロジェクトとモデルを選択してください"
            )
            return

        # 新しい形式（複数プリセット）か古い形式（単一プリセット）かを判定
        if 'lists' in import_data and isinstance(import_data['lists'], list):
            # 新しい形式：複数プリセット
            presets_to_import = import_data['lists']
        elif 'name' in import_data:
            # 古い形式：単一プリセット
            presets_to_import = [import_data]
        else:
            raise ValueError("無効なプリセットファイル形式です")

        # プリセットデータの検証と補完
        for preset_data in presets_to_import:
            if 'name' not in preset_data:
                preset_data['name'] = f"作業_{len(model.get('works', [])) + 1}"

            # 旧形式の場合は新形式に変換
            if 'phrase_presets' not in preset_data:
                # phrase_dataがある場合は、それをフレーズプリセットに変換
                phrase_data = preset_data.get('phrase_data', [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}])
                match_mode = preset_data.get('match_mode', 'any')
                dag_only = preset_data.get('dag_only', False)

                preset_data['phrase_presets'] = [
                    {
                        'name': 'フレーズ1',
                        'phrase_data': phrase_data,
                        'match_mode': match_mode,
                        'dag_only': dag_only
                    }
                ]
                # 旧形式のキーを削除（オプション）
                # preset_data.pop('phrase_data', None)
                # preset_data.pop('match_mode', None)
                # preset_data.pop('dag_only', None)

            # 共通フィルターを追加
            if 'common_filters' not in preset_data:
                preset_data['common_filters'] = [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}]

            # 各フレーズプリセットにuse_common_filterを追加（存在しない場合）
            for phrase_preset in preset_data.get('phrase_presets', []):
                if 'use_common_filter' not in phrase_preset:
                    phrase_preset['use_common_filter'] = True

        # 既存の作業プリセット名を取得
        existing_names = [work['name'] for work in model.get('works', [])]

        # プリセット選択ダイアログを表示
        dialog = PresetImportDialog(presets_to_import, existing_names, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            print("プリセットの読み込みをキャンセルしました")
            return

        # ユーザーの選択を取得
        choices = dialog.get_import_choices()

        imported_count = 0
        overwritten_count = 0
        skipped_count = 0
        first_imported_index = -1

        if 'works' not in model:
            model['works'] = []

        for choice in choices:
            preset_data = choice['data'].copy()  # データをコピーして使用
            import_mode = choice['mode']
            preset_name = preset_data.get('name', 'Unknown')  # データ内の名前を使用

            if import_mode == 'skip':
                skipped_count += 1
                print(f"作業プリセット '{preset_name}' をスキップしました")
                continue

            elif import_mode == 'overwrite':
                # 既存のプリセットを上書き
                existing_index = next(
                    (i for i, work in enumerate(model['works']) if work['name'] == preset_name),
                    None
                )
                if existing_index is not None:
                    # データをディープコピーして上書き
                    model['works'][existing_index] = copy.deepcopy(preset_data)
                    # 最初にインポートされたプリセットのインデックスを記録
                    if first_imported_index < 0:
                        first_imported_index = existing_index
                    # 現在表示中のプリセットを上書きした場合はUIを更新
                    if existing_index == self.current_work_index:
                        self.load_work_to_ui(existing_index)
                    overwritten_count += 1
                    print(f"作業プリセット '{preset_name}' を上書きしました")
                else:
                    # 存在しない場合は新規追加（念のため）
                    model['works'].append(copy.deepcopy(preset_data))
                    new_index = len(model['works']) - 1
                    if first_imported_index < 0:
                        first_imported_index = new_index
                    self.create_work_button(new_index)
                    imported_count += 1
                    print(f"作業プリセット '{preset_name}' を読み込みました")

            elif import_mode == 'rename':
                # 名前を変えて読み込み
                original_name = preset_data['name']
                counter = 1
                new_name = original_name
                while any(work['name'] == new_name for work in model['works']):
                    new_name = f"{original_name}_{counter}"
                    counter += 1

                # 新しい名前を設定
                preset_data['name'] = new_name

                # プリセットをリストに追加（ディープコピー）
                model['works'].append(copy.deepcopy(preset_data))
                new_index = len(model['works']) - 1

                # 最初にインポートされたプリセットのインデックスを記録
                if first_imported_index < 0:
                    first_imported_index = new_index

                # ボタンを作成
                self.create_work_button(new_index)
                imported_count += 1
                print(f"作業プリセット '{new_name}' を読み込みました")

        # 最初にインポートされたプリセットに切り替え
        if first_imported_index >= 0:
            self.switch_to_work(first_imported_index)

        # 最後に使用したパスを保存（ディレクトリ部分のみ）
        self.last_import_path = os.path.dirname(file_path)

        # 結果をサマリー表示
        summary_parts = []
        if imported_count > 0:
            summary_parts.append(f"新規: {imported_count}個")
        if overwritten_count > 0:
            summary_parts.append(f"上書き: {overwritten_count}個")
        if skipped_count > 0:
            summary_parts.append(f"スキップ: {skipped_count}個")

        summary = ", ".join(summary_parts) if summary_parts else "なし"
        print(f"作業プリセット読み込み完了 ({summary}): {file_path}")
        self.save_settings()

    def save_settings(self):
        """設定をファイルに保存"""
        try:
            # 現在の状態を保存
            if self.current_work_index >= 0:
                self.save_common_filters_state()
            if self.current_phrase_preset_index >= 0:
                self.save_current_phrase_preset_state()
            self.save_current_work_state()

            # ディレクトリがなければ作成
            os.makedirs(SETTINGS_DIR, exist_ok=True)

            settings = {
                'version': 2,  # 階層構造バージョン
                'projects': self.projects,
                'current_project_index': self.current_project_index,
                'current_model_index': self.current_model_index,
                'current_work_index': self.current_work_index,
                'last_import_path': self.last_import_path,
                'last_export_path': self.last_export_path,
                'main_window_geometry': self.main_window_geometry,
                # 旧形式との互換性のため保持（マイグレーション用）
                'lists': self.outliner_lists,
                'current_index': self.current_list_index
            }

            # デバッグ: 現在のワークプリセットの共通フィルターを確認
            work = self.get_current_work_preset()
            if work:
                print(f"[save_settings] 現在のワークプリセットの共通フィルター: {work.get('common_filters', [])}")

            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            print(f"Multi Filtering Outliner: 設定を保存しました: {SETTINGS_FILE}")

        except Exception as e:
            print(f"Multi Filtering Outliner: 設定の保存に失敗: {e}")

    def save_main_window_geometry(self):
        """メインウィンドウのジオメトリを保存"""
        geometry = self.geometry()
        self.main_window_geometry = {
            'x': geometry.x(),
            'y': geometry.y(),
            'width': geometry.width(),
            'height': geometry.height()
        }

    def restore_main_window_geometry(self):
        """メインウィンドウのジオメトリを復元"""
        if self.main_window_geometry:
            x = self.main_window_geometry.get('x')
            y = self.main_window_geometry.get('y')
            width = self.main_window_geometry.get('width', 800)
            height = self.main_window_geometry.get('height', 600)

            if x is not None and y is not None:
                self.setGeometry(x, y, width, height)
            else:
                self.resize(width, height)

    def load_settings(self):
        """設定をファイルから読み込み"""
        try:
            if not os.path.exists(SETTINGS_FILE):
                # 旧設定ファイルからの移行を試みる
                old_settings_file = os.path.expanduser("~/.ez_modeling_tools/node_filter_settings.json")
                if os.path.exists(old_settings_file):
                    print("Multi Filtering Outliner: 旧設定ファイルを発見しました。移行します...")
                    try:
                        with open(old_settings_file, 'r', encoding='utf-8') as f:
                            old_settings = json.load(f)
                        # 新しいディレクトリを作成
                        os.makedirs(SETTINGS_DIR, exist_ok=True)
                        # 旧設定を新しい場所にコピー
                        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                            json.dump(old_settings, f, indent=2, ensure_ascii=False)
                        print(f"Multi Filtering Outliner: 設定を移行しました: {SETTINGS_FILE}")
                        # 移行した設定を読み込む
                        settings = old_settings
                    except Exception as e:
                        print(f"Multi Filtering Outliner: 旧設定の移行に失敗しました: {e}")
                        print("Multi Filtering Outliner: デフォルト階層を作成します")
                        self.create_default_hierarchy()
                        return
                else:
                    # デフォルトで階層を作成
                    print("Multi Filtering Outliner: 設定ファイルが存在しないため、デフォルト階層を作成します")
                    self.create_default_hierarchy()
                    return
            else:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

            version = settings.get('version', 1)

            # 最後に使用したパスを読み込み
            self.last_import_path = settings.get('last_import_path', "")
            self.last_export_path = settings.get('last_export_path', "")

            # メインウィンドウのジオメトリを読み込み
            self.main_window_geometry = settings.get('main_window_geometry', {})

            if version == 2:
                # 新形式（階層構造）
                self.projects = settings.get('projects', [])
                self.current_project_index = settings.get('current_project_index', -1)
                self.current_model_index = settings.get('current_model_index', -1)
                self.current_work_index = settings.get('current_work_index', -1)

                if not self.projects:
                    self.create_default_hierarchy()
                    return

                # プロジェクトのコンボボックスを更新
                for project in self.projects:
                    self.project_combo.addItem(project['name'])

                # 前回の選択状態を復元
                if 0 <= self.current_project_index < len(self.projects):
                    self.project_combo.setCurrentIndex(self.current_project_index)
                else:
                    self.project_combo.setCurrentIndex(0)

                print(f"Multi Filtering Outliner: 設定を読み込みました（階層構造）: {SETTINGS_FILE}")

            else:
                # 旧形式からマイグレーション
                print("Multi Filtering Outliner: 旧形式の設定を階層構造に変換します")
                self.migrate_from_old_format(settings)

            # 前回開いていたダイアログを復元
            self.restore_dialogs()

        except Exception as e:
            print(f"Multi Filtering Outliner: 設定の読み込みに失敗: {e}")
            import traceback
            traceback.print_exc()
            self.create_default_hierarchy()

    def create_default_hierarchy(self):
        """デフォルトの階層構造を作成"""
        default_project = {
            'name': 'プロジェクト1',
            'models': [
                {
                    'name': 'モデル1',
                    'works': [
                        {
                            'name': '作業1',
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
                    ]
                }
            ]
        }

        self.projects = [default_project]
        self.project_combo.addItem(default_project['name'])
        self.project_combo.setCurrentIndex(0)
        self.on_project_changed(0)

    def migrate_from_old_format(self, settings):
        """旧形式の設定を階層構造に変換"""
        old_lists = settings.get('lists', [])

        if not old_lists:
            self.create_default_hierarchy()
            return

        # 旧形式のリストをすべて1つのプロジェクト・モデルに統合
        migrated_works = []
        for old_list in old_lists:
            # phrase_presetsがない旧形式の場合は変換
            if 'phrase_presets' not in old_list:
                work = {
                    'name': old_list.get('name', 'リスト'),
                    'common_filters': [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}],
                    'phrase_presets': [
                        {
                            'name': 'フレーズ1',
                            'phrase_data': old_list.get('phrase_data', [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}]),
                            'match_mode': old_list.get('match_mode', 'any'),
                            'dag_only': old_list.get('dag_only', False),
                            'use_common_filter': True,
                            # 旧形式のdialog_openフラグをフレーズプリセットに移行（マイグレーション時はFalseにする）
                            'dialog_open': False,
                            'dialog_geometry': old_list.get('dialog_geometry', {})
                        }
                    ]
                }
            else:
                # すでにphrase_presetsがある場合はcommon_filtersを追加
                work = old_list.copy()  # コピーして元データを変更しない
                if 'common_filters' not in work:
                    work['common_filters'] = [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}]

                # 各フレーズプリセットにuse_common_filterを追加（存在しない場合）
                for phrase_preset in work.get('phrase_presets', []):
                    if 'use_common_filter' not in phrase_preset:
                        phrase_preset['use_common_filter'] = True
                    # マイグレーション時はdialog_openをFalseにする（古いダイアログを復元しない）
                    if 'dialog_open' in phrase_preset:
                        phrase_preset['dialog_open'] = False

                # 作業プリセットレベルのdialog_openとdialog_geometryを削除（新しい構造では不要）
                if 'dialog_open' in work:
                    del work['dialog_open']
                if 'dialog_geometry' in work:
                    del work['dialog_geometry']

            migrated_works.append(work)

        # 新しい階層構造を作成
        migrated_project = {
            'name': 'プロジェクト1',
            'models': [
                {
                    'name': 'モデル1',
                    'works': migrated_works
                }
            ]
        }

        self.projects = [migrated_project]
        self.project_combo.addItem(migrated_project['name'])
        self.project_combo.setCurrentIndex(0)
        self.on_project_changed(0)

        # 前回の選択状態を復元
        old_current_index = settings.get('current_index', 0)
        if 0 <= old_current_index < len(migrated_works):
            self.switch_to_work(old_current_index)

        print(f"旧形式から{len(migrated_works)}個の作業プリセットを移行しました")

    def restore_dialogs(self):
        """前回開いていたダイアログを復元"""
        # 階層構造内のすべてのフレーズプリセットをチェック
        for project_index, project in enumerate(self.projects):
            for model_index, model in enumerate(project.get('models', [])):
                for work_index, work_data in enumerate(model.get('works', [])):
                    work_name = work_data.get('name', f"作業{work_index+1}")

                    # 各フレーズプリセットをチェック
                    for phrase_index, phrase_preset in enumerate(work_data.get('phrase_presets', [])):
                        # ダイアログが開いていた場合
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
                                work_indices=(project_index, model_index, work_index),
                                phrase_index=phrase_index,
                                dialog_key=dialog_key,
                                parent_widget=self,
                                parent=self
                            )
                            self.node_dialogs[dialog_key] = dialog
                            dialog.show()

                            print(f"ダイアログを復元しました: {dialog_title}")

    def closeEvent(self, event):
        """ウィンドウが閉じられる時に呼ばれる"""
        # 現在の状態を保存
        if self.current_work_index >= 0:
            self.save_common_filters_state()
        if self.current_phrase_preset_index >= 0:
            self.save_current_phrase_preset_state()

        # すべてのダイアログを閉じる
        dialogs_to_close = list(self.node_dialogs.values())
        for dialog in dialogs_to_close:
            if dialog.isVisible():
                # メインウィンドウから閉じられたことを示すフラグを設定
                dialog._closing_from_main = True
                dialog.close()

        # 設定を保存
        self.save_settings()

        # 親クラスのcloseEventを呼ぶ
        super().closeEvent(event)


def create_multi_filtering_outliner_tab(parent=None):
    """
    Multi Filtering Outlinerタブを作成

    Args:
        parent: 親ウィジェット

    Returns:
        MultiFilteringOutlinerWidget: 作成されたウィジェット
    """
    return MultiFilteringOutlinerWidget(parent)
