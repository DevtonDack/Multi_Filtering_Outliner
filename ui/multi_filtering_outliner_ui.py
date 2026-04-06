# -*- coding: utf-8 -*-
"""
Multi Filtering Outliner UI - PySide6版
シーン内のノードをフレーズでフィルタリングして表示
"""

from PySide6 import QtWidgets, QtCore, QtGui
import json
import os
from tools import multi_filtering_outliner
from ui.mixins import (GeometryManagerMixin, SettingsManagerMixin,
                       DialogManagerMixin, HierarchyManagerMixin,
                       WorkPresetManagerMixin, PhrasePresetManagerMixin,
                       FilterManagerMixin, NodeListManagerMixin)
from ui.widgets import FlowLayout, EditableButton, DraggablePhraseWidget
from ui.dialogs import PresetImportDialog, NodeListDialog, CommonNodeListDialog
import sys


# 設定ファイルのパス
SETTINGS_DIR = os.path.expanduser("~/.multi_filtering_outliner")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "multi_filtering_outliner_settings.json")


class MultiFilteringOutlinerWidget(HierarchyManagerMixin, WorkPresetManagerMixin,
                                   PhrasePresetManagerMixin, FilterManagerMixin,
                                   NodeListManagerMixin, GeometryManagerMixin,
                                   SettingsManagerMixin, DialogManagerMixin,
                                   QtWidgets.QWidget):
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

        # ウィンドウフラグを設定（Maya統合のため）
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowMinMaxButtonsHint | QtCore.Qt.WindowCloseButtonHint)
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
        self.common_dialogs = {}  # 共通ダイアログ {unique_id: dialog}
        self.last_import_path = ""  # 最後に使用した読み込みパス
        self.last_export_path = ""  # 最後に使用した書き出しパス
        self.create_ui()
        self.load_settings()  # 設定を読み込み
        self.restore_model_geometry()  # ウィンドウ位置を復元（モデルプリセットごと）

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

        # プリセットID設定エリア
        id_layout = QtWidgets.QHBoxLayout()
        id_label = QtWidgets.QLabel("共通ダイアログID:")
        id_label.setMinimumWidth(120)
        id_layout.addWidget(id_label)

        self.preset_id_input = QtWidgets.QLineEdit()
        self.preset_id_input.setPlaceholderText("数字を入力 (例: 1, 2, 3...)")
        self.preset_id_input.setMaximumWidth(150)
        # 数字のみ入力可能に設定
        validator = QtGui.QIntValidator(1, 9999, self.preset_id_input)
        self.preset_id_input.setValidator(validator)
        self.preset_id_input.textChanged.connect(self.on_preset_id_changed)
        self.preset_id_input.editingFinished.connect(self.on_preset_id_editing_finished)
        id_layout.addWidget(self.preset_id_input)

        id_layout.addStretch()

        phrase_layout.addLayout(id_layout)

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

        # ダイアログボタン
        action_buttons_layout = QtWidgets.QHBoxLayout()

        dialog_btn = QtWidgets.QPushButton("ダイアログで開く")
        dialog_btn.setMinimumHeight(30)
        dialog_btn.setStyleSheet("background-color: rgb(102, 179, 153);")
        dialog_btn.clicked.connect(self.on_open_dialog)
        action_buttons_layout.addWidget(dialog_btn)

        common_dialog_btn = QtWidgets.QPushButton("共通ダイアログで開く")
        common_dialog_btn.setMinimumHeight(30)
        common_dialog_btn.setStyleSheet("background-color: rgb(153, 102, 179);")
        common_dialog_btn.clicked.connect(self.on_open_common_dialog)
        action_buttons_layout.addWidget(common_dialog_btn)

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

        # すべての共通ダイアログを閉じる
        for dialog in list(self.common_dialogs.values()):
            try:
                dialog.close()
            except:
                pass
        self.common_dialogs.clear()

        # 現在のモデルのジオメトリを保存
        if self.current_model_index >= 0:
            self.save_model_geometry()

        # 設定を保存
        self.save_settings()
        super().closeEvent(event)

    # ========== 階層構造管理メソッド ==========


    # ========== フレーズプリセット管理メソッド ==========


    # ========== 共通フィルター管理メソッド ==========

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
        if unique_id in self.common_dialogs and self.common_dialogs[unique_id].isVisible():
            self.common_dialogs[unique_id].on_refresh()
            self.common_dialogs[unique_id].raise_()
            self.common_dialogs[unique_id].activateWindow()
        else:
            # 新しい共通ダイアログを作成
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


    def migrate_uuid_to_numeric_ids(self):
        """すべてのUUID形式のIDを数字形式に変換"""
        converted_count = 0
        for project in self.projects:
            for model in project.get('models', []):
                for work in model.get('works', []):
                    phrase_presets = work.get('phrase_presets', [])
                    used_ids = set()

                    # まず既に数字形式のIDを収集
                    for preset in phrase_presets:
                        unique_id = preset.get('unique_id', '')
                        if unique_id and unique_id.isdigit():
                            used_ids.add(int(unique_id))

                    # UUID形式のIDを数字形式に変換
                    next_id = 1
                    for preset in phrase_presets:
                        unique_id = preset.get('unique_id', '')
                        if not unique_id or not unique_id.isdigit():
                            # 次の利用可能なIDを見つける
                            while next_id in used_ids:
                                next_id += 1
                            preset['unique_id'] = str(next_id)
                            used_ids.add(next_id)
                            converted_count += 1
                            next_id += 1

        if converted_count > 0:
            print(f"Multi Filtering Outliner: {converted_count}個のUUID形式のIDを数字形式に変換しました")
            # 変換後の設定を保存
            self.save_settings()

    def ensure_phrase_preset_fields(self):
        """すべてのフレーズプリセットに必要なフィールドが存在することを確認"""
        updated_count = 0
        for project in self.projects:
            for model in project.get('models', []):
                for work in model.get('works', []):
                    for phrase_preset in work.get('phrase_presets', []):
                        # unique_id フィールドが存在しない、または空の場合は生成
                        if not phrase_preset.get('unique_id'):
                            phrase_preset['unique_id'] = self.get_globally_unique_id()
                            updated_count += 1

                        # dialog_open フィールドが存在しない場合はFalseを設定
                        if 'dialog_open' not in phrase_preset:
                            phrase_preset['dialog_open'] = False
                            updated_count += 1

                        # common_dialog_open フィールドが存在しない場合はFalseを設定
                        if 'common_dialog_open' not in phrase_preset:
                            phrase_preset['common_dialog_open'] = False
                            updated_count += 1

        if updated_count > 0:
            print(f"Multi Filtering Outliner: {updated_count}個のフィールドにデフォルト値を設定しました")
            # 更新後の設定を保存
            self.save_settings()

    def fix_duplicate_unique_ids(self):
        """重複したunique_idを検出して修正"""
        seen_ids = {}  # {unique_id: (project_idx, model_idx, work_idx, phrase_idx)}
        duplicates = []

        # すべてのフレーズプリセットをスキャンして重複を検出
        for project_idx, project in enumerate(self.projects):
            for model_idx, model in enumerate(project.get('models', [])):
                for work_idx, work in enumerate(model.get('works', [])):
                    for phrase_idx, phrase_preset in enumerate(work.get('phrase_presets', [])):
                        unique_id = phrase_preset.get('unique_id')
                        if unique_id:
                            if unique_id in seen_ids:
                                # 重複を検出
                                duplicates.append((project_idx, model_idx, work_idx, phrase_idx, phrase_preset))
                            else:
                                seen_ids[unique_id] = (project_idx, model_idx, work_idx, phrase_idx)

        # 重複したIDに新しいグローバルにユニークなIDを割り当て
        fixed_count = 0
        for project_idx, model_idx, work_idx, phrase_idx, phrase_preset in duplicates:
            old_id = phrase_preset['unique_id']
            new_id = self.get_globally_unique_id()
            phrase_preset['unique_id'] = new_id
            seen_ids[new_id] = (project_idx, model_idx, work_idx, phrase_idx)

            # ダイアログの状態をリセット（重複していたため、どれが正しいかわからない）
            phrase_preset['dialog_open'] = False
            phrase_preset['common_dialog_open'] = False

            fixed_count += 1
            print(f"Multi Filtering Outliner: 重複したID '{old_id}' を '{new_id}' に変更しました (フレーズプリセット '{phrase_preset.get('name')}')")

        if fixed_count > 0:
            print(f"Multi Filtering Outliner: {fixed_count}個の重複IDを修正しました")
            # 修正後の設定を保存
            self.save_settings()

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

    def closeEvent(self, event):
        """ウィンドウが閉じられる時に呼ばれる"""
        print(f"[DEBUG closeEvent] ========== メインウィンドウクローズ開始 ==========")
        # 現在のモデルのジオメトリを保存
        if self.current_model_index >= 0:
            print(f"[DEBUG closeEvent] 現在のモデル(index={self.current_model_index})のジオメトリを保存")
            self.save_model_geometry()

        # 現在の状態を保存
        if self.current_work_index >= 0:
            self.save_common_filters_state()
        if self.current_phrase_preset_index >= 0:
            self.save_current_phrase_preset_state()

        # 開いているダイアログのジオメトリを保存してから閉じる
        print(f"[DEBUG closeEvent] --- ダイアログジオメトリ保存フェーズ ---")
        project = self.get_current_project()
        if project and 0 <= self.current_model_index < len(project.get('models', [])):
            current_model = project['models'][self.current_model_index]
            for work_index, work in enumerate(current_model.get('works', [])):
                work_name = work.get('name', f"作業{work_index+1}")
                for phrase_index, phrase_preset in enumerate(work.get('phrase_presets', [])):
                    unique_id = phrase_preset.get('unique_id')
                    phrase_name = phrase_preset.get('name', f"フレーズ{phrase_index+1}")
                    dialog_key = f"{work_name}::{phrase_name}"

                    # 専用ダイアログのジオメトリを保存
                    if dialog_key in self.node_dialogs and self.node_dialogs[dialog_key].isVisible():
                        dialog = self.node_dialogs[dialog_key]
                        geometry = dialog.geometry()
                        phrase_preset['dialog_geometry'] = {
                            'x': geometry.x(),
                            'y': geometry.y(),
                            'width': geometry.width(),
                            'height': geometry.height()
                        }
                        print(f"[DEBUG closeEvent] 専用ダイアログ '{dialog_key}': ジオメトリ保存 x={geometry.x()}, y={geometry.y()}")

                    # 共通ダイアログのジオメトリを保存
                    if unique_id and unique_id in self.common_dialogs and self.common_dialogs[unique_id].isVisible():
                        dialog = self.common_dialogs[unique_id]
                        geometry = dialog.geometry()
                        phrase_preset['common_dialog_geometry'] = {
                            'x': geometry.x(),
                            'y': geometry.y(),
                            'width': geometry.width(),
                            'height': geometry.height()
                        }
                        print(f"[DEBUG closeEvent] 共通ダイアログ ID={unique_id} ('{phrase_name}'): ジオメトリ保存 x={geometry.x()}, y={geometry.y()}")

        # すべての専用ダイアログを閉じる
        dialogs_to_close = list(self.node_dialogs.values())
        for dialog in dialogs_to_close:
            if dialog.isVisible():
                # メインウィンドウから閉じられたことを示すフラグを設定
                dialog._closing_from_main = True
                dialog.close()

        # すべての共通ダイアログを閉じる
        common_dialogs_to_close = list(self.common_dialogs.values())
        for dialog in common_dialogs_to_close:
            if dialog.isVisible():
                # メインウィンドウから閉じられたことを示すフラグを設定
                dialog._closing_from_main = True
                dialog.update_timer.stop()
                dialog.close()

        # 設定を保存
        print(f"[DEBUG closeEvent] 最終的なsave_settings()を呼び出します")
        self.save_settings()

        print(f"[DEBUG closeEvent] ========== メインウィンドウクローズ完了 ==========")
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
