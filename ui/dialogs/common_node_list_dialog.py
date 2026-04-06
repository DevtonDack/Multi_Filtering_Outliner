"""
CommonNodeListDialog - 共通ノードリスト表示用のダイアログ（作業プリセット間で共有）
"""

try:
    from PySide6 import QtWidgets, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtCore


class CommonNodeListDialog(QtWidgets.QDialog):
    """共通ノードリスト表示用のダイアログ（作業プリセット間で共有）"""

    def __init__(self, unique_id="", parent_widget=None, parent=None):
        # Mayaのメインウィンドウを親として取得
        if parent is None:
            try:
                from maya import OpenMayaUI as omui
                from shiboken6 import wrapInstance
                maya_main_window_ptr = omui.MQtUtil.mainWindow()
                parent = wrapInstance(int(maya_main_window_ptr), QtWidgets.QWidget)
            except:
                pass

        super(CommonNodeListDialog, self).__init__(parent)

        self.unique_id = unique_id  # フレーズプリセットのユニークID
        self.parent_widget = parent_widget  # MultiFilteringOutlinerWidgetへの参照
        self.nodes = []

        # ウィンドウフラグを設定
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowMinimizeButtonHint | QtCore.Qt.WindowMaximizeButtonHint | QtCore.Qt.WindowCloseButtonHint)

        # ウィンドウタイトルを設定（プリセット名とIDを表示）
        preset_name = ""
        if parent_widget:
            phrase_preset = parent_widget.get_current_phrase_preset()
            if phrase_preset:
                preset_name = phrase_preset.get('name', '')

        if preset_name and unique_id:
            self.setWindowTitle(f"{preset_name} (ID: {unique_id})")
        elif unique_id:
            self.setWindowTitle(f"共通ダイアログ (ID: {unique_id})")
        else:
            self.setWindowTitle("共通ダイアログ")

        self.setMinimumWidth(400)
        self.setWindowModality(QtCore.Qt.NonModal)

        self.create_ui()
        # ジオメトリは外部から設定されるため、ここでは復元しない
        # self.restore_geometry()
        self.on_refresh()

        # 自動更新タイマーを設定
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.timeout.connect(self.auto_refresh)
        self.update_timer.start(1000)

    def create_ui(self):
        """UIを作成"""
        layout = QtWidgets.QVBoxLayout(self)

        # 共通ダイアログラベル
        common_label = QtWidgets.QLabel("共通ダイアログ")
        common_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: rgb(102, 153, 179);")
        common_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(common_label)

        # ノード数表示
        self.count_label = QtWidgets.QLabel("ノード数: 0")
        layout.addWidget(self.count_label)

        # ノードリストウィジェット
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.list_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        # リスト選択でMayaのノードを選択（update_list中はblockSignalsで無効化）
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.list_widget)

    def get_current_phrase_preset(self):
        """現在の作業プリセットから、このunique_idに一致するフレーズプリセットを取得"""
        if not self.parent_widget:
            return None

        work = self.parent_widget.get_current_work_preset()
        if not work:
            return None

        phrase_presets = work.get('phrase_presets', [])
        for preset in phrase_presets:
            if preset.get('unique_id') == self.unique_id:
                return preset

        return None

    def on_refresh(self):
        """ノードリストを更新"""
        phrase_preset = self.get_current_phrase_preset()
        if not phrase_preset:
            self.nodes = []
            self.update_list()
            self.setWindowTitle(f"共通ダイアログ (ID: {self.unique_id}) - プリセット未検出")
            return

        # ウィンドウタイトルを更新
        work = self.parent_widget.get_current_work_preset()
        work_name = work.get('name', '不明') if work else '不明'
        preset_name = phrase_preset.get('name', '不明')
        self.setWindowTitle(f"共通ダイアログ - {work_name} - {preset_name}")

        # フレーズ設定を収集
        from tools import multi_filtering_outliner as nf

        # 共通フィルターを取得
        common_include_configs = []
        common_exclude_configs = []
        if phrase_preset.get('use_common_filter', True) and work:
            for common_phrase in work.get('common_filters', []):
                config = {
                    'text': common_phrase['text'],
                    'exact_token': common_phrase.get('exact_token', False)
                }
                if common_phrase.get('exclude', False):
                    common_exclude_configs.append(config)
                else:
                    common_include_configs.append(config)

        # フレーズプリセットのフィルターを取得
        include_configs = []
        exclude_configs = []
        for phrase in phrase_preset.get('phrase_data', []):
            if not phrase.get('enabled', True):
                continue
            config = {
                'text': phrase['text'],
                'exact_token': phrase.get('exact_token', False)
            }
            if phrase.get('exclude', False):
                exclude_configs.append(config)
            else:
                include_configs.append(config)

        # フィルタリング実行
        match_mode = phrase_preset.get('match_mode', 'any')

        if common_include_configs:
            matched_nodes = nf.filter_nodes_by_phrase_configs(common_include_configs, 'all')
        else:
            matched_nodes = nf.get_all_nodes()

        if common_exclude_configs:
            common_excluded_nodes = nf.filter_nodes_by_phrase_configs(common_exclude_configs, 'any')
            matched_nodes = [node for node in matched_nodes if node not in common_excluded_nodes]

        if include_configs:
            original_get_all = nf.get_all_nodes
            nf.get_all_nodes = lambda: matched_nodes
            matched_nodes = nf.filter_nodes_by_phrase_configs(include_configs, match_mode)
            nf.get_all_nodes = original_get_all

        if exclude_configs:
            excluded_nodes = nf.filter_nodes_by_phrase_configs(exclude_configs, 'any')
            matched_nodes = [node for node in matched_nodes if node not in excluded_nodes]

        # DAGオブジェクトのみフィルタリング
        dag_only = phrase_preset.get('dag_only', False)
        if dag_only:
            import maya.cmds as cmds
            matched_nodes = [node for node in matched_nodes if cmds.objectType(node, isAType='dagNode')]

        # フルパスでソート（短い名前でソート）
        self.nodes = sorted(matched_nodes, key=lambda x: x.split('|')[-1].lower())
        self.update_list()

    def update_list(self):
        """リストウィジェットを更新"""
        # 現在のフォーカスウィジェットを保存
        focused_widget = QtWidgets.QApplication.focusWidget()

        # シグナルをブロックしてリストを更新
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        self.count_label.setText(f"ノード数: {len(self.nodes)}")
        for node_path in self.nodes:
            short_name = node_path.split('|')[-1]
            item = QtWidgets.QListWidgetItem(short_name)
            item.setData(QtCore.Qt.UserRole, node_path)  # フルパスを保存
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)

        # フォーカスを復元（ダイアログ外のウィジェットにのみ）
        if focused_widget and not self.isAncestorOf(focused_widget):
            focused_widget.setFocus()

    def auto_refresh(self):
        """自動更新（タイマーから呼ばれる）"""
        # ダイアログが表示されている場合のみ更新
        if not self.isVisible():
            return

        # ダイアログにフォーカスがある場合は更新しない
        focused_widget = QtWidgets.QApplication.focusWidget()
        if focused_widget and self.isAncestorOf(focused_widget):
            return

        self.on_refresh()

    def on_item_double_clicked(self, item):
        """アイテムダブルクリック時にクリップボードにコピー"""
        QtWidgets.QApplication.clipboard().setText(item.text())

    def show_context_menu(self, pos):
        """右クリックメニュー表示"""
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
            import maya.cmds as cmds
            node_path = item.data(QtCore.Qt.UserRole)
            if node_path and cmds.objExists(node_path):
                cmds.select(node_path, replace=True)

    def on_selection_changed(self):
        """リスト選択変更時にMayaで選択"""
        import maya.cmds as cmds

        # 現在のフォーカスウィジェットを保存
        focused_widget = QtWidgets.QApplication.focusWidget()

        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return

        # フルパスを取得
        node_paths = []
        for item in selected_items:
            node_path = item.data(QtCore.Qt.UserRole)
            if node_path:
                node_paths.append(node_path)

        # 存在するノードのみを選択
        existing = [n for n in node_paths if cmds.objExists(n)]
        if existing:
            try:
                cmds.select(existing, replace=True)
            except:
                pass

        # フォーカスを復元（このダイアログ外のウィジェットにのみ）
        if focused_widget and not self.isAncestorOf(focused_widget):
            QtCore.QTimer.singleShot(0, lambda: focused_widget.setFocus())

    def restore_geometry(self):
        """ジオメトリを復元"""
        phrase_preset = self.get_current_phrase_preset()
        if phrase_preset and 'common_dialog_geometry' in phrase_preset:
            geometry = phrase_preset['common_dialog_geometry']
            print(f"[DEBUG CommonNodeListDialog.restore_geometry] ID={self.unique_id}, 復元位置: x={geometry['x']}, y={geometry['y']}, w={geometry['width']}, h={geometry['height']}")
            if self.parent_widget:
                current_model = self.parent_widget.get_current_model()
                if current_model:
                    print(f"[DEBUG CommonNodeListDialog.restore_geometry] 現在のモデル: {current_model.get('name')}")
            self.setGeometry(geometry['x'], geometry['y'], geometry['width'], geometry['height'])
        else:
            print(f"[DEBUG CommonNodeListDialog.restore_geometry] ID={self.unique_id}, ジオメトリなし")

    def save_current_geometry(self):
        """現在のジオメトリを保存（移動時に呼ばれる）"""
        # 現在選択中のモデル内のunique_idに一致するフレーズプリセットにのみ保存
        if self.parent_widget and self.unique_id:
            current_model = self.parent_widget.get_current_model()
            if current_model:
                geometry = self.geometry()
                print(f"[DEBUG CommonNodeListDialog.save_current_geometry] ID={self.unique_id}, モデル={current_model.get('name')}, 保存位置: x={geometry.x()}, y={geometry.y()}, w={geometry.width()}, h={geometry.height()}")
                for work in current_model.get('works', []):
                    for preset in work.get('phrase_presets', []):
                        if preset.get('unique_id') == self.unique_id:
                            preset['common_dialog_geometry'] = {
                                'x': geometry.x(),
                                'y': geometry.y(),
                                'width': geometry.width(),
                                'height': geometry.height()
                            }
                            print(f"[DEBUG CommonNodeListDialog.save_current_geometry] フレーズプリセット '{preset.get('name')}' に保存しました")

    def closeEvent(self, event):
        """ダイアログが閉じられる時"""
        self.update_timer.stop()


        # unique_idに一致するフレーズプリセットを全プロジェクト・モデル・作業から検索
        phrase_preset = None
        if self.parent_widget and self.unique_id:
            for project in self.parent_widget.projects:
                for model in project.get('models', []):
                    for work in model.get('works', []):
                        for preset in work.get('phrase_presets', []):
                            if preset.get('unique_id') == self.unique_id:
                                phrase_preset = preset
                                break
                        if phrase_preset:
                            break
                    if phrase_preset:
                        break
                if phrase_preset:
                    break

        if phrase_preset:
            geometry = self.geometry()
            phrase_preset['common_dialog_geometry'] = {
                'x': geometry.x(),
                'y': geometry.y(),
                'width': geometry.width(),
                'height': geometry.height()
            }

            # メインウィンドウから閉じられた場合はcommon_dialog_openフラグを変更しない
            if not hasattr(self, '_closing_from_main') or not self._closing_from_main:
                # ユーザーが直接閉じた場合のみcommon_dialog_openをFalseに設定
                phrase_preset['common_dialog_open'] = False

            if self.parent_widget:
                self.parent_widget.save_settings()

        if self.parent_widget and self.unique_id in self.parent_widget.common_dialogs:
            del self.parent_widget.common_dialogs[self.unique_id]

        super().closeEvent(event)
