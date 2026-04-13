# -*- coding: utf-8 -*-
"""
DpiScaleMixin - DPI/解像度適応スケーリング

4K モニター (logicalDPI=144) の見た目を「拡大しない 1.0 のベース」とし、
低 DPI 環境のみ縮小方向にスケールする。
scale = clamp(logicalDPI / base_dpi, 0.5, 1.0)

使い方:
  class MyDialog(DpiScaleMixin, QDialog):
      def __init__(self, ...):
          super().__init__(parent)
          self._init_dpi_scale()  # __init__ の冒頭で呼ぶ
          ...
"""

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui


class DpiScaleMixin:
    """DPI 適応スケーリングを提供する Mixin。

    QWidget (QDialog / QWidget) のサブクラスに組み込む。
    self._ui_scale (float) をウィジェット構築前にセットする。
    showEvent / moveEvent をフックして画面移動時に再適用する。
    """

    # 起動時に全スクリーンの最大 logicalDPI を検出して基準とする
    _base_dpi = None

    @classmethod
    def _ensure_base_dpi(cls):
        """全スクリーンを走査して最大 logicalDPI を基準値として設定"""
        if cls._base_dpi is not None:
            return
        max_dpi = 96.0
        try:
            app = QtWidgets.QApplication.instance()
            if app:
                for scr in app.screens():
                    try:
                        d = scr.logicalDotsPerInch()
                        if d > max_dpi:
                            max_dpi = d
                    except Exception:
                        pass
        except Exception:
            pass
        cls._base_dpi = max_dpi
        print(f"[DEBUG DPI] base_dpi={cls._base_dpi}")

    def _init_dpi_scale(self):
        """__init__ の冒頭で呼ぶ。ウィジェット構築前に _ui_scale を確定させる。"""
        self._ensure_base_dpi()
        self._ui_scale = 1.0
        self._last_screen_name = None
        self._dpi_scale_initialized = False
        try:
            initial_screen = QtWidgets.QApplication.primaryScreen()
            if initial_screen is not None:
                self._ui_scale = self._compute_ui_scale_for_screen(initial_screen)
                self._last_screen_name = self._screen_id(initial_screen)
        except Exception:
            pass

    # ========== スケール算出 ==========

    @staticmethod
    def _screen_id(screen):
        """スクリーンの識別キーを返す（name + geometry で一意化）"""
        try:
            g = screen.geometry()
            return f"{screen.name()}_{g.x()}_{g.y()}_{g.width()}_{g.height()}"
        except Exception:
            return None

    @classmethod
    def _compute_ui_scale_for_screen(cls, screen):
        """logicalDPI からUI スケール係数を算出。

        最大 logicalDPI のモニターを 1.0 として、
        低 DPI モニターでは縮小方向にスケールする。
        """
        if screen is None:
            return 1.0
        try:
            dpi = screen.logicalDotsPerInch()
            print(f"[DEBUG DPI] screen={screen.name()}, logicalDPI={dpi}, base_dpi={cls._base_dpi}")
        except Exception:
            return 1.0
        if dpi <= 0:
            return 1.0
        base = cls._base_dpi if cls._base_dpi and cls._base_dpi > 0 else 96.0
        scale = dpi / base
        if scale > 1.0:
            scale = 1.0
        if scale < 0.5:
            scale = 0.5
        print(f"[DEBUG DPI] scale={scale}")
        return scale

    def _detect_screen(self):
        """このウィジェットが現在表示されている画面を取得"""
        try:
            scr = self.screen()
            if scr is not None:
                return scr
        except Exception:
            pass
        try:
            wh = self.windowHandle()
            if wh is not None:
                scr = wh.screen()
                if scr is not None:
                    return scr
        except Exception:
            pass
        try:
            return QtWidgets.QApplication.primaryScreen()
        except Exception:
            return None

    def _s(self, value):
        """ピクセル値をスケーリングして int で返す"""
        return int(round(value * self._ui_scale))

    def _spt(self, pt):
        """pt 値を返す（スケーリングなし）。

        Qt は pt → px 変換時に logicalDPI を自動使用するため、
        同じ pt 値であれば各モニターで適切なピクセル数に変換される。
        4K (logicalDPI=144) で 10pt=20px、FHD (logicalDPI=96) で 10pt≒13px
        となり、物理的に近い大きさで表示される。
        """
        return float(pt)

    # ========== 再適用 ==========

    def _apply_dpi_scale_if_changed(self):
        """画面変更を検出してスケールを更新。
        サブクラスは _on_dpi_scale_changed() をオーバーライドして
        UI 再構築を行う。"""
        screen = self._detect_screen()
        if screen is None:
            return
        screen_id = self._screen_id(screen)
        if screen_id == self._last_screen_name and self._dpi_scale_initialized:
            return
        new_scale = self._compute_ui_scale_for_screen(screen)
        self._last_screen_name = screen_id
        scale_changed = abs(new_scale - self._ui_scale) > 0.01
        if (not scale_changed) and self._dpi_scale_initialized:
            self._dpi_scale_initialized = True
            return
        self._ui_scale = new_scale
        self._dpi_scale_initialized = True
        print(f"[DEBUG DPI] _on_dpi_scale_changed triggered, scale={new_scale}")
        self._on_dpi_scale_changed()

    def _on_dpi_scale_changed(self):
        """スケール変更時に呼ばれる。サブクラスでオーバーライドする。"""
        pass
