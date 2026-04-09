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
                       FilterManagerMixin, NodeListManagerMixin,
                       PresetIDManagerMixin, DialogInteractionMixin,
                       PresetImportExportMixin, PresetMigrationMixin)
from ui.widgets import FlowLayout, EditableButton, DraggablePhraseWidget
from ui.dialogs import PresetImportDialog, NodeListDialog, CommonNodeListDialog
import sys


# 設定ファイルのパス
SETTINGS_DIR = os.path.expanduser("~/.multi_filtering_outliner")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "multi_filtering_outliner_settings.json")

# グローバルインスタンス管理（多重起動防止用）
_global_instance = None


class MultiFilteringOutlinerWidget(HierarchyManagerMixin, WorkPresetManagerMixin,
                                   PhrasePresetManagerMixin, FilterManagerMixin,
                                   NodeListManagerMixin, PresetIDManagerMixin,
                                   DialogInteractionMixin, PresetImportExportMixin,
                                   PresetMigrationMixin, GeometryManagerMixin,
                                   SettingsManagerMixin, DialogManagerMixin,
                                   QtWidgets.QWidget):
    """Multi Filtering Outliner ツールウィジェット"""

    # 固定のオブジェクト名（シングルトン識別用）
    WINDOW_OBJECT_NAME = "MultiFilteringOutlinerWidget_Singleton"

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

        # 固定のオブジェクト名を設定（シングルトン識別用）
        self.setObjectName(self.WINDOW_OBJECT_NAME)

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
        self.integrated_dialogs = {}  # 統合ダイアログ {(project_index, model_index): dialog}
        self.last_import_path = ""  # 最後に使用した読み込みパス
        self.last_export_path = ""  # 最後に使用した書き出しパス
        self.create_ui()
        self.load_settings()  # 設定を読み込み
        self.restore_model_geometry()  # ウィンドウ位置を復元（モデルプリセットごと）

        # 初期化完了
        self._is_loading = False

        # ダイアログの復元（初期化完了後に実行）
        print("[DEBUG __init__] 初期化完了。ダイアログの復元を開始します")
        self.restore_dialogs()
        print("[DEBUG __init__] ダイアログの復元が完了しました")

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
        # 2 列グリッドで配置（作業プリセットのフレーズ指定欄）
        self.common_filter_container_layout = QtWidgets.QGridLayout(self.common_filter_container)
        self.common_filter_container_layout.setSpacing(3)
        self.common_filter_container_layout.setContentsMargins(0, 0, 0, 0)
        self.common_filter_container_layout.setAlignment(QtCore.Qt.AlignTop)
        self.common_filter_container_layout.setColumnStretch(0, 1)
        self.common_filter_container_layout.setColumnStretch(1, 1)
        # 1 行あたりの列数
        self.common_filter_columns = 2

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
        # 2 列グリッドで配置
        self.phrase_container_layout = QtWidgets.QGridLayout(self.phrase_container)
        self.phrase_container_layout.setSpacing(3)
        self.phrase_container_layout.setContentsMargins(0, 0, 0, 0)
        self.phrase_container_layout.setAlignment(QtCore.Qt.AlignTop)
        self.phrase_container_layout.setColumnStretch(0, 1)
        self.phrase_container_layout.setColumnStretch(1, 1)
        # 1 行あたりの列数（将来変更しやすいよう定数化）
        self.phrase_columns = 2

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

        integrated_dialog_btn = QtWidgets.QPushButton("統合ダイアログで開く")
        integrated_dialog_btn.setMinimumHeight(30)
        integrated_dialog_btn.setStyleSheet("background-color: rgb(102, 140, 200);")
        integrated_dialog_btn.clicked.connect(self.open_integrated_dialog)
        action_buttons_layout.addWidget(integrated_dialog_btn)

        phrase_preset_content_layout.addLayout(action_buttons_layout)

    def closeEvent(self, event):
        """ウィンドウが閉じられる時に呼ばれる"""
        global _global_instance
        print(f"[DEBUG closeEvent] ========== メインウィンドウクローズ開始 ==========")

        # グローバルインスタンスをクリア
        if _global_instance == self:
            _global_instance = None
            print(f"[DEBUG closeEvent] グローバルインスタンスをクリアしました")

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

        # すべての統合ダイアログを閉じる（分割構成とジオメトリを保存してから）
        integrated_to_close = list(self.integrated_dialogs.values())
        for dialog in integrated_to_close:
            try:
                if dialog.isVisible():
                    dialog._closing_from_main = True
                    if hasattr(dialog, 'update_timer'):
                        dialog.update_timer.stop()
                    try:
                        dialog.save_layout_to_data()
                    except Exception as e:
                        print(f"[closeEvent] 統合ダイアログ保存失敗: {e}")
                    dialog.close()
            except RuntimeError:
                pass
        self.integrated_dialogs.clear()

        # 設定を保存
        print(f"[DEBUG closeEvent] 最終的なsave_settings()を呼び出します")
        self.save_settings()

        print(f"[DEBUG closeEvent] ウィジェットを削除します（deleteLater）")

        # 親から切り離してから削除
        if self.parent():
            self.setParent(None)
            print(f"[DEBUG closeEvent] 親から切り離しました")

        # ウィジェットを完全に削除
        self.deleteLater()

        print(f"[DEBUG closeEvent] ========== メインウィンドウクローズ完了 ==========")
        # 親クラスのcloseEventを呼ぶ
        super().closeEvent(event)


