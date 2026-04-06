"""
NodeListDialog - ノードリスト表示用のダイアログ（専用ダイアログ）
"""

try:
    from PySide6 import QtWidgets, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtCore


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
        self.parent_widget = parent_widget  # MultiFilteringOutlinerWidgetへの参照

        # ウィンドウフラグを設定（タイトルの前に設定する必要がある）
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowMinimizeButtonHint | QtCore.Qt.WindowMaximizeButtonHint | QtCore.Qt.WindowCloseButtonHint)

        # ウィンドウタイトルを設定（プリセット名とIDを表示）
        # このダイアログに関連付けられたフレーズプリセット情報を取得
        preset_name = ""
        preset_id = ""
        if parent_widget and phrase_index >= 0:
            project_idx, model_idx, work_idx = work_indices
            if project_idx >= 0 and model_idx >= 0 and work_idx >= 0:
                projects = parent_widget.projects
                if project_idx < len(projects):
                    models = projects[project_idx].get('models', [])
                    if model_idx < len(models):
                        works = models[model_idx].get('works', [])
                        if work_idx < len(works):
                            phrase_presets = works[work_idx].get('phrase_presets', [])
                            if phrase_index < len(phrase_presets):
                                phrase_preset = phrase_presets[phrase_index]
                                preset_name = phrase_preset.get('name', '')
                                preset_id = phrase_preset.get('unique_id', '')

        if preset_name and preset_id:
            window_title = f"{preset_name} (ID: {preset_id})"
        elif preset_name:
            window_title = preset_name
        else:
            window_title = "ノードリスト"
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

        # ノード数表示
        self.title_label = QtWidgets.QLabel(f"ノードリスト ({len(self.nodes)}個)")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
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
        from tools import multi_filtering_outliner as nf

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
        # 現在のフォーカスウィジェットを保存
        focused_widget = QtWidgets.QApplication.focusWidget()

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

        # フォーカスを復元（ダイアログ外のウィジェットにのみ）
        if focused_widget and not self.isAncestorOf(focused_widget):
            focused_widget.setFocus()

    def auto_refresh(self):
        """自動更新（定期的に呼ばれる）"""
        # ダイアログが表示されている場合のみ更新
        if not self.isVisible():
            return

        # ダイアログにフォーカスがある場合は更新しない
        focused_widget = QtWidgets.QApplication.focusWidget()
        if focused_widget and self.isAncestorOf(focused_widget):
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
