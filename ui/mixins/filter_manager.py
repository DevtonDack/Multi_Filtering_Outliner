# -*- coding: utf-8 -*-
"""
FilterManagerMixin - Common filter management operations
"""

from PySide6 import QtWidgets
from ui.widgets import DraggablePhraseWidget


class FilterManagerMixin:
    """フィルター管理を提供するMixin"""

    # ========== Common Filter Management ==========

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
            return

        # UIが破棄されている場合は保存しない
        if not hasattr(self, 'common_filter_container_layout') or self.common_filter_container_layout is None:
            return

        work = self.get_current_work_preset()
        if not work:
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

    def _get_common_filter_columns(self):
        """1 行あたりの共通フィルター列数（デフォルト 2）"""
        return getattr(self, 'common_filter_columns', 2)

    def _collect_common_filter_widgets(self):
        widgets = []
        for i in range(self.common_filter_container_layout.count()):
            item = self.common_filter_container_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), DraggablePhraseWidget):
                widgets.append(item.widget())
        return widgets

    def _repack_common_filter_widgets(self, widgets=None):
        if widgets is None:
            widgets = self._collect_common_filter_widgets()
        for w in widgets:
            self.common_filter_container_layout.removeWidget(w)
        cols = self._get_common_filter_columns()
        for i, w in enumerate(widgets):
            self.common_filter_container_layout.addWidget(w, i // cols, i % cols)

    def add_common_filter_row(self, text='', enabled=True, exclude=False, exact_token=False):
        """共通フィルター入力行を追加（2 列グリッド）"""
        filter_widget = DraggablePhraseWidget(text, enabled, exclude, exact_token, self.common_filter_container)
        filter_widget.phrase_input.textChanged.connect(self.on_common_filter_changed)
        filter_widget.enabled_check.stateChanged.connect(self.on_common_filter_changed)
        filter_widget.exclude_check.stateChanged.connect(self.on_common_filter_changed)
        filter_widget.exact_token_check.stateChanged.connect(self.on_common_filter_changed)
        filter_widget.remove_btn.clicked.connect(lambda: self.on_remove_common_filter(filter_widget))

        cols = self._get_common_filter_columns()
        count = self.common_filter_container_layout.count()
        self.common_filter_container_layout.addWidget(filter_widget, count // cols, count % cols)

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

        # ウィジェットを削除してからグリッドを詰める
        self.common_filter_container_layout.removeWidget(filter_widget)
        filter_widget.deleteLater()
        self._repack_common_filter_widgets()

        # フィルターを更新
        self.on_common_filter_changed()

    def on_remove_last_common_filter(self):
        """最後の共通フィルター入力を削除"""
        if self.common_filter_container_layout.count() > 1:
            widgets = self._collect_common_filter_widgets()
            if widgets:
                self.on_remove_common_filter(widgets[-1])

    def on_common_filter_changed(self):
        """共通フィルターが変更された時"""
        # 初期化中は保存しない
        if getattr(self, '_is_loading', False):
            return
        self.save_common_filters_state()
        self.on_filter_changed()

    def on_filter_changed(self):
        """フィルタが変更された時（自動更新）"""
        # 読み込み中は保存・リフレッシュを行わない
        if getattr(self, '_is_loading', False):
            return

        # 現在のフレーズプリセットの状態を保存（ダイアログが最新の設定を参照できるように）
        if self.current_phrase_preset_index >= 0:
            self.save_current_phrase_preset_state()

        self.on_refresh()

        # フレーズ変更時に自動保存
        self.save_settings()
