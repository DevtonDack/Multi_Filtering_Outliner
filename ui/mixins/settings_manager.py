"""
SettingsManagerMixin - 設定ファイルの保存・読み込み管理
"""

import json
import os


# 設定ファイルのパス（メインファイルからインポート）
SETTINGS_DIR = os.path.expanduser("~/.multi_filtering_outliner")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "multi_filtering_outliner_settings.json")


class SettingsManagerMixin:
    """設定の保存・読み込みを管理するMixin"""

    def save_settings(self):
        """設定をファイルに保存"""
        try:
            # 読み込み中は状態を保存しない
            if getattr(self, '_is_loading', False):
                # プロジェクト構造のみを保存
                os.makedirs(SETTINGS_DIR, exist_ok=True)
                settings = {
                    'version': 2,
                    'projects': self.projects,
                    'current_project_index': self.current_project_index,
                    'current_model_index': self.current_model_index,
                    'current_work_index': self.current_work_index,
                    'last_import_path': self.last_import_path,
                    'last_export_path': self.last_export_path,
                    'lists': self.outliner_lists,
                    'current_index': self.current_list_index
                }
                with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
                print(f"Multi Filtering Outliner: 設定を保存しました（読み込み中）: {SETTINGS_FILE}")
                return

            # 現在の状態を保存
            if self.current_work_index >= 0:
                self.save_common_filters_state()
            if self.current_phrase_preset_index >= 0:
                self.save_current_phrase_preset_state()
            self.save_current_work_state()

            # ディレクトリがなければ作成
            os.makedirs(SETTINGS_DIR, exist_ok=True)

            settings = {
                'version': 2,  # 階層構造バージョン
                'projects': self.projects,
                'current_project_index': self.current_project_index,
                'current_model_index': self.current_model_index,
                'current_work_index': self.current_work_index,
                'last_import_path': self.last_import_path,
                'last_export_path': self.last_export_path,
                # 旧形式との互換性のため保持（マイグレーション用）
                'lists': self.outliner_lists,
                'current_index': self.current_list_index
            }

            # デバッグ: 各モデルのwindow_geometryを確認
            print(f"[DEBUG save_settings] ========== 保存内容確認 ==========")
            print(f"[DEBUG save_settings] 現在のウィンドウ位置: x={self.geometry().x()}, y={self.geometry().y()}, w={self.geometry().width()}, h={self.geometry().height()}")
            print(f"[DEBUG save_settings] current_model_index={self.current_model_index}")
            for proj_idx, project in enumerate(self.projects):
                print(f"[DEBUG save_settings] プロジェクト[{proj_idx}]: {project.get('name')}")
                for model_idx, model in enumerate(project.get('models', [])):
                    has_geometry = 'window_geometry' in model
                    is_current = (proj_idx == self.current_project_index and model_idx == self.current_model_index)
                    current_marker = " ★現在選択中★" if is_current else ""
                    if has_geometry:
                        geom = model['window_geometry']
                        print(f"[DEBUG save_settings]   モデル[{model_idx}] '{model.get('name')}'{current_marker}: window_geometry有 (x={geom.get('x')}, y={geom.get('y')}, w={geom.get('width')}, h={geom.get('height')})")
                    else:
                        print(f"[DEBUG save_settings]   モデル[{model_idx}] '{model.get('name')}'{current_marker}: window_geometry無")

            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            print(f"Multi Filtering Outliner: 設定を保存しました: {SETTINGS_FILE}")

        except Exception as e:
            print(f"Multi Filtering Outliner: 設定の保存に失敗: {e}")

    def load_settings(self):
        """設定をファイルから読み込み"""
        try:
            if not os.path.exists(SETTINGS_FILE):
                # 旧設定ファイルからの移行を試みる
                old_settings_file = os.path.expanduser("~/.ez_modeling_tools/node_filter_settings.json")
                if os.path.exists(old_settings_file):
                    print("Multi Filtering Outliner: 旧設定ファイルを発見しました。移行します...")
                    try:
                        with open(old_settings_file, 'r', encoding='utf-8') as f:
                            old_settings = json.load(f)
                        # 新しいディレクトリを作成
                        os.makedirs(SETTINGS_DIR, exist_ok=True)
                        # 旧設定を新しい場所にコピー
                        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                            json.dump(old_settings, f, indent=2, ensure_ascii=False)
                        print(f"Multi Filtering Outliner: 設定を移行しました: {SETTINGS_FILE}")
                        # 移行した設定を読み込む
                        settings = old_settings
                    except Exception as e:
                        print(f"Multi Filtering Outliner: 旧設定の移行に失敗しました: {e}")
                        print("Multi Filtering Outliner: デフォルト階層を作成します")
                        self.create_default_hierarchy()
                        return
                else:
                    # デフォルトで階層を作成
                    print("Multi Filtering Outliner: 設定ファイルが存在しないため、デフォルト階層を作成します")
                    self.create_default_hierarchy()
                    return
            else:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

            version = settings.get('version', 1)

            # 最後に使用したパスを読み込み
            self.last_import_path = settings.get('last_import_path', "")
            self.last_export_path = settings.get('last_export_path', "")

            if version == 2:
                # 新形式（階層構造）
                self.projects = settings.get('projects', [])
                self.current_project_index = settings.get('current_project_index', -1)
                self.current_model_index = settings.get('current_model_index', -1)
                self.current_work_index = settings.get('current_work_index', -1)

                if not self.projects:
                    self.create_default_hierarchy()
                    return

                # UUID形式のIDを数字形式に一括変換
                self.migrate_uuid_to_numeric_ids()

                # 欠けているフィールドのデフォルト値を設定
                self.ensure_phrase_preset_fields()

                # プロジェクトのコンボボックスを更新
                for project in self.projects:
                    self.project_combo.addItem(project['name'])

                # 前回の選択状態を復元
                if 0 <= self.current_project_index < len(self.projects):
                    self.project_combo.setCurrentIndex(self.current_project_index)
                else:
                    self.project_combo.setCurrentIndex(0)

                print(f"Multi Filtering Outliner: 設定を読み込みました（階層構造）: {SETTINGS_FILE}")

            else:
                # 旧形式からマイグレーション
                print("Multi Filtering Outliner: 旧形式の設定を階層構造に変換します")
                self.migrate_from_old_format(settings)

            # current_model_indexが未設定の場合、設定から復元
            if self.current_model_index < 0:
                self.current_model_index = settings.get('current_model_index', -1)

            # 前回開いていたダイアログを復元
            self.restore_dialogs()

        except Exception as e:
            print(f"Multi Filtering Outliner: 設定の読み込みに失敗: {e}")
            import traceback
            traceback.print_exc()
            self.create_default_hierarchy()

    def create_default_hierarchy(self):
        """デフォルトの階層構造を作成"""
        default_project = {
            'name': 'プロジェクト1',
            'models': [
                {
                    'name': 'モデル1',
                    'works': [
                        {
                            'name': '作業1',
                            'common_filters': [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}],
                            'phrase_presets': [
                                {
                                    'name': 'フレーズ1',
                                    'unique_id': '1',
                                    'phrase_data': [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}],
                                    'match_mode': 'any',
                                    'dag_only': False,
                                    'use_common_filter': True,
                                    'use_common_dialog': False,
                                    'dialog_open': False,
                                    'common_dialog_open': False
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        self.projects = [default_project]
        self.project_combo.addItem(default_project['name'])
        self.project_combo.setCurrentIndex(0)
        self.on_project_changed(0)
