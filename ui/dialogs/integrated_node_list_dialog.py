# -*- coding: utf-8 -*-
"""
IntegratedNodeListDialog - 複数の共通ダイアログを 1 つのウィンドウ内に
グリッド状に並べて表示する統合ダイアログ。

仕様詳細は docs/INTEGRATED_DIALOG_SPEC.md を参照。

- エリアは最大 3 行 x 最大 6 列で動的に分割可能
- 行ごとに独立した列数を持てる
- 各セルに共通ダイアログ ID を割り当てると、該当するフレーズプリセットの
  フィルタ結果を共通ダイアログと同じロジックで表示する
- モデルプリセットごとに 1 インスタンスのみ
- 作業プリセット切替時は分割構成やジオメトリは変わらず、リスト内容のみ更新
"""

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui

# モジュール先頭で本プロジェクトの tools.multi_filtering_outliner を固定 import する。
# 起動時 (one_line_launch.py / one_line_launch_dev.py) で sys.path 先頭がこのプロジェクトに
# 設定された状態で読み込まれるため、ここで束縛しておけば、後段で他プロジェクトの
# tools パッケージが sys.modules に入っても影響を受けない。
# 遅延 import (関数内の `from tools import multi_filtering_outliner`) は
# 実行時の sys.modules['tools'] を参照してしまい、別プロジェクトの tools/__init__.py が
# 先にキャッシュされていると ImportError になるため使わない。
from tools import multi_filtering_outliner as _mfo
from ui.mixins.dpi_scale import DpiScaleMixin
from ui.dialogs.node_type_filter_dialog import NODE_TYPE_ENTRIES, NodeTypeFilterDialog


MAX_ROWS = 100
MAX_COLS = 100

CELL_MIME = "application/x-mfo-integrated-cell"
ROW_MIME = "application/x-mfo-integrated-row"


class _DragGrip(QtWidgets.QLabel):
    """ドラッグ開始用の小さなハンドル。mime_type と get_payload コールバックで動作。"""

    def __init__(self, text, mime_type, payload_getter, parent=None):
        super().__init__(text, parent)
        self._mime_type = mime_type
        self._payload_getter = payload_getter
        self._drag_start_pos = None
        self.setCursor(QtCore.Qt.OpenHandCursor)
        self.setStyleSheet(
            "QLabel { color: rgb(200,200,200); padding: 0 4px; "
            "background-color: rgba(80,80,100,180); border-radius: 2px; }"
        )
        self.setToolTip("ドラッグで並び替え")

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & QtCore.Qt.LeftButton):
            return
        if self._drag_start_pos is None:
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < QtWidgets.QApplication.startDragDistance():
            return
        payload = self._payload_getter()
        if payload is None:
            return
        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        mime.setData(self._mime_type, str(payload).encode('utf-8'))
        drag.setMimeData(mime)
        drag.exec(QtCore.Qt.MoveAction)
        self._drag_start_pos = None


