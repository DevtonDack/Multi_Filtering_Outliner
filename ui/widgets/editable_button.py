"""
EditableButton - ダブルクリックで編集可能、ドラッグ&ドロップで並べ替え可能なボタン
"""

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui


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
