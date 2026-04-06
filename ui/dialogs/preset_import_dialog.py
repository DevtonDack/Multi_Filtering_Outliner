"""
PresetImportDialog - プリセットインポート時の選択ダイアログ（リスト形式）
"""

try:
    from PySide6 import QtWidgets, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtCore


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