class _IntegratedCell(QtWidgets.QFrame):
    """統合ダイアログ内の 1 セル分のウィジェット"""

    id_changed = QtCore.Signal(object, str)  # (cell_widget, new_unique_id)
    delete_requested = QtCore.Signal(object)  # (cell_widget,)
    cell_dropped = QtCore.Signal(object, int, int)  # (target_cell, src_row, src_col)

    def __init__(self, ui_scale=1.0, parent=None):
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setStyleSheet(
            "QFrame { background-color: rgba(60,60,70,180); "
            "border: 1px solid rgba(120,120,140,140); border-radius: 3px; }"
        )
        self.unique_id = ""
        self.nodes = []
        self.row_idx = -1
        self.col_idx = -1
        self._loading = False
        self._ui_scale = float(ui_scale) if ui_scale else 1.0
        self.setAcceptDrops(True)
        self._create_ui()

    def _s(self, value):
        return int(round(value * self._ui_scale))

    def _create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        m = self._s(4)
        layout.setContentsMargins(m, m, m, m)
        layout.setSpacing(self._s(3))

        header = QtWidgets.QHBoxLayout()
        header.setSpacing(self._s(4))

        # ドラッググリップ
        self.drag_grip = _DragGrip(
            "⋮⋮",
            CELL_MIME,
            lambda: f"{self.row_idx},{self.col_idx}" if self.row_idx >= 0 else None,
        )
        self.drag_grip.setFixedHeight(self._s(20))
        self.drag_grip.setStyleSheet(
            "QLabel { color: rgb(200,200,200); padding: 0 4px; "
            "background-color: rgba(80,80,100,180); border-radius: 2px; "
            "font-size: 9pt; }"
        )
        header.addWidget(self.drag_grip)

        id_label = QtWidgets.QLabel("ID:")
        id_label.setStyleSheet("font-size: 9pt;")
        header.addWidget(id_label)

        self.id_combo = QtWidgets.QComboBox()
        self.id_combo.setMinimumWidth(self._s(70))
        self.id_combo.setStyleSheet("QComboBox { font-size: 9pt; }")
        self.id_combo.currentIndexChanged.connect(self._on_combo_changed)
        header.addWidget(self.id_combo, 1)

        self.count_label = QtWidgets.QLabel("0")
        self.count_label.setStyleSheet(
            "color: rgb(200,200,200); background: transparent; font-size: 9pt;"
        )
        header.addWidget(self.count_label)

        # 削除ボタン
        self.delete_btn = QtWidgets.QPushButton("×")
        self.delete_btn.setFixedSize(self._s(20), self._s(20))
        self.delete_btn.setStyleSheet(
            "QPushButton { background-color: rgb(120, 70, 70); color: white; "
            "border-radius: 2px; font-weight: bold; font-size: 10pt; }"
            "QPushButton:hover { background-color: rgb(160, 80, 80); }"
        )
        self.delete_btn.setToolTip("このセルを削除")
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        header.addWidget(self.delete_btn)

        layout.addLayout(header)

        self.title_label = QtWidgets.QLabel("(未割り当て)")
        self.title_label.setStyleSheet(
            "color: rgb(180,200,220); font-size: 9pt;"
        )
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget { font-size: 9pt; }"
        )
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list_widget, 1)

    def set_id_options(self, id_name_pairs, current_id):
        """コンボボックスの選択肢を更新。
        id_name_pairs: [(unique_id, display_name), ...]
        current_id: 現在割り当てられている unique_id
        """
        self._loading = True
        self.id_combo.clear()
        self.id_combo.addItem("(未割り当て)", "")
        selected_index = 0
        for i, (uid, name) in enumerate(id_name_pairs):
            label = f"{uid}: {name}" if name else str(uid)
            self.id_combo.addItem(label, uid)
            if uid == current_id:
                selected_index = i + 1
        self.id_combo.setCurrentIndex(selected_index)
        self.unique_id = current_id
        self._loading = False

    def _on_combo_changed(self, index):
        if self._loading:
            return
        new_id = self.id_combo.itemData(index) or ""
        self.unique_id = new_id
        self.id_changed.emit(self, new_id)

    def set_nodes(self, nodes, title=""):
        # セルのリスト選択は Maya シーンの現在の選択と同期させる方針:
        #  - ユーザがリストでアイテムをクリック → _on_selection_changed が
        #    Maya 側を更新する。次の自動更新時には Maya 選択と一致するため
        #    リストの選択もそのまま維持される。
        #  - ユーザが Maya 側で別ノードを選択 → 次の自動更新時にリストの
        #    選択がクリア/更新され、Maya の状態に追従する。
        # こうすることで「自動更新で勝手に選択が消える」「別ノードを選んでも
        # 古い選択が残り続ける」両方の問題を回避できる。
        new_nodes = list(nodes)

        # 現在の Maya 選択（フルパス）を取得
        try:
            import maya.cmds as cmds
            maya_selected = set(cmds.ls(selection=True, long=True) or [])
        except ImportError:
            maya_selected = set()

        # 現在のリスト内容と選択を取得
        current_nodes = []
        current_selected = set()
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            p = it.data(QtCore.Qt.UserRole) if it else None
            if p:
                current_nodes.append(p)
                if it.isSelected():
                    current_selected.add(p)

        self.nodes = new_nodes
        self.count_label.setText(str(len(new_nodes)))
        self.title_label.setText(title if title else "(未割り当て)")

        # Maya 選択のうちこのセルに含まれるものが「あるべき選択」
        desired_selected = {p for p in new_nodes if p in maya_selected}

        # 内容も選択も同一なら何もしない（スクロール位置等を維持）
        if current_nodes == new_nodes and current_selected == desired_selected:
            return

        self.list_widget.blockSignals(True)
        try:
            if current_nodes == new_nodes:
                # 内容は同じで選択だけ差し替え（clear せずスクロール位置を維持）
                for i in range(self.list_widget.count()):
                    it = self.list_widget.item(i)
                    p = it.data(QtCore.Qt.UserRole)
                    should_be_selected = p in desired_selected
                    if it.isSelected() != should_be_selected:
                        it.setSelected(should_be_selected)
            else:
                # 内容が変わっているので作り直し
                self.list_widget.clear()
                for node_path in new_nodes:
                    short_name = node_path.split('|')[-1]
                    item = QtWidgets.QListWidgetItem(short_name)
                    item.setData(QtCore.Qt.UserRole, node_path)
                    self.list_widget.addItem(item)
                    if node_path in desired_selected:
                        item.setSelected(True)
        finally:
            self.list_widget.blockSignals(False)

    def _on_item_double_clicked(self, item):
        QtWidgets.QApplication.clipboard().setText(item.text())

    def _on_selection_changed(self):
        try:
            import maya.cmds as cmds
        except ImportError:
            return
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        node_paths = [i.data(QtCore.Qt.UserRole) for i in selected_items]
        existing = [n for n in node_paths if n and cmds.objExists(n)]
        if existing:
            try:
                cmds.select(existing, replace=True)
            except Exception:
                pass

    def _on_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        menu = QtWidgets.QMenu(self)
        copy_action = menu.addAction("ノード名をコピー")
        select_action = menu.addAction("Mayaで選択")
        action = menu.exec_(self.list_widget.mapToGlobal(pos))
        if action == copy_action:
            QtWidgets.QApplication.clipboard().setText(item.text())
        elif action == select_action:
            try:
                import maya.cmds as cmds
                node_path = item.data(QtCore.Qt.UserRole)
                if node_path and cmds.objExists(node_path):
                    cmds.select(node_path, replace=True)
            except ImportError:
                pass

    # ---- Drag & Drop 受け入れ ----
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(CELL_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(CELL_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(CELL_MIME):
            event.ignore()
            return
        try:
            raw = bytes(event.mimeData().data(CELL_MIME)).decode('utf-8')
            src_row, src_col = [int(x) for x in raw.split(',')]
        except Exception:
            event.ignore()
            return
        event.acceptProposedAction()
        self.cell_dropped.emit(self, src_row, src_col)


class _IntegratedRow(QtWidgets.QWidget):
    """統合ダイアログ内の 1 行分のウィジェット。
    行自体のドラッグ&ドロップ(行順序入れ替え)を受け付ける。"""

    row_dropped = QtCore.Signal(object, int)  # (target_row_widget, src_row_idx)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_idx = -1
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(ROW_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(ROW_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(ROW_MIME):
            event.ignore()
            return
        try:
            raw = bytes(event.mimeData().data(ROW_MIME)).decode('utf-8')
            src_row = int(raw)
        except Exception:
            event.ignore()
            return
        event.acceptProposedAction()
        self.row_dropped.emit(self, src_row)


class IntegratedNodeListDialog(DpiScaleMixin, QtWidgets.QDialog):
    """モデルプリセット単位で管理される統合ダイアログ"""

    def __init__(self, project_index, model_index, parent_widget, parent=None):
        if parent is None:
            try:
                from maya import OpenMayaUI as omui
                from shiboken6 import wrapInstance
                maya_main_window_ptr = omui.MQtUtil.mainWindow()
                parent = wrapInstance(int(maya_main_window_ptr), QtWidgets.QWidget)
            except Exception:
                pass

        super().__init__(parent)
        self._init_dpi_scale()

        self.project_index = project_index
        self.model_index = model_index
        self.parent_widget = parent_widget

        # rows[row_idx] = [cell_widget, cell_widget, ...]
        self._rows = []
        # rows_layout[row_idx] = (row_container_widget, row_hbox_layout)
        self._row_entries = []

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowMaximizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
        )
        self.setWindowModality(QtCore.Qt.NonModal)
        self.setMinimumSize(600, 400)

        self._update_title()
        self._create_ui()
        self._rebuild_from_data()

        # 自動更新タイマー
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.timeout.connect(self._auto_refresh)
        self.update_timer.start(1000)

    # ========== DPI 適応スケーリング ==========

    def _on_dpi_scale_changed(self):
        """DpiScaleMixin からのコールバック: スケール変更時に再構築"""
        self._restyle_static_ui()
        self._rebuild_from_data()

    def _restyle_static_ui(self):
        """ヘッダー/ツールバー等の静的要素にスケールを反映"""
        if hasattr(self, 'header_label') and self.header_label is not None:
            self.header_label.setStyleSheet(
                f"font-weight: bold; font-size: {self._spt(12):.2f}pt; color: rgb(180, 200, 230);"
            )
        if hasattr(self, 'hint_label') and self.hint_label is not None:
            self.hint_label.setStyleSheet(
                f"color: rgb(150,150,150); font-size: {self._spt(9):.2f}pt;"
            )
        # ツールバーボタンのフォントサイズ
        try:
            base_font = QtWidgets.QApplication.font()
        except Exception:
            base_font = self.font()
        f = QtGui.QFont(base_font)
        f.setPointSizeF(max(1.0, self._spt(9)))
        for attr in ('add_row_btn', 'refresh_btn'):
            btn = getattr(self, attr, None)
            if btn is not None:
                btn.setFont(f)

    def showEvent(self, event):
        super().showEvent(event)
        # 表示直後の画面に応じてスケールを適用
        QtCore.QTimer.singleShot(0, lambda: self._apply_dpi_scale_if_changed())

    # ========== UI 構築 ==========

    def _create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        m = self._s(6)
        layout.setContentsMargins(m, m, m, m)
        layout.setSpacing(self._s(6))

        self.header_label = QtWidgets.QLabel("統合ダイアログ")
        self.header_label.setStyleSheet(
            "font-weight: bold; font-size: 12pt; color: rgb(180, 200, 230);"
        )
        self.header_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.header_label)

        # 行追加/更新ツールバー（削除は各行/各セルの個別ボタンで行う）
        toolbar = QtWidgets.QHBoxLayout()
        self.add_row_btn = QtWidgets.QPushButton("+ 行追加")
        self.add_row_btn.clicked.connect(self.add_row)
        toolbar.addWidget(self.add_row_btn)

        self.refresh_btn = QtWidgets.QPushButton("更新")
        self.refresh_btn.clicked.connect(self.on_refresh)
        toolbar.addWidget(self.refresh_btn)

        self.hint_label = QtWidgets.QLabel("(⋮⋮ をドラッグで並び替え)")
        self.hint_label.setStyleSheet("color: rgb(150,150,150); font-size: 9pt;")
        toolbar.addWidget(self.hint_label)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 行のコンテナ(縦)
        self.rows_container = QtWidgets.QWidget()
        self.rows_layout = QtWidgets.QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(6)
        layout.addWidget(self.rows_container, 1)

    # ========== データ <-> UI 同期 ==========

    def _get_model(self):
        if not self.parent_widget:
            return None
        try:
            project = self.parent_widget.projects[self.project_index]
            return project['models'][self.model_index]
        except (IndexError, KeyError, TypeError):
            return None

    def _get_integrated_data(self):
        """model['integrated_dialog'] を取得、無ければデフォルト生成"""
        model = self._get_model()
        if not model:
            return None
        data = model.get('integrated_dialog')
        if not isinstance(data, dict):
            data = {
                'open': False,
                'rows': [{'cells': [{'unique_id': ''}]}],
            }
            model['integrated_dialog'] = data
        # rows が無い/空なら初期化
        rows = data.get('rows')
        if not isinstance(rows, list) or not rows:
            rows = [{'cells': [{'unique_id': ''}]}]
            data['rows'] = rows
        # 各行の cells が無い/空なら初期化
        for row in rows:
            cells = row.get('cells') if isinstance(row, dict) else None
            if not isinstance(cells, list) or not cells:
                row['cells'] = [{'unique_id': ''}]
        return data

    def _rebuild_from_data(self):
        """data 構造から UI を完全に再構築"""
        # 既存の行をクリア
        for entry in self._row_entries:
            row_widget = entry[0]
            self.rows_layout.removeWidget(row_widget)
            row_widget.deleteLater()
        self._row_entries.clear()
        self._rows.clear()

        data = self._get_integrated_data()
        if not data:
            return

        rows_data = data.get('rows', [])
        for row_idx, row_data in enumerate(rows_data):
            self._create_row_widget(row_idx)
            cells = row_data.get('cells', []) if isinstance(row_data, dict) else []
            for cell_data in cells:
                uid = ''
                if isinstance(cell_data, dict):
                    uid = cell_data.get('unique_id', '') or ''
                self._append_cell_widget(row_idx, initial_id=uid)

        self.on_refresh()

    def _create_row_widget(self, row_idx):
        """行 1 つ分のコンテナを作成してレイアウトに追加"""
        row_widget = _IntegratedRow()
        row_widget.row_idx = row_idx
        row_widget.row_dropped.connect(self._on_row_dropped)
        row_outer = QtWidgets.QVBoxLayout(row_widget)
        row_outer.setContentsMargins(0, 0, 0, 0)
        row_outer.setSpacing(self._s(2))

        # 行ツールバー
        row_toolbar = QtWidgets.QHBoxLayout()

        # 行ドラッググリップ
        row_grip = _DragGrip(
            "≡",
            ROW_MIME,
            lambda rw=row_widget: str(rw.row_idx) if rw.row_idx >= 0 else None,
        )
        row_grip.setFixedHeight(self._s(22))
        row_grip.setStyleSheet(
            "QLabel { color: rgb(200,200,200); padding: 0 4px; "
            "background-color: rgba(80,80,100,180); border-radius: 2px; "
            "font-size: 10pt; }"
        )
        row_toolbar.addWidget(row_grip)

        row_label = QtWidgets.QLabel(f"行 {row_idx + 1}")
        row_label.setStyleSheet(
            "color: rgb(180, 180, 180); font-size: 9pt;"
        )
        row_toolbar.addWidget(row_label)

        # 行削除ボタン（フォントサイズはデフォルトの 75%）
        delete_row_btn = QtWidgets.QPushButton("× 行削除")
        delete_row_btn.setFixedHeight(self._s(22))
        delete_row_btn.setFixedWidth(self._s(70))
        base_pt = self.font().pointSizeF()
        if base_pt <= 0:
            base_pt = 9.0
        small_pt = base_pt * 0.75
        delete_row_btn.setStyleSheet(
            "QPushButton { background-color: rgb(120, 70, 70); color: white; "
            f"font-size: {small_pt:.2f}pt; }}"
            "QPushButton:hover { background-color: rgb(160, 80, 80); }"
        )
        delete_row_btn.setToolTip("この行を削除")
        delete_row_btn.clicked.connect(lambda _=False, r=row_idx: self._on_delete_row_clicked(r))
        row_toolbar.addWidget(delete_row_btn)

        row_toolbar.addStretch()
        row_outer.addLayout(row_toolbar)

        # セル横並びレイアウト + 末尾の「+ 列」ボタン
        cells_container = QtWidgets.QWidget()
        cells_hbox = QtWidgets.QHBoxLayout(cells_container)
        cells_hbox.setContentsMargins(0, 0, 0, 0)
        cells_hbox.setSpacing(self._s(4))
        row_outer.addWidget(cells_container, 1)

        # 「+」ボタンは右端のセルの右隣りに置く（青背景・縦はリストと同じ高さに伸縮）
        add_cell_btn = QtWidgets.QPushButton("+")
        add_cell_btn.setFixedWidth(self._s(28))
        add_cell_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
        )
        add_cell_btn.setStyleSheet(
            "QPushButton { background-color: rgb(45, 75, 120); color: white; "
            "font-weight: bold; border-radius: 3px; font-size: 12pt; }"
            "QPushButton:hover { background-color: rgb(55, 90, 140); }"
        )
        add_cell_btn.setToolTip("この行に列を追加")
        add_cell_btn.clicked.connect(lambda _=False, r=row_idx: self.add_cell(r))
        cells_hbox.addWidget(add_cell_btn)

        self.rows_layout.addWidget(row_widget, 1)
        self._row_entries.append((row_widget, cells_hbox, add_cell_btn))
        self._rows.append([])

    def _append_cell_widget(self, row_idx, initial_id=""):
        if row_idx < 0 or row_idx >= len(self._row_entries):
            return
        cell = _IntegratedCell(ui_scale=self._ui_scale)
        cell.unique_id = initial_id
        cell.row_idx = row_idx
        cell.col_idx = len(self._rows[row_idx])
        cell.id_changed.connect(self._on_cell_id_changed)
        cell.delete_requested.connect(self._on_cell_delete_requested)
        cell.cell_dropped.connect(self._on_cell_dropped)
        entry = self._row_entries[row_idx]
        cells_hbox = entry[1]
        add_cell_btn = entry[2]
        # 「+ 列」ボタンの直前にセルを挿入することで、ボタンを常に右端に保つ
        insert_index = cells_hbox.indexOf(add_cell_btn)
        if insert_index < 0:
            cells_hbox.addWidget(cell, 1)
        else:
            cells_hbox.insertWidget(insert_index, cell, 1)
        self._rows[row_idx].append(cell)
        # コンボの選択肢を最新化
        self._refresh_cell_combo(cell, initial_id)

    # ========== 行/列 操作 ==========

    def add_row(self):
        data = self._get_integrated_data()
        if not data:
            return
        if len(data['rows']) >= MAX_ROWS:
            return
        data['rows'].append({'cells': [{'unique_id': ''}]})
        # 先に UI を再構築（self._rows を新しい data に同期させる）してから保存する
        self._rebuild_from_data()
        self._save_to_settings()

    def _on_delete_row_clicked(self, row_idx):
        """行削除ボタンが押されたとき: 確認ダイアログを出してから削除"""
        data = self._get_integrated_data()
        if not data:
            return
        if row_idx < 0 or row_idx >= len(data['rows']):
            return
        if len(data['rows']) <= 1:
            QtWidgets.QMessageBox.information(
                self, "行削除", "最後の 1 行は削除できません。"
            )
            return
        cells_count = len(data['rows'][row_idx].get('cells', []))
        reply = QtWidgets.QMessageBox.question(
            self,
            "行削除の確認",
            f"行 {row_idx + 1} を削除しますか？\n"
            f"この行に含まれる {cells_count} 個のセルも削除されます。",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        self.delete_row(row_idx)

    def delete_row(self, row_idx):
        """指定の行を削除。最後の 1 行は削除不可。"""
        data = self._get_integrated_data()
        if not data:
            return
        if row_idx < 0 or row_idx >= len(data['rows']):
            return
        if len(data['rows']) <= 1:
            return
        del data['rows'][row_idx]
        self._rebuild_from_data()
        self._save_to_settings()

    def add_cell(self, row_idx):
        data = self._get_integrated_data()
        if not data:
            return
        if row_idx < 0 or row_idx >= len(data['rows']):
            return
        row = data['rows'][row_idx]
        cells = row.setdefault('cells', [])
        if len(cells) >= MAX_COLS:
            return
        cells.append({'unique_id': ''})
        self._rebuild_from_data()
        self._save_to_settings()

    def delete_cell(self, row_idx, col_idx):
        """指定セルを削除。その行の最後の 1 セルは削除不可。"""
        data = self._get_integrated_data()
        if not data:
            return
        if row_idx < 0 or row_idx >= len(data['rows']):
            return
        cells = data['rows'][row_idx].get('cells', [])
        if col_idx < 0 or col_idx >= len(cells):
            return
        if len(cells) <= 1:
            return
        del cells[col_idx]
        self._rebuild_from_data()
        self._save_to_settings()

    def _on_cell_delete_requested(self, cell_widget):
        """× ボタン押下時: 自分自身の (row_idx, col_idx) で delete_cell を呼ぶ"""
        self.delete_cell(cell_widget.row_idx, cell_widget.col_idx)

    def _on_cell_dropped(self, target_cell, src_row, src_col):
        """セルがドロップされたとき: src と target を入れ替える"""
        dst_row = target_cell.row_idx
        dst_col = target_cell.col_idx
        if src_row == dst_row and src_col == dst_col:
            return
        data = self._get_integrated_data()
        if not data:
            return
        rows = data['rows']
        if not (0 <= src_row < len(rows) and 0 <= dst_row < len(rows)):
            return
        src_cells = rows[src_row].get('cells', [])
        dst_cells = rows[dst_row].get('cells', [])
        if not (0 <= src_col < len(src_cells) and 0 <= dst_col < len(dst_cells)):
            return
        # 入れ替え
        src_cells[src_col], dst_cells[dst_col] = dst_cells[dst_col], src_cells[src_col]
        self._rebuild_from_data()
        self._save_to_settings()

    def _on_row_dropped(self, target_row_widget, src_row):
        """行がドロップされたとき: src 行を target 行の位置へ入れ替える"""
        dst_row = target_row_widget.row_idx
        if src_row == dst_row:
            return
        data = self._get_integrated_data()
        if not data:
            return
        rows = data['rows']
        if not (0 <= src_row < len(rows) and 0 <= dst_row < len(rows)):
            return
        rows[src_row], rows[dst_row] = rows[dst_row], rows[src_row]
        self._rebuild_from_data()
        self._save_to_settings()

    def _on_cell_id_changed(self, cell_widget, new_id):
        """セル側でコンボの ID が変更されたとき"""
        # 該当セルを探して data に反映
        for row_idx, row_cells in enumerate(self._rows):
            for col_idx, cell in enumerate(row_cells):
                if cell is cell_widget:
                    data = self._get_integrated_data()
                    if data and row_idx < len(data['rows']):
                        cells_data = data['rows'][row_idx].setdefault('cells', [])
                        while len(cells_data) <= col_idx:
                            cells_data.append({'unique_id': ''})
                        cells_data[col_idx]['unique_id'] = new_id
                    self._save_to_settings()
                    self._refresh_single_cell(cell)
                    return

    # ========== フィルタリング / リスト更新 ==========

    def on_refresh(self):
        """全セルのノードリストを再計算"""
        # コンボ選択肢を現在の作業プリセットで更新
        for row_cells in self._rows:
            for cell in row_cells:
                self._refresh_cell_combo(cell, cell.unique_id)
                self._refresh_single_cell(cell)

    def _auto_refresh(self):
        if not self.isVisible():
            return
        focused = QtWidgets.QApplication.focusWidget()
        if focused and self.isAncestorOf(focused):
            return
        self.on_refresh()

    def _get_id_name_pairs(self):
        """現在の作業プリセットのフレーズプリセット ID 一覧を取得"""
        if not self.parent_widget:
            return []
        work = self.parent_widget.get_current_work_preset()
        if not work:
            return []
        pairs = []
        for preset in work.get('phrase_presets', []):
            uid = preset.get('unique_id', '')
            name = preset.get('name', '')
            if uid:
                pairs.append((uid, name))
        return pairs

    def _refresh_cell_combo(self, cell, current_id):
        pairs = self._get_id_name_pairs()
        cell.set_id_options(pairs, current_id)

    def _find_phrase_preset_by_id(self, unique_id):
        """現在の作業プリセット内で unique_id に一致するフレーズプリセットを取得"""
        if not unique_id or not self.parent_widget:
            return None, None
        work = self.parent_widget.get_current_work_preset()
        if not work:
            return None, None
        for preset in work.get('phrase_presets', []):
            if preset.get('unique_id') == unique_id:
                return preset, work
        return None, work

    def _refresh_single_cell(self, cell):
        uid = cell.unique_id
        if not uid:
            cell.set_nodes([], "(未割り当て)")
            return

        phrase_preset, work = self._find_phrase_preset_by_id(uid)
        if not phrase_preset:
            cell.set_nodes([], f"ID={uid} (該当プリセットなし)")
            return

        # モジュール先頭で固定 import 済みのものを使う
        # (関数内 import は他プロジェクトの tools 衝突で失敗するため避ける)
        nf = _mfo

        # CommonNodeListDialog.on_refresh と同等のロジック

        # 共通フィルター
        common_include_configs = []
        common_exclude_configs = []
        if phrase_preset.get('use_common_filter', True) and work:
            for common_phrase in work.get('common_filters', []):
                if not isinstance(common_phrase, dict) or not common_phrase.get('enabled', True):
                    continue
                text = common_phrase.get('text', '').strip()
                if not text:
                    continue
                config = {
                    'text': text,
                    'exact_token': common_phrase.get('exact_token', False)
                }
                if common_phrase.get('exclude', False):
                    common_exclude_configs.append(config)
                else:
                    common_include_configs.append(config)

        # フレーズプリセット側フィルター
        include_configs = []
        exclude_configs = []
        for phrase in phrase_preset.get('phrase_data', []):
            if not isinstance(phrase, dict) or not phrase.get('enabled', True):
                continue
            text = phrase.get('text', '').strip()
            if not text:
                continue
            config = {
                'text': text,
                'exact_token': phrase.get('exact_token', False)
            }
            if phrase.get('exclude', False):
                exclude_configs.append(config)
            else:
                include_configs.append(config)

        match_mode = phrase_preset.get('match_mode', 'any')

        # 登録ノードモード
        show_registered_only = phrase_preset.get('show_registered_only', False)
        apply_filter_to_registered = phrase_preset.get('apply_filter_to_registered', False)
        skip_phrase_filter = False

        include_hierarchy = phrase_preset.get('include_hierarchy', False)

        if show_registered_only:
            registered_uuids = phrase_preset.get('registered_node_uuids', [])
            base_population = []
            try:
                import maya.cmds as cmds
                for r_uid in registered_uuids:
                    if not r_uid:
                        continue
                    try:
                        nodes = cmds.ls(r_uid, long=True)
                    except Exception:
                        nodes = None
                    if nodes:
                        base_population.append(nodes[0])

                # 子階層を含む場合は各登録ノードの子孫を追加
                if include_hierarchy and base_population:
                    seen = set()
                    expanded = []
                    for node in base_population:
                        if node not in seen:
                            seen.add(node)
                            expanded.append(node)
                        try:
                            descendants = cmds.listRelatives(
                                node, allDescendents=True, fullPath=True
                            ) or []
                        except Exception:
                            descendants = []
                        for desc in descendants:
                            if desc not in seen:
                                seen.add(desc)
                                expanded.append(desc)
                    base_population = expanded
            except ImportError:
                pass

            if not apply_filter_to_registered:
                matched_nodes = list(base_population)
                skip_phrase_filter = True
            else:
                if common_include_configs:
                    original_get_all = nf.get_all_nodes
                    nf.get_all_nodes = lambda: list(base_population)
                    try:
                        matched_nodes = nf.filter_nodes_by_phrase_configs(common_include_configs, 'all')
                    finally:
                        nf.get_all_nodes = original_get_all
                else:
                    matched_nodes = list(base_population)
        else:
            if common_include_configs:
                matched_nodes = nf.filter_nodes_by_phrase_configs(common_include_configs, 'all')
            else:
                matched_nodes = nf.get_all_nodes()

        if not skip_phrase_filter and common_exclude_configs:
            common_excluded_nodes = nf.filter_nodes_by_phrase_configs(common_exclude_configs, 'any')
            matched_nodes = [n for n in matched_nodes if n not in common_excluded_nodes]

        if not skip_phrase_filter and include_configs:
            original_get_all = nf.get_all_nodes
            nf.get_all_nodes = lambda: matched_nodes
            try:
                matched_nodes = nf.filter_nodes_by_phrase_configs(include_configs, match_mode)
            finally:
                nf.get_all_nodes = original_get_all

        if not skip_phrase_filter and exclude_configs:
            excluded_nodes = nf.filter_nodes_by_phrase_configs(exclude_configs, 'any')
            matched_nodes = [n for n in matched_nodes if n not in excluded_nodes]

        if phrase_preset.get('dag_only', False):
            try:
                import maya.cmds as cmds
                matched_nodes = [n for n in matched_nodes if cmds.objectType(n, isAType='dagNode')]
            except ImportError:
                pass

        # ノードタイプフィルターを適用
        node_type_filter = phrase_preset.get('node_type_filter', None)
        if node_type_filter and not NodeTypeFilterDialog.is_default(node_type_filter):
            matched_nodes = self._apply_node_type_filter_to_list(
                matched_nodes, node_type_filter
            )

        matched_nodes = sorted(matched_nodes, key=lambda x: x.split('|')[-1].lower())

        work_name = work.get('name', '') if work else ''
        preset_name = phrase_preset.get('name', '')
        title = f"{work_name} / {preset_name} (ID: {uid})"
        cell.set_nodes(matched_nodes, title)

    @staticmethod
    def _apply_node_type_filter_to_list(nodes, node_type_filter):
        """node_list_manager._apply_node_type_filter と同等のロジック（スタンドアロン版）"""
        try:
            import maya.cmds as cmds
        except Exception:
            return nodes

        other_enabled = node_type_filter.get("その他", True)

        allowed_types = set()
        for display_name, maya_types in NODE_TYPE_ENTRIES:
            if display_name == "その他":
                continue
            if node_type_filter.get(display_name, True):
                allowed_types.update(maya_types)

        all_known_types = set()
        for _, maya_types in NODE_TYPE_ENTRIES:
            all_known_types.update(maya_types)

        try:
            node_types = {n: cmds.nodeType(n) for n in nodes}
        except Exception:
            node_types = {}
            for n in nodes:
                try:
                    node_types[n] = cmds.nodeType(n)
                except Exception:
                    pass

        result = []
        for node in nodes:
            nt = node_types.get(node)
            if nt is None:
                continue
            if nt in allowed_types:
                result.append(node)
                continue
            matched_allowed = False
            for t in allowed_types:
                try:
                    if cmds.objectType(node, isAType=t):
                        matched_allowed = True
                        break
                except Exception:
                    pass
            if matched_allowed:
                result.append(node)
                continue
            if other_enabled:
                is_known = nt in all_known_types
                if not is_known:
                    for t in all_known_types:
                        try:
                            if cmds.objectType(node, isAType=t):
                                is_known = True
                                break
                        except Exception:
                            pass
                if not is_known:
                    result.append(node)
        return result

    # ========== ジオメトリ / 保存 ==========

    def _update_title(self):
        model = self._get_model()
        model_name = model.get('name', '') if model else ''
        if model_name:
            self.setWindowTitle(f"統合ダイアログ - {model_name}")
        else:
            self.setWindowTitle("統合ダイアログ")

    def save_layout_to_data(self):
        """現在の分割構成とジオメトリを model['integrated_dialog'] に書き戻す"""
        data = self._get_integrated_data()
        if not data:
            return
        new_rows = []
        for row_cells in self._rows:
            cells_list = [{'unique_id': cell.unique_id or ''} for cell in row_cells]
            if not cells_list:
                cells_list = [{'unique_id': ''}]
            new_rows.append({'cells': cells_list})
        if not new_rows:
            new_rows = [{'cells': [{'unique_id': ''}]}]
        data['rows'] = new_rows
        geo = self.geometry()
        data['geometry'] = {
            'x': geo.x(),
            'y': geo.y(),
            'width': geo.width(),
            'height': geo.height(),
        }
        data['open'] = self.isVisible()

    def save_current_geometry(self):
        data = self._get_integrated_data()
        if not data:
            return
        geo = self.geometry()
        data['geometry'] = {
            'x': geo.x(),
            'y': geo.y(),
            'width': geo.width(),
            'height': geo.height(),
        }

    def _save_to_settings(self):
        self.save_layout_to_data()
        if self.parent_widget and hasattr(self.parent_widget, 'save_settings'):
            self.parent_widget.save_settings()

    def restore_geometry(self):
        data = self._get_integrated_data()
        if not data:
            return
        geo = data.get('geometry')
        if isinstance(geo, dict):
            x = geo.get('x', 100)
            y = geo.get('y', 100)
            w = geo.get('width', 800)
            h = geo.get('height', 500)
            if self.parent_widget and hasattr(self.parent_widget, 'clamp_to_screen'):
                x, y = self.parent_widget.clamp_to_screen(x, y, w, h)
            self.setGeometry(x, y, w, h)

    def moveEvent(self, event):
        super().moveEvent(event)
        if self.isVisible():
            self.save_current_geometry()
            # 画面をまたいで移動した場合は DPI スケールを再適用
            self._apply_dpi_scale_if_changed()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.isVisible():
            self.save_current_geometry()

    def closeEvent(self, event):
        self.update_timer.stop()
        self.save_layout_to_data()
        data = self._get_integrated_data()
        if data is not None:
            if not getattr(self, '_closing_from_main', False):
                data['open'] = False
        if self.parent_widget and hasattr(self.parent_widget, 'integrated_dialogs'):
            key = (self.project_index, self.model_index)
            if key in self.parent_widget.integrated_dialogs:
                del self.parent_widget.integrated_dialogs[key]
        if self.parent_widget and hasattr(self.parent_widget, 'save_settings'):
            self.parent_widget.save_settings()
        super().closeEvent(event)
