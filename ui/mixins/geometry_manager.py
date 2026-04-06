"""
GeometryManagerMixin - ウィンドウとダイアログのジオメトリ管理
"""

try:
    from PySide6 import QtCore
except ImportError:
    from PySide2 import QtCore


class GeometryManagerMixin:
    """ウィンドウ位置・サイズの保存・復元を管理するMixin"""

    def save_model_geometry(self):
        """現在のモデルプリセットのジオメトリを保存"""
        project = self.get_current_project()
        model = self.get_current_model()

        print(f"[DEBUG save_model_geometry] current_model_index={self.current_model_index}")
        print(f"[DEBUG save_model_geometry] project={project.get('name') if project else None}")
        print(f"[DEBUG save_model_geometry] model={model.get('name') if model else None}")

        if model:
            geometry = self.geometry()
            model['window_geometry'] = {
                'x': geometry.x(),
                'y': geometry.y(),
                'width': geometry.width(),
                'height': geometry.height()
            }
            print(f"[DEBUG save_model_geometry] モデル '{model.get('name')}' のジオメトリを保存: x={geometry.x()}, y={geometry.y()}, w={geometry.width()}, h={geometry.height()}")

            # 保存直後の確認
            if 'window_geometry' in model:
                saved = model['window_geometry']
                print(f"[DEBUG save_model_geometry] 保存確認: x={saved.get('x')}, y={saved.get('y')}, w={saved.get('width')}, h={saved.get('height')}")
        else:
            print(f"[DEBUG save_model_geometry] モデルが見つかりません")

    def restore_model_geometry(self):
        """現在のモデルプリセットのジオメトリを復元"""
        project = self.get_current_project()
        model = self.get_current_model()

        print(f"[DEBUG restore_model_geometry] current_model_index={self.current_model_index}")
        print(f"[DEBUG restore_model_geometry] project={project.get('name') if project else None}")
        print(f"[DEBUG restore_model_geometry] model={model.get('name') if model else None}")

        if model:
            if 'window_geometry' in model:
                geometry_data = model['window_geometry']
                x = geometry_data.get('x')
                y = geometry_data.get('y')
                width = geometry_data.get('width', 800)
                height = geometry_data.get('height', 600)

                print(f"[DEBUG restore_model_geometry] モデル '{model.get('name')}' のジオメトリを復元: x={x}, y={y}, w={width}, h={height}")
                if x is not None and y is not None:
                    self.setGeometry(x, y, width, height)
                    print(f"[DEBUG restore_model_geometry] setGeometry実行後の実際の位置: x={self.geometry().x()}, y={self.geometry().y()}")
                else:
                    self.resize(width, height)
            else:
                # デフォルトサイズ
                print(f"[DEBUG restore_model_geometry] モデル '{model.get('name')}' にジオメトリ情報なし - デフォルトサイズを使用")
                self.resize(800, 600)
        else:
            print(f"[DEBUG restore_model_geometry] モデルが見つかりません")

    def moveEvent(self, event):
        """ウィンドウが移動された時に呼ばれる"""
        super().moveEvent(event)
        if not hasattr(self, '_is_loading') or not self._is_loading:
            new_pos = event.pos()
            model = self.get_current_model()
            if model:
                print(f"[DEBUG moveEvent] ウィンドウ移動: x={new_pos.x()}, y={new_pos.y()}, モデル='{model.get('name')}'")

    def resizeEvent(self, event):
        """ウィンドウがリサイズされた時に呼ばれる"""
        super().resizeEvent(event)
        if not hasattr(self, '_is_loading') or not self._is_loading:
            new_size = event.size()
            model = self.get_current_model()
            if model:
                print(f"[DEBUG resizeEvent] ウィンドウリサイズ: w={new_size.width()}, h={new_size.height()}, モデル='{model.get('name')}')")