def create_multi_filtering_outliner_tab(parent=None):
    """
    Multi Filtering Outlinerタブを作成（多重起動防止）

    Args:
        parent: 親ウィジェット

    Returns:
        MultiFilteringOutlinerWidget: 作成されたウィジェット（既存または新規）
    """
    global _global_instance

    # 1. グローバル変数のチェック
    if _global_instance is not None:
        try:
            # オブジェクトが有効かチェック
            _global_instance.objectName()
            print("[多重起動防止] グローバル変数から既存ウィンドウを使用")
            if not _global_instance.isVisible():
                _global_instance.show()
            _global_instance.raise_()
            _global_instance.activateWindow()
            return _global_instance
        except (RuntimeError, AttributeError):
            print("[多重起動防止] グローバル変数のインスタンスは無効")
            _global_instance = None

    # 2. objectNameで既存ウィジェットを検索
    try:
        from maya import OpenMayaUI as omui
        from shiboken6 import wrapInstance

        # Mayaのメインウィンドウを取得
        maya_main_window_ptr = omui.MQtUtil.mainWindow()
        maya_main_window = wrapInstance(int(maya_main_window_ptr), QtWidgets.QWidget)

        # objectNameで検索
        existing_widget = maya_main_window.findChild(
            QtWidgets.QWidget,
            MultiFilteringOutlinerWidget.WINDOW_OBJECT_NAME
        )

        if existing_widget is not None:
            try:
                # 有効なウィジェットかチェック（削除予定でないか、閉じられていないか）
                existing_widget.windowTitle()

                # ウィジェットが閉じられている、または削除予定の場合はスキップ
                if existing_widget.parent() is None and not existing_widget.isVisible():
                    print(f"[多重起動防止] 発見したウィジェットは閉じられているため無視します")
                else:
                    print(f"[多重起動防止] objectName '{MultiFilteringOutlinerWidget.WINDOW_OBJECT_NAME}' で既存ウィンドウを発見")
                    _global_instance = existing_widget

                    # 既存ウィンドウの場合も、閉じていたダイアログを復元
                    print("[多重起動防止] 既存ウィンドウのダイアログ状態をチェックします")
                    existing_widget.restore_model_dialogs()

                    if not existing_widget.isVisible():
                        existing_widget.show()
                    existing_widget.raise_()
                    existing_widget.activateWindow()
                    return existing_widget
            except (RuntimeError, AttributeError) as e:
                print(f"[多重起動防止] 発見したウィジェットは無効: {e}")

    except Exception as e:
        print(f"[多重起動防止] ウィジェット検索中にエラー: {e}")

    # 3. 新しいインスタンスを作成
    print("[多重起動防止] 新しいウィンドウを作成します")
    instance = MultiFilteringOutlinerWidget(parent)
    _global_instance = instance
    instance.show()
    return instance
