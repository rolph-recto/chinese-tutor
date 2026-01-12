# SQLite Migration Plan

Migrate knowledge points and student state from JSON files to SQLite.

## Configuration
- **Database location**: `data/tutor.db`
- **Migration strategy**: Manual script (no auto-migration)

---

## SQLite Schema

### knowledge_points
```sql
CREATE TABLE knowledge_points (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('vocabulary', 'grammar')),
    chinese TEXT NOT NULL,
    pinyin TEXT NOT NULL,
    english TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]'  -- JSON array as TEXT
);
```

### student_mastery
```sql
CREATE TABLE student_mastery (
    knowledge_point_id TEXT PRIMARY KEY,
    stability REAL,
    difficulty REAL,
    due TEXT,           -- ISO 8601 datetime
    last_review TEXT,   -- ISO 8601 datetime
    state INTEGER NOT NULL DEFAULT 1,
    step INTEGER,
    FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id)
);
```

### minimal_pairs
```sql
CREATE TABLE minimal_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id TEXT NOT NULL,
    distractor_chinese TEXT NOT NULL,
    distractor_pinyin TEXT NOT NULL,
    distractor_english TEXT NOT NULL,
    reason TEXT,
    FOREIGN KEY (target_id) REFERENCES knowledge_points(id)
);
```

### cloze_templates
```sql
CREATE TABLE cloze_templates (
    id TEXT PRIMARY KEY,
    chinese TEXT NOT NULL,
    english TEXT NOT NULL,
    target_vocab_id TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (target_vocab_id) REFERENCES knowledge_points(id)
);
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `storage/__init__.py` | Export repository classes and factory functions |
| `storage/base.py` | Abstract repository interfaces |
| `storage/sqlite.py` | SQLite repository implementations |
| `storage/connection.py` | Database connection and schema management |
| `scripts/migrate_to_sqlite.py` | Migration script (JSON to SQLite) |
| `tests/test_storage.py` | Repository unit tests |

## Files to Modify

| File | Changes |
|------|---------|
| `main.py` | Replace `load_knowledge_points()`, `load_student_state()`, `save_student_state()` with repository calls |
| `exercises/minimal_pair.py` | Replace `_load_minimal_pairs()` with repository |
| `exercises/cloze_deletion.py` | Replace `_load_templates()` with repository |
| `tests/conftest.py` | Add test database fixtures |
| `tests/test_integration_interactive.py` | Update mocking to use DB_PATH instead of STATE_FILE |

---

## Implementation Steps

### Phase 1: Storage Layer
1. Create `storage/` module structure
2. Implement `storage/connection.py` with schema initialization
3. Implement `storage/base.py` with abstract interfaces:
   - `KnowledgePointRepository`
   - `StudentStateRepository`
   - `MinimalPairsRepository`
   - `ClozeTemplatesRepository`
4. Implement `storage/sqlite.py` with SQLite implementations

### Phase 2: Migration Script
5. Create `scripts/migrate_to_sqlite.py`:
   - `--force` flag to overwrite existing DB
   - Migrate vocabulary.json, grammar.json
   - Migrate minimal_pairs.json, cloze_templates.json
   - Migrate student_state.json (if exists)

### Phase 3: Application Updates
6. Update `main.py`:
   - Add `DB_PATH = Path(__file__).parent / "data" / "tutor.db"`
   - Update `load_knowledge_points()` to use repository
   - Update `load_student_state()` to use repository
   - Update `save_student_state()` to use repository
7. Update `exercises/minimal_pair.py` to use `MinimalPairsRepository`
8. Update `exercises/cloze_deletion.py` to use `ClozeTemplatesRepository`

### Phase 4: Test Updates
9. Add fixtures to `tests/conftest.py`:
   - `test_db_path` - temporary database path
   - `populated_test_db` - database with sample data
10. Create `tests/test_storage.py` for repository tests
11. Update `tests/test_integration_interactive.py`:
    - Patch `main.DB_PATH` instead of `main.STATE_FILE`

### Phase 5: Verification
12. Run tests: `uv run pytest -v`
13. Run linter: `uvx ruff check --fix`
14. Run formatter: `uvx ruff format`

---

## Key Design Decisions

1. **Tags as JSON column**: Store as JSON string rather than junction table (simpler, no tag queries needed)
2. **Flatten FSRSState**: Store FSRS fields directly in student_mastery (enables due date indexing)
3. **No new dependencies**: Use built-in `sqlite3` module
4. **Repository pattern**: Abstract interface allows future storage backends
5. **Keep function signatures**: `load_knowledge_points()` etc. remain unchanged to minimize calling code changes
