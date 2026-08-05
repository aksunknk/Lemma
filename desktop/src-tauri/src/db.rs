use chrono::{Local, Utc};
use rusqlite::{params, Connection, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::sync::Mutex;
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ReadingLog {
    pub id: String,
    pub isbn: Option<String>,
    pub title: String,
    pub author: Option<String>,
    pub publisher: Option<String>,
    pub status: String,
    pub resonance: i64,
    pub started_at: Option<String>,
    pub finished_at: Option<String>,
    pub notes: Option<String>,
    pub updated_at: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct NewReadingLog {
    pub id: Option<String>,
    pub isbn: Option<String>,
    pub title: String,
    pub author: Option<String>,
    pub publisher: Option<String>,
    pub status: Option<String>,
    pub resonance: Option<i64>,
    pub started_at: Option<String>,
    pub finished_at: Option<String>,
    pub notes: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct UpdateReadingLogPayload {
    pub id: String,
    pub title: Option<String>,
    pub author: Option<String>,
    pub publisher: Option<String>,
    pub isbn: Option<String>,
    pub status: Option<String>,
    pub resonance: Option<i64>,
    pub started_at: Option<String>,
    pub finished_at: Option<String>,
    pub notes: Option<String>,
}

pub struct DbState {
    pub conn: Mutex<Connection>,
}

impl DbState {
    pub fn new(db_path: PathBuf) -> Result<Self, rusqlite::Error> {
        if let Some(parent) = db_path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        let conn = Connection::open(db_path)?;
        init_schema(&conn)?;
        Ok(Self {
            conn: Mutex::new(conn),
        })
    }
}

pub fn init_schema(conn: &Connection) -> Result<(), rusqlite::Error> {
    conn.execute_batch(
        "
        CREATE TABLE IF NOT EXISTS reading_logs (
            id TEXT PRIMARY KEY,
            isbn TEXT,
            title TEXT NOT NULL,
            author TEXT,
            publisher TEXT,
            status TEXT NOT NULL DEFAULT 'unread',
            resonance INTEGER NOT NULL DEFAULT 0,
            started_at TEXT,
            finished_at TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_reading_logs_updated_at ON reading_logs(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_reading_logs_resonance ON reading_logs(resonance);
        ",
    )?;

    // Safe idempotent migrations for existing databases
    let _ = conn.execute("ALTER TABLE reading_logs ADD COLUMN started_at TEXT", []);
    let _ = conn.execute("ALTER TABLE reading_logs ADD COLUMN finished_at TEXT", []);
    let _ = conn.execute("ALTER TABLE reading_logs ADD COLUMN notes TEXT", []);

    Ok(())
}

pub fn get_all_logs(conn: &Connection) -> Result<Vec<ReadingLog>, rusqlite::Error> {
    let mut stmt = conn.prepare(
        "SELECT id, isbn, title, author, publisher, status, resonance, started_at, finished_at, notes, updated_at 
         FROM reading_logs 
         ORDER BY updated_at DESC",
    )?;

    let rows = stmt.query_map([], |row| {
        Ok(ReadingLog {
            id: row.get(0)?,
            isbn: row.get(1)?,
            title: row.get(2)?,
            author: row.get(3)?,
            publisher: row.get(4)?,
            status: row.get(5)?,
            resonance: row.get(6)?,
            started_at: row.get(7)?,
            finished_at: row.get(8)?,
            notes: row.get(9)?,
            updated_at: row.get(10)?,
        })
    })?;

    let mut logs = Vec::new();
    for log in rows {
        logs.push(log?);
    }
    Ok(logs)
}

pub fn insert_log(conn: &Connection, new_log: NewReadingLog) -> Result<ReadingLog, rusqlite::Error> {
    let id = new_log.id.unwrap_or_else(|| Uuid::new_v4().to_string());
    let updated_at = Utc::now().to_rfc3339();
    let status = new_log.status.unwrap_or_else(|| "unread".to_string());
    let resonance = new_log.resonance.unwrap_or(0);

    let today = Local::now().format("%Y-%m-%d").to_string();

    // Auto-timestamp logic on insertion if not explicitly provided
    let started_at = match (new_log.started_at, status.as_str()) {
        (Some(s), _) if !s.trim().is_empty() => Some(s),
        (None, "reading") => Some(today.clone()),
        _ => None,
    };

    let finished_at = match (new_log.finished_at, status.as_str()) {
        (Some(f), _) if !f.trim().is_empty() => Some(f),
        (None, "read") => Some(today),
        _ => None,
    };

    let notes = new_log.notes.filter(|n| !n.trim().is_empty());

    conn.execute(
        "INSERT INTO reading_logs (id, isbn, title, author, publisher, status, resonance, started_at, finished_at, notes, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
        params![
            &id,
            &new_log.isbn,
            &new_log.title,
            &new_log.author,
            &new_log.publisher,
            &status,
            &resonance,
            &started_at,
            &finished_at,
            &notes,
            &updated_at
        ],
    )?;

    Ok(ReadingLog {
        id,
        isbn: new_log.isbn,
        title: new_log.title,
        author: new_log.author,
        publisher: new_log.publisher,
        status,
        resonance,
        started_at,
        finished_at,
        notes,
        updated_at,
    })
}

pub fn batch_insert_logs(conn: &mut Connection, logs: Vec<NewReadingLog>) -> Result<usize, rusqlite::Error> {
    let tx = conn.transaction()?;
    let mut count = 0;
    for log in logs {
        if log.title.trim().is_empty() {
            continue;
        }
        let id = log.id.unwrap_or_else(|| Uuid::new_v4().to_string());
        let updated_at = Utc::now().to_rfc3339();
        let status = log.status.unwrap_or_else(|| "unread".to_string());
        let resonance = log.resonance.unwrap_or(0);
        let notes = log.notes.filter(|n| !n.trim().is_empty());

        tx.execute(
            "INSERT OR REPLACE INTO reading_logs (id, isbn, title, author, publisher, status, resonance, started_at, finished_at, notes, updated_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
            params![
                &id,
                &log.isbn,
                &log.title,
                &log.author,
                &log.publisher,
                &status,
                &resonance,
                &log.started_at,
                &log.finished_at,
                &notes,
                &updated_at
            ],
        )?;
        count += 1;
    }
    tx.commit()?;
    Ok(count)
}

pub fn update_existing_log(
    conn: &Connection,
    payload: UpdateReadingLogPayload,
) -> Result<ReadingLog, rusqlite::Error> {
    // 1. Fetch current record
    let mut stmt = conn.prepare(
        "SELECT id, isbn, title, author, publisher, status, resonance, started_at, finished_at, notes, updated_at
         FROM reading_logs WHERE id = ?1",
    )?;

    let current = stmt.query_row(params![&payload.id], |row| {
        Ok(ReadingLog {
            id: row.get(0)?,
            isbn: row.get(1)?,
            title: row.get(2)?,
            author: row.get(3)?,
            publisher: row.get(4)?,
            status: row.get(5)?,
            resonance: row.get(6)?,
            started_at: row.get(7)?,
            finished_at: row.get(8)?,
            notes: row.get(9)?,
            updated_at: row.get(10)?,
        })
    })?;

    let new_title = payload.title.unwrap_or(current.title);
    let new_author = if payload.author.is_some() { payload.author } else { current.author };
    let new_publisher = if payload.publisher.is_some() { payload.publisher } else { current.publisher };
    let new_isbn = if payload.isbn.is_some() { payload.isbn } else { current.isbn };
    let new_status = payload.status.unwrap_or(current.status);
    let new_resonance = payload.resonance.unwrap_or(current.resonance);
    let new_notes = if payload.notes.is_some() {
        payload.notes.map(|n| if n.trim().is_empty() { String::new() } else { n }).filter(|n| !n.is_empty())
    } else {
        current.notes
    };

    let today = Local::now().format("%Y-%m-%d").to_string();

    // Auto-timestamp logic for started_at
    let mut new_started_at = match payload.started_at {
        Some(s) => if s.trim().is_empty() { None } else { Some(s) },
        None => current.started_at,
    };
    if new_status == "reading" && new_started_at.is_none() {
        new_started_at = Some(today.clone());
    }

    // Auto-timestamp logic for finished_at
    let mut new_finished_at = match payload.finished_at {
        Some(f) => if f.trim().is_empty() { None } else { Some(f) },
        None => current.finished_at,
    };
    if new_status == "read" && new_finished_at.is_none() {
        new_finished_at = Some(today);
    }

    let updated_at = Utc::now().to_rfc3339();

    conn.execute(
        "UPDATE reading_logs 
         SET title = ?1, author = ?2, publisher = ?3, isbn = ?4, status = ?5, resonance = ?6, started_at = ?7, finished_at = ?8, notes = ?9, updated_at = ?10
         WHERE id = ?11",
        params![
            &new_title,
            &new_author,
            &new_publisher,
            &new_isbn,
            &new_status,
            &new_resonance,
            &new_started_at,
            &new_finished_at,
            &new_notes,
            &updated_at,
            &payload.id
        ],
    )?;

    Ok(ReadingLog {
        id: payload.id,
        isbn: new_isbn,
        title: new_title,
        author: new_author,
        publisher: new_publisher,
        status: new_status,
        resonance: new_resonance,
        started_at: new_started_at,
        finished_at: new_finished_at,
        notes: new_notes,
        updated_at,
    })
}

pub fn delete_existing_log(conn: &Connection, id: &str) -> Result<(), rusqlite::Error> {
    conn.execute("DELETE FROM reading_logs WHERE id = ?1", params![id])?;
    Ok(())
}

pub fn get_resonance_logs(conn: &Connection) -> Result<Vec<ReadingLog>, rusqlite::Error> {
    let mut stmt = conn.prepare(
        "SELECT id, isbn, title, author, publisher, status, resonance, started_at, finished_at, notes, updated_at 
         FROM reading_logs 
         WHERE resonance = 1
         ORDER BY updated_at DESC",
    )?;

    let rows = stmt.query_map([], |row| {
        Ok(ReadingLog {
            id: row.get(0)?,
            isbn: row.get(1)?,
            title: row.get(2)?,
            author: row.get(3)?,
            publisher: row.get(4)?,
            status: row.get(5)?,
            resonance: row.get(6)?,
            started_at: row.get(7)?,
            finished_at: row.get(8)?,
            notes: row.get(9)?,
            updated_at: row.get(10)?,
        })
    })?;

    let mut logs = Vec::new();
    for log in rows {
        logs.push(log?);
    }
    Ok(logs)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sqlite_crud_and_auto_timestamps_and_notes() {
        let mut conn = Connection::open_in_memory().unwrap();
        init_schema(&conn).unwrap();

        // 1. Insert unread log with personal notes
        let log1 = insert_log(
            &conn,
            NewReadingLog {
                id: None,
                isbn: Some("9784101006017".into()),
                title: "人間失格".into(),
                author: Some("太宰治".into()),
                publisher: Some("新潮文庫".into()),
                status: Some("unread".into()),
                resonance: Some(0),
                started_at: None,
                finished_at: None,
                notes: Some("「恥の多い生涯を送って来ました。」冒頭のインパクトが凄まじい。".into()),
            },
        )
        .unwrap();

        assert_eq!(log1.status, "unread");
        assert!(log1.started_at.is_none());
        assert!(log1.finished_at.is_none());
        assert_eq!(
            log1.notes.as_deref(),
            Some("「恥の多い生涯を送って来ました。」冒頭のインパクトが凄まじい。")
        );

        // 2. Cycle to reading -> auto-sets started_at, retains notes
        let updated1 = update_existing_log(
            &conn,
            UpdateReadingLogPayload {
                id: log1.id.clone(),
                title: None,
                author: None,
                publisher: None,
                isbn: None,
                status: Some("reading".into()),
                resonance: None,
                started_at: None,
                finished_at: None,
                notes: None,
            },
        )
        .unwrap();

        assert_eq!(updated1.status, "reading");
        assert!(updated1.started_at.is_some());
        assert!(updated1.finished_at.is_none());
        assert_eq!(
            updated1.notes.as_deref(),
            Some("「恥の多い生涯を送って来ました。」冒頭のインパクトが凄まじい。")
        );

        // 3. Update notes
        let updated2 = update_existing_log(
            &conn,
            UpdateReadingLogPayload {
                id: log1.id.clone(),
                title: None,
                author: None,
                publisher: None,
                isbn: None,
                status: Some("read".into()),
                resonance: None,
                started_at: None,
                finished_at: None,
                notes: Some("読了。人間の弱さと救済についての深い思索。".into()),
            },
        )
        .unwrap();

        assert_eq!(updated2.status, "read");
        assert!(updated2.started_at.is_some());
        assert!(updated2.finished_at.is_some());
        assert_eq!(
            updated2.notes.as_deref(),
            Some("読了。人間の弱さと救済についての深い思索。")
        );

        // 4. Batch insert for CSV import with notes
        let batch = vec![
            NewReadingLog {
                id: Some("custom-id-1".into()),
                isbn: None,
                title: "こころ".into(),
                author: Some("夏目漱石".into()),
                publisher: Some("岩波文庫".into()),
                status: Some("reading".into()),
                resonance: Some(1),
                started_at: Some("2026-08-01".into()),
                finished_at: None,
                notes: Some("先生と遺書の手紙の心理描写。".into()),
            },
        ];
        let imported = batch_insert_logs(&mut conn, batch).unwrap();
        assert_eq!(imported, 1);

        let all = get_all_logs(&conn).unwrap();
        assert_eq!(all.len(), 2);

        // 5. Resonance items
        let res_items = get_resonance_logs(&conn).unwrap();
        assert_eq!(res_items.len(), 1);
        assert_eq!(res_items[0].title, "こころ");
        assert_eq!(res_items[0].notes.as_deref(), Some("先生と遺書の手紙の心理描写。"));
    }
}
