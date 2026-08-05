# Lemma Desktop: Personal Reading Notes & TheGrid Exploration System

## 実装概要 (Overview)
読書録としての「生の思考・共鳴理由（Personal Context）」を記録・蓄積するための **Notes（読書ノート）機能** と、書籍が多数になった際にも即座に目的の知にアクセスできる **TheGrid 高速探索システム（リアルタイム検索・ステータスタブ・カラムソート）** を実装しました。

---

## 主な改修点 (Key Implementations)

### 1. 個人のコンテキスト（読書ノート / メモ機能）
- **SQLite データベーススキーマ & マイグレーション**:
  - [db.rs](file:///c:/Users/aksak/lemma_project_core/desktop/src-tauri/src/db.rs): `reading_logs` テーブルに `notes TEXT` カラムを追加。既存DB起動時にも安全にカラム追加を行う自動マイグレーション処理を実装。
  - CRUD（`insert_log`, `update_existing_log`, `batch_insert_logs`, `get_all_logs`）および Rust ユニットテストを改修。
- **型定義 & CSV 同期**:
  - [types/index.ts](file:///c:/Users/aksak/lemma_project_core/desktop/src/types/index.ts): `ReadingLog`, `NewReadingLog`, `UpdateLogPayload` に `notes: string | null` を追加。
  - [csvSync.ts](file:///c:/Users/aksak/lemma_project_core/desktop/src/services/csvSync.ts): CSVのエクスポート/インポート時に `notes` カラムを完全同期（改行やカンマを含むエスケープ処理対応）。
- **編集モーダル（EditModal）**:
  - [EditModal.tsx](file:///c:/Users/aksak/lemma_project_core/desktop/src/components/EditModal.tsx): 複数行入力可能なサイバーパンク風 `<textarea>` を配置。
  - ラベル: `// PERSONAL CONTEXT / READING NOTES` （文字数カウンター `[ 120 CHARS ]` 付き）。
  - 共鳴した理由、心に残った一文、ページ番号などをシームレスに記録・保存可能。
- **グリッド表示**:
  - [TheGrid.tsx](file:///c:/Users/aksak/lemma_project_core/desktop/src/components/TheGrid.tsx): ノートが保存されている書籍には、タイトル横に `[NOTE]` バッジが表示され、ダブルクリックまたは `[EDIT]` で即座に展開。

---

### 2. スケール時の探索機能（TheGrid HUD & 高速フィルター）
- **リアルタイム・クイックフィルター（インクリメンタル検索）**:
  - `FILTER:// [ search title, author, notes... ]` 検索窓を設置。
  - タイトル・著者名・出版社・ISBN・**保存した読書ノート（Notes）** の全文をリアルタイムに検索して瞬時に絞り込み。`[✕]` ボタンでワンタップクリア。
- **ステータス切り替えタブ（HUD Filter Tabs）**:
  - `[ALL (N)]`
  - `[READING (N)]`
  - `[READ (N)]`
  - `[UNREAD (N)]`
  - `[ABANDONED (N)]`
  - `[● RESONATING (N)]`
  - 各状態の件数バッジ付きで、ワンクリックでビューを瞬時にスイッチ。
- **マルチカラム・ソート機能**:
  - カラムヘッダー（`RES`, `STATUS`, `TITLE`, `AUTHOR`, `PERIOD / PUBLISHER`, `ISBN`）をクリックすることで、昇順（`▲`）/ 降順（`▼`）/ デフォルト（更新日降順）をサイクリックに切り替え。
  - 日本語（五十音・漢字順）の適切なロケールソート（`localeCompare('ja')`）に対応。

---

## 検証結果 (Verification)
- `cargo test`: SQLite マイグレーション、CRUD、Notes 更新、CSV バッチ処理の単体テストすべて合格 (1 passed)
- `npm run build`: TypeScript / Vite コンパイルエラー 0 件でビルド完了
