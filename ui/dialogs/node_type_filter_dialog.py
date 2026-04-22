# -*- coding: utf-8 -*-
"""
NodeTypeFilterDialog - フレーズプリセットごとのノードタイプ表示フィルター設定ダイアログ
"""

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui


# 表示するノードタイプの定義
# (表示名, Mayaタイプ識別子リスト)
NODE_TYPE_ENTRIES = [
    ("メッシュ (mesh)",          ["mesh"]),
    ("NURBS曲面 (nurbsSurface)", ["nurbsSurface"]),
    ("NURBS曲線 (nurbsCurve)",   ["nurbsCurve"]),
    ("ジョイント (joint)",       ["joint"]),
    ("カメラ (camera)",          ["camera"]),
    ("ライト (light)",           ["light", "directionalLight", "pointLight",
                                  "spotLight", "areaLight", "ambientLight"]),
    ("ロケーター (locator)",     ["locator"]),
    ("グループ/トランスフォーム (transform)", ["transform"]),
    ("ラティス (lattice)",       ["lattice", "baseLattice"]),
    ("クラスター (cluster)",     ["clusterHandle"]),
    ("IK ハンドル (ikHandle)",   ["ikHandle"]),
    ("その他",                    []),   # 上記に該当しないすべて
]

# デフォルトはすべて有効
DEFAULT_NODE_TYPE_FILTER = {entry[0]: True for entry in NODE_TYPE_ENTRIES}


class NodeTypeFilterDialog(QtWidgets.QDialog):
    """ノードタイプ表示フィルター設定ダイアログ"""

    def __init__(self, current_filter=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ノードタイプ フィルター設定")
        self.setModal(True)
        self.setMinimumWidth(320)

        # 渡された設定をベースに、未設定項目はデフォルトで補完
        self._filter = dict(DEFAULT_NODE_TYPE_FILTER)
        if current_filter:
            self._filter.update(current_filter)

        self._checkboxes = {}
        self._create_ui()

    def _create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ヘッダー
        header = QtWidgets.QLabel("表示するノードタイプを選択してください")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        # チェックボックス一覧
        group = QtWidgets.QGroupBox()
        group.setStyleSheet("QGroupBox { border: 1px solid rgba(120,120,120,120); border-radius: 4px; padding: 4px; }")
        group_layout = QtWidgets.QVBoxLayout(group)
        group_layout.setSpacing(4)
        group_layout.setContentsMargins(8, 8, 8, 8)

        for display_name, _ in NODE_TYPE_ENTRIES:
            cb = QtWidgets.QCheckBox(display_name)
            cb.setChecked(self._filter.get(display_name, True))
            group_layout.addWidget(cb)
            self._checkboxes[display_name] = cb

        layout.addWidget(group)

        # 一括操作ボタン
        bulk_layout = QtWidgets.QHBoxLayout()
        all_btn = QtWidgets.QPushButton("すべてON")
        all_btn.clicked.connect(self._check_all)
        none_btn = QtWidgets.QPushButton("すべてOFF")
        none_btn.clicked.connect(self._uncheck_all)
        bulk_layout.addWidget(all_btn)
        bulk_layout.addWidget(none_btn)
        bulk_layout.addStretch()
        layout.addLayout(bulk_layout)

        # OK / キャンセル
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QtWidgets.QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QtWidgets.QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _check_all(self):
        for cb in self._checkboxes.values():
            cb.setChecked(True)

    def _uncheck_all(self):
        for cb in self._checkboxes.values():
            cb.setChecked(False)

    def get_filter(self):
        """現在の設定を dict で返す"""
        return {name: cb.isChecked() for name, cb in self._checkboxes.items()}

    @staticmethod
    def is_default(filter_dict):
        """すべての項目が有効（デフォルト状態）か判定"""
        return all(filter_dict.get(name, True) for name in DEFAULT_NODE_TYPE_FILTER)
