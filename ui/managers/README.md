# Managers パッケージ

## 現状

このディレクトリは **将来的な拡張のために予約** されています。

現在、マネージャークラスは実装されていません。理由は以下の通りです：

## なぜマネージャークラスを実装しなかったか

### 1. 過度な分離のリスク

プロジェクト/モデル/作業/フレーズ管理のメソッドは、以下の理由で分離が困難です：

- **多数の属性への依存**: `self.projects`, `self.current_project_index`, `self.current_model_index` など、メインクラスの多数の属性に密接に依存
- **UI要素との密結合**: `self.project_combo`, `self.model_combo`, `self.buttons_layout` など、UI要素と密結合
- **相互依存**: メソッド間で複雑に相互依存しており、分離すると循環参照のリスク

### 2. 可読性の低下

これらのメソッドをMixinに分離すると：
- メソッドと使用するデータが離れる
- コードの流れが追いにくくなる
- デバッグが困難になる

### 3. 保守性の低下

現在の構造では：
- 関連するコードが近くにある
- 一つのファイルで全体像が把握できる
- 修正時に複数ファイルを行き来する必要がない

## 計画されていたマネージャークラス

ドキュメントで言及されていた、将来実装可能なマネージャークラス：

### ProjectManagerMixin (約400行削減見込み)
```python
# ui/managers/project_manager.py
class ProjectManagerMixin:
    """プロジェクト/モデル管理を担当するMixin"""

    def on_add_project(self): ...
    def on_remove_project(self): ...
    def on_duplicate_project(self): ...
    def on_rename_project(self): ...
    def on_add_model(self): ...
    def on_remove_model(self): ...
    def on_duplicate_model(self): ...
    def on_rename_model(self): ...
    def on_project_changed(self, index): ...
    def on_model_changed(self, index): ...
    def update_model_combo(self): ...
```

**問題点**:
- `self.projects`, `self.current_project_index` に依存
- `self.project_combo`, `self.model_combo` に依存
- UI更新とビジネスロジックが密結合

### WorkManagerMixin (約300行削減見込み)
```python
# ui/managers/work_manager.py
class WorkManagerMixin:
    """作業プリセット管理を担当するMixin"""

    def switch_to_work(self, index): ...
    def save_current_work_state(self): ...
    def load_work_to_ui(self, index): ...
    def on_add_list(self): ...
    def on_remove_current_list(self): ...
    def on_duplicate_work(self): ...
    def update_work_buttons(self): ...
    def clear_work_buttons(self): ...
```

**問題点**:
- `self.buttons_layout`, `self.current_work_index` に依存
- UIボタンの作成・更新と密結合

### PhraseManagerMixin (約300行削減見込み)
```python
# ui/managers/phrase_manager.py
class PhraseManagerMixin:
    """フレーズプリセット管理を担当するMixin"""

    def switch_to_phrase_preset(self, index): ...
    def save_current_phrase_preset_state(self): ...
    def load_phrase_preset_to_ui(self, index): ...
    def on_add_phrase_preset(self): ...
    def on_remove_phrase_preset(self): ...
    def on_duplicate_phrase_preset(self): ...
    def add_phrase_row(self, ...): ...
    def on_add_phrase(self): ...
    def on_remove_phrase(self, phrase_widget): ...
```

**問題点**:
- `self.phrase_container`, `self.phrase_preset_buttons_layout` に依存
- フレーズウィジェットの作成・管理と密結合

## 推奨される方針

### 現状を維持（推奨）

**理由**:
1. メインファイル4284行は管理可能なサイズ
2. 関連するコードが近くにあり、可読性が高い
3. 過度な分離は逆効果

### 将来の実装条件

以下の条件が揃った場合のみ、マネージャークラスの実装を検討：

1. **ユニットテストの完備**: 各メソッドにテストがある
2. **明確なインターフェース**: メソッドとデータの依存関係が明確
3. **リファクタリングの必要性**: 実際に保守が困難になった場合

## まとめ

**managersディレクトリは空のままで問題ありません。**

現在の構造（Mixinは3つのみ）が最適なバランスです：

- ✅ **GeometryManagerMixin**: ジオメトリ管理（横断的関心事）
- ✅ **SettingsManagerMixin**: 設定管理（横断的関心事）
- ✅ **DialogManagerMixin**: ダイアログ管理（横断的関心事）
- ❌ **ProjectManagerMixin**: 分離困難（UI要素と密結合）
- ❌ **WorkManagerMixin**: 分離困難（UI要素と密結合）
- ❌ **PhraseManagerMixin**: 分離困難（UI要素と密結合）

重要なのは **行数ではなく、保守性・可読性・テスト容易性** です。

## 関連ドキュメント

- [../../../REFACTORING_COMPLETE.md](../../../REFACTORING_COMPLETE.md) - リファクタリング完了報告
- [../../../REFACTORING_STATUS_REPORT.md](../../../REFACTORING_STATUS_REPORT.md) - 状況分析レポート
