"""
DraggablePhraseWidget - ドラッグ&ドロップ可能なフレーズ行ウィジェット
"""

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui


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
        self.drag_handle = QtWidgets.QLabel("⋮⋮")
        self.drag_handle.setStyleSheet("color: gray; font-weight: bold;")
        self.drag_handle.setFixedWidth(20)
        self.drag_handle.setCursor(QtCore.Qt.OpenHandCursor)
        layout.addWidget(self.drag_handle)

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
        self.dragging_from_handle = False

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
            # ドラッグハンドル上でクリックされたかチェック
            handle_rect = self.drag_handle.geometry()
            if handle_rect.contains(event.pos()):
                self.drag_start_position = event.pos()
                self.dragging_from_handle = True
            else:
                self.dragging_from_handle = False
        super(DraggablePhraseWidget, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """マウス移動イベント - ドラッグ開始"""
        if not (event.buttons() & QtCore.Qt.LeftButton):
            return
        if not self.drag_start_position or not self.dragging_from_handle:
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

        # ドラッグ完了後リセット
        self.dragging_from_handle = False

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

            # 親ウィジェット（MultiFilteringOutlinerWidget）に通知
            # Note: MultiFilteringOutlinerWidgetのインポートは循環参照を避けるため遅延インポート
            source_widget = event.source()
            if source_widget and source_widget != self:
                from ui.multi_filtering_outliner_ui import MultiFilteringOutlinerWidget
                parent_widget = self.parent()
                while parent_widget and not isinstance(parent_widget, MultiFilteringOutlinerWidget):
                    parent_widget = parent_widget.parent()
                if parent_widget:
                    parent_widget.swap_phrase_rows(source_widget, self)
        else:
            event.ignore()
