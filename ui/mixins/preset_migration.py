# -*- coding: utf-8 -*-
"""
PresetMigrationMixin - Data format migration and compatibility operations
"""

from PySide6 import QtWidgets
import copy


class PresetMigrationMixin:
    """データマイグレーションと互換性処理を提供するMixin"""

    # ========== Format Import Methods ==========

    def import_hierarchical_preset(self, import_data, file_path):
        """階層構造プリセットをインポート"""
        import copy

        imported_projects = import_data.get('projects', [])
        if not imported_projects:
            print("インポートするプロジェクトがありません")
            return

        # 単純に全プロジェクトをマージ（同名プロジェクトは番号付与）
        for project in imported_projects:
            project_name = project.get('name', 'プロジェクト')

            # 同名プロジェクトがあれば番号を付ける
            counter = 1
            new_name = project_name
            existing_names = [p['name'] for p in self.projects]
            while new_name in existing_names:
                new_name = f"{project_name}_{counter}"
                counter += 1

            project['name'] = new_name
            self.projects.append(copy.deepcopy(project))
            self.project_combo.addItem(new_name)

        # 最初にインポートしたプロジェクトに切り替え
        if self.projects:
            self.project_combo.setCurrentIndex(len(self.projects) - len(imported_projects))

        self.last_import_path = os.path.dirname(file_path)
        print(f"{len(imported_projects)}個のプロジェクトを読み込みました: {file_path}")
        self.save_settings()

    def import_flat_preset(self, import_data, file_path):
        """旧形式（フラット）プリセットをインポート - 現在のモデルの作業プリセットとして追加"""
        import copy

        # 現在のモデルを取得
        model = self.get_current_model()
        if not model:
            QtWidgets.QMessageBox.warning(
                self,
                "警告",
                "旧形式のプリセットをインポートするには、先にプロジェクトとモデルを選択してください"
            )
            return

        # 新しい形式（複数プリセット）か古い形式（単一プリセット）かを判定
        if 'lists' in import_data and isinstance(import_data['lists'], list):
            # 新しい形式：複数プリセット
            presets_to_import = import_data['lists']
        elif 'name' in import_data:
            # 古い形式：単一プリセット
            presets_to_import = [import_data]
        else:
            raise ValueError("無効なプリセットファイル形式です")

        # プリセットデータの検証と補完
        for preset_data in presets_to_import:
            if 'name' not in preset_data:
                preset_data['name'] = f"作業_{len(model.get('works', [])) + 1}"

            # 旧形式の場合は新形式に変換
            if 'phrase_presets' not in preset_data:
                # phrase_dataがある場合は、それをフレーズプリセットに変換
                phrase_data = preset_data.get('phrase_data', [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}])
                match_mode = preset_data.get('match_mode', 'any')
                dag_only = preset_data.get('dag_only', False)

                preset_data['phrase_presets'] = [
                    {
                        'name': 'フレーズ1',
                        'phrase_data': phrase_data,
                        'match_mode': match_mode,
                        'dag_only': dag_only
                    }
                ]
                # 旧形式のキーを削除（オプション）
                # preset_data.pop('phrase_data', None)
                # preset_data.pop('match_mode', None)
                # preset_data.pop('dag_only', None)

            # 共通フィルターを追加
            if 'common_filters' not in preset_data:
                preset_data['common_filters'] = [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}]

            # 各フレーズプリセットにuse_common_filterを追加（存在しない場合）
            for phrase_preset in preset_data.get('phrase_presets', []):
                if 'use_common_filter' not in phrase_preset:
                    phrase_preset['use_common_filter'] = True

        # 既存の作業プリセット名を取得
        existing_names = [work['name'] for work in model.get('works', [])]

        # プリセット選択ダイアログを表示
        dialog = PresetImportDialog(presets_to_import, existing_names, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            print("プリセットの読み込みをキャンセルしました")
            return

        # ユーザーの選択を取得
        choices = dialog.get_import_choices()

        imported_count = 0
        overwritten_count = 0
        skipped_count = 0
        first_imported_index = -1

        if 'works' not in model:
            model['works'] = []

        for choice in choices:
            preset_data = choice['data'].copy()  # データをコピーして使用
            import_mode = choice['mode']
            preset_name = preset_data.get('name', 'Unknown')  # データ内の名前を使用

            if import_mode == 'skip':
                skipped_count += 1
                print(f"作業プリセット '{preset_name}' をスキップしました")
                continue

            elif import_mode == 'overwrite':
                # 既存のプリセットを上書き
                existing_index = next(
                    (i for i, work in enumerate(model['works']) if work['name'] == preset_name),
                    None
                )
                if existing_index is not None:
                    # データをディープコピーして上書き
                    model['works'][existing_index] = copy.deepcopy(preset_data)
                    # 最初にインポートされたプリセットのインデックスを記録
                    if first_imported_index < 0:
                        first_imported_index = existing_index
                    # 現在表示中のプリセットを上書きした場合はUIを更新
                    if existing_index == self.current_work_index:
                        self.load_work_to_ui(existing_index)
                    overwritten_count += 1
                    print(f"作業プリセット '{preset_name}' を上書きしました")
                else:
                    # 存在しない場合は新規追加（念のため）
                    model['works'].append(copy.deepcopy(preset_data))
                    new_index = len(model['works']) - 1
                    if first_imported_index < 0:
                        first_imported_index = new_index
                    self.create_work_button(new_index)
                    imported_count += 1
                    print(f"作業プリセット '{preset_name}' を読み込みました")

            elif import_mode == 'rename':
                # 名前を変えて読み込み
                original_name = preset_data['name']
                counter = 1
                new_name = original_name
                while any(work['name'] == new_name for work in model['works']):
                    new_name = f"{original_name}_{counter}"
                    counter += 1

                # 新しい名前を設定
                preset_data['name'] = new_name

                # プリセットをリストに追加（ディープコピー）
                model['works'].append(copy.deepcopy(preset_data))
                new_index = len(model['works']) - 1

                # 最初にインポートされたプリセットのインデックスを記録
                if first_imported_index < 0:
                    first_imported_index = new_index

                # ボタンを作成
                self.create_work_button(new_index)
                imported_count += 1
                print(f"作業プリセット '{new_name}' を読み込みました")

        # 最初にインポートされたプリセットに切り替え
        if first_imported_index >= 0:
            self.switch_to_work(first_imported_index)

        # 最後に使用したパスを保存（ディレクトリ部分のみ）
        self.last_import_path = os.path.dirname(file_path)

        # 結果をサマリー表示
        summary_parts = []
        if imported_count > 0:
            summary_parts.append(f"新規: {imported_count}個")
        if overwritten_count > 0:
            summary_parts.append(f"上書き: {overwritten_count}個")
        if skipped_count > 0:
            summary_parts.append(f"スキップ: {skipped_count}個")

        summary = ", ".join(summary_parts) if summary_parts else "なし"
        print(f"作業プリセット読み込み完了 ({summary}): {file_path}")
        self.save_settings()



    # ========== Migration Utilities ==========

    def migrate_uuid_to_numeric_ids(self):
        """すべてのUUID形式のIDを数字形式に変換"""
        converted_count = 0
        for project in self.projects:
            for model in project.get('models', []):
                for work in model.get('works', []):
                    phrase_presets = work.get('phrase_presets', [])
                    used_ids = set()

                    # まず既に数字形式のIDを収集
                    for preset in phrase_presets:
                        unique_id = preset.get('unique_id', '')
                        if unique_id and unique_id.isdigit():
                            used_ids.add(int(unique_id))

                    # UUID形式のIDを数字形式に変換
                    next_id = 1
                    for preset in phrase_presets:
                        unique_id = preset.get('unique_id', '')
                        if not unique_id or not unique_id.isdigit():
                            # 次の利用可能なIDを見つける
                            while next_id in used_ids:
                                next_id += 1
                            preset['unique_id'] = str(next_id)
                            used_ids.add(next_id)
                            converted_count += 1
                            next_id += 1

        if converted_count > 0:
            print(f"Multi Filtering Outliner: {converted_count}個のUUID形式のIDを数字形式に変換しました")
            # 変換後の設定を保存
            self.save_settings()

    def ensure_phrase_preset_fields(self):
        """すべてのフレーズプリセットに必要なフィールドが存在することを確認"""
        updated_count = 0
        for project in self.projects:
            for model in project.get('models', []):
                for work in model.get('works', []):
                    for phrase_preset in work.get('phrase_presets', []):
                        # unique_id フィールドが存在しない、または空の場合は生成
                        if not phrase_preset.get('unique_id'):
                            phrase_preset['unique_id'] = self.get_globally_unique_id()
                            updated_count += 1

                        # dialog_open フィールドが存在しない場合はFalseを設定
                        if 'dialog_open' not in phrase_preset:
                            phrase_preset['dialog_open'] = False
                            updated_count += 1

                        # common_dialog_open フィールドが存在しない場合はFalseを設定
                        if 'common_dialog_open' not in phrase_preset:
                            phrase_preset['common_dialog_open'] = False
                            updated_count += 1

        if updated_count > 0:
            print(f"Multi Filtering Outliner: {updated_count}個のフィールドにデフォルト値を設定しました")
            # 更新後の設定を保存
            self.save_settings()

    def fix_duplicate_unique_ids(self):
        """重複したunique_idを検出して修正"""
        seen_ids = {}  # {unique_id: (project_idx, model_idx, work_idx, phrase_idx)}
        duplicates = []

        # すべてのフレーズプリセットをスキャンして重複を検出
        for project_idx, project in enumerate(self.projects):
            for model_idx, model in enumerate(project.get('models', [])):
                for work_idx, work in enumerate(model.get('works', [])):
                    for phrase_idx, phrase_preset in enumerate(work.get('phrase_presets', [])):
                        unique_id = phrase_preset.get('unique_id')
                        if unique_id:
                            if unique_id in seen_ids:
                                # 重複を検出
                                duplicates.append((project_idx, model_idx, work_idx, phrase_idx, phrase_preset))
                            else:
                                seen_ids[unique_id] = (project_idx, model_idx, work_idx, phrase_idx)

        # 重複したIDに新しいグローバルにユニークなIDを割り当て
        fixed_count = 0
        for project_idx, model_idx, work_idx, phrase_idx, phrase_preset in duplicates:
            old_id = phrase_preset['unique_id']
            new_id = self.get_globally_unique_id()
            phrase_preset['unique_id'] = new_id
            seen_ids[new_id] = (project_idx, model_idx, work_idx, phrase_idx)

            # ダイアログの状態をリセット（重複していたため、どれが正しいかわからない）
            phrase_preset['dialog_open'] = False
            phrase_preset['common_dialog_open'] = False

            fixed_count += 1
            print(f"Multi Filtering Outliner: 重複したID '{old_id}' を '{new_id}' に変更しました (フレーズプリセット '{phrase_preset.get('name')}')")

        if fixed_count > 0:
            print(f"Multi Filtering Outliner: {fixed_count}個の重複IDを修正しました")
            # 修正後の設定を保存
            self.save_settings()

    def migrate_from_old_format(self, settings):
        """旧形式の設定を階層構造に変換"""
        old_lists = settings.get('lists', [])

        if not old_lists:
            self.create_default_hierarchy()
            return

        # 旧形式のリストをすべて1つのプロジェクト・モデルに統合
        migrated_works = []
        for old_list in old_lists:
            # phrase_presetsがない旧形式の場合は変換
            if 'phrase_presets' not in old_list:
                work = {
                    'name': old_list.get('name', 'リスト'),
                    'common_filters': [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}],
                    'phrase_presets': [
                        {
                            'name': 'フレーズ1',
                            'phrase_data': old_list.get('phrase_data', [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}]),
                            'match_mode': old_list.get('match_mode', 'any'),
                            'dag_only': old_list.get('dag_only', False),
                            'use_common_filter': True,
                            # 旧形式のdialog_openフラグをフレーズプリセットに移行（マイグレーション時はFalseにする）
                            'dialog_open': False,
                            'dialog_geometry': old_list.get('dialog_geometry', {})
                        }
                    ]
                }
            else:
                # すでにphrase_presetsがある場合はcommon_filtersを追加
                work = old_list.copy()  # コピーして元データを変更しない
                if 'common_filters' not in work:
                    work['common_filters'] = [{'text': '', 'enabled': True, 'exclude': False, 'exact_token': False}]

                # 各フレーズプリセットにuse_common_filterを追加（存在しない場合）
                for phrase_preset in work.get('phrase_presets', []):
                    if 'use_common_filter' not in phrase_preset:
                        phrase_preset['use_common_filter'] = True
                    # マイグレーション時はdialog_openをFalseにする（古いダイアログを復元しない）
                    if 'dialog_open' in phrase_preset:
                        phrase_preset['dialog_open'] = False

                # 作業プリセットレベルのdialog_openとdialog_geometryを削除（新しい構造では不要）
                if 'dialog_open' in work:
                    del work['dialog_open']
                if 'dialog_geometry' in work:
                    del work['dialog_geometry']

            migrated_works.append(work)

        # 新しい階層構造を作成
        migrated_project = {
            'name': 'プロジェクト1',
            'models': [
                {
                    'name': 'モデル1',
                    'works': migrated_works
                }
            ]
        }

        self.projects = [migrated_project]
        self.project_combo.addItem(migrated_project['name'])
        self.project_combo.setCurrentIndex(0)
        self.on_project_changed(0)

        # 前回の選択状態を復元
        old_current_index = settings.get('current_index', 0)
        if 0 <= old_current_index < len(migrated_works):
            self.switch_to_work(old_current_index)

        print(f"旧形式から{len(migrated_works)}個の作業プリセットを移行しました")

