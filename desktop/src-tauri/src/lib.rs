mod db;

use db::{
    batch_insert_logs, delete_existing_log, get_all_logs, get_resonance_logs, insert_log,
    update_existing_log, DbState, NewReadingLog, ReadingLog, UpdateReadingLogPayload,
};
use serde::{Deserialize, Serialize};
use tauri::{Manager, State};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CentroidResponseItem {
    pub id: Option<String>,
    pub item_id: Option<String>,
    pub title: String,
    pub author: Option<String>,
    pub publisher: Option<String>,
    pub source: Option<String>,
    pub isbn: Option<String>,
    pub year: Option<i32>,
    pub origin: Option<f64>,
    pub style: Option<f64>,
    pub renown: Option<f64>,
    pub distance: Option<f64>,
    pub status: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CentroidRequestItem {
    pub title: String,
    pub date: Option<String>,
}

#[derive(Serialize)]
struct CentroidRequestPayload<'a> {
    items: &'a [CentroidRequestItem],
}

#[tauri::command]
fn get_logs(state: State<'_, DbState>) -> Result<Vec<ReadingLog>, String> {
    let conn = state.conn.lock().map_err(|e| e.to_string())?;
    get_all_logs(&conn).map_err(|e| e.to_string())
}

#[tauri::command]
fn add_log(state: State<'_, DbState>, log: NewReadingLog) -> Result<ReadingLog, String> {
    let conn = state.conn.lock().map_err(|e| e.to_string())?;
    insert_log(&conn, log).map_err(|e| e.to_string())
}

#[tauri::command]
fn update_log(
    state: State<'_, DbState>,
    payload: UpdateReadingLogPayload,
) -> Result<ReadingLog, String> {
    let conn = state.conn.lock().map_err(|e| e.to_string())?;
    update_existing_log(&conn, payload).map_err(|e| e.to_string())
}

#[tauri::command]
fn delete_log(state: State<'_, DbState>, id: String) -> Result<(), String> {
    let conn = state.conn.lock().map_err(|e| e.to_string())?;
    delete_existing_log(&conn, &id).map_err(|e| e.to_string())
}

#[tauri::command]
fn get_resonance_items(state: State<'_, DbState>) -> Result<Vec<ReadingLog>, String> {
    let conn = state.conn.lock().map_err(|e| e.to_string())?;
    get_resonance_logs(&conn).map_err(|e| e.to_string())
}

#[tauri::command]
fn batch_add_logs(state: State<'_, DbState>, logs: Vec<NewReadingLog>) -> Result<usize, String> {
    let mut conn = state.conn.lock().map_err(|e| e.to_string())?;
    batch_insert_logs(&mut conn, logs).map_err(|e| e.to_string())
}

#[tauri::command]
async fn extract_centroid_api(
    items: Vec<CentroidRequestItem>,
    api_url: Option<String>,
) -> Result<Vec<CentroidResponseItem>, String> {
    let base_url = api_url.unwrap_or_else(|| "http://192.168.0.130:8000".to_string());
    let endpoint = format!("{}/api/extract_centroid", base_url.trim_end_matches('/'));

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(15))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let res = client
        .post(&endpoint)
        .json(&CentroidRequestPayload { items: &items })
        .send()
        .await
        .map_err(|e| format!("Connection to Lemma API failed ({}): {}", endpoint, e))?;

    if !res.status().is_success() {
        let status = res.status();
        let body = res.text().await.unwrap_or_default();
        return Err(format!("Lemma API error (HTTP {}): {}", status, body));
    }

    let resp_items = res
        .json::<Vec<CentroidResponseItem>>()
        .await
        .map_err(|e| format!("Failed to parse Lemma API JSON response: {}", e))?;

    Ok(resp_items)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .setup(|app| {
            let app_dir = app
                .path()
                .app_config_dir()
                .unwrap_or_else(|_| std::path::PathBuf::from("."));
            let db_path = app_dir.join("lemma.db");
            let db_state = DbState::new(db_path).expect("Failed to initialize SQLite database");
            app.manage(db_state);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_logs,
            add_log,
            update_log,
            delete_log,
            get_resonance_items,
            batch_add_logs,
            extract_centroid_api
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
