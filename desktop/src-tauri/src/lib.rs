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

const SYSTEM_PROMPT_MIMI_LEMMA: &str = r#"
あなたは高度な概念抽出エンジンです。ユーザーの読書メモから、その根底にある抽象的な「概念（Concept）」「テーマ（Theme）」「哲学（Philosophy）」を3〜5個抽出してください。
一般的なジャンル名（例: 小説、ビジネス書）は排除し、より深くメタ的なキーワード（例: 時間の非線形性、自己組織化、実存主義）を生成してください。
出力は以下の厳密なJSON形式のみとし、他のテキストは一切含めないでください。
{ "tags": ["概念1", "概念2", "概念3"] }
"#;

fn clean_extracted_tags(tags: Vec<String>) -> Vec<String> {
    let placeholders = ["概念a", "概念b", "概念c", "概念1", "概念2", "概念3", "a", "b", "c", "tag1", "tag2", "tag3"];
    tags.into_iter()
        .map(|t| t.trim().to_string())
        .filter(|t| !t.is_empty() && !placeholders.contains(&t.to_lowercase().as_str()))
        .collect()
}

fn parse_llm_json_tags(raw: &str) -> Vec<String> {
    if raw.is_empty() {
        return Vec::new();
    }
    
    // 1. Try to extract markdown json code blocks ```json ... ``` (checking the last codeblock first)
    if let Some(start) = raw.rfind("```") {
        if let Some(first_start) = raw[..start].rfind("```") {
            let inner = &raw[first_start + 3..start];
            let inner = inner.strip_prefix("json").unwrap_or(inner).trim();
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(inner) {
                if let Some(tags_arr) = val.get("tags").and_then(|t| t.as_array()) {
                    let tags: Vec<String> = tags_arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect();
                    let cleaned = clean_extracted_tags(tags);
                    if !cleaned.is_empty() {
                        return cleaned;
                    }
                }
                if let Some(tags_arr) = val.as_array() {
                    let tags: Vec<String> = tags_arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect();
                    let cleaned = clean_extracted_tags(tags);
                    if !cleaned.is_empty() {
                        return cleaned;
                    }
                }
            }
        }
    }

    // 2. Direct JSON parse
    if let Ok(val) = serde_json::from_str::<serde_json::Value>(raw.trim()) {
        if let Some(tags_arr) = val.get("tags").and_then(|t| t.as_array()) {
            let tags: Vec<String> = tags_arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect();
            let cleaned = clean_extracted_tags(tags);
            if !cleaned.is_empty() {
                return cleaned;
            }
        }
        if let Some(tags_arr) = val.as_array() {
            let tags: Vec<String> = tags_arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect();
            let cleaned = clean_extracted_tags(tags);
            if !cleaned.is_empty() {
                return cleaned;
            }
        }
    }

    // 3. Find outermost { ... }
    if let Some(start) = raw.find('{') {
        if let Some(end) = raw.rfind('}') {
            if end > start {
                let slice = &raw[start..=end];
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(slice) {
                    if let Some(tags_arr) = val.get("tags").and_then(|t| t.as_array()) {
                        let tags: Vec<String> = tags_arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect();
                        let cleaned = clean_extracted_tags(tags);
                        if !cleaned.is_empty() {
                            return cleaned;
                        }
                    }
                }
            }
        }
    }

    Vec::new()
}

#[derive(Serialize)]
struct ExtractConceptsRequestPayload<'a> {
    note: &'a str,
}

#[derive(Deserialize)]
struct ExtractConceptsResponsePayload {
    tags: Vec<String>,
}

#[tauri::command]
async fn extract_concepts_api(
    note: String,
    api_url: Option<String>,
) -> Result<Vec<String>, String> {
    if note.trim().is_empty() {
        return Ok(Vec::new());
    }

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(180))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    // 1. Direct local LM Studio attempt (http://127.0.0.1:1234)
    let local_lm_models_url = "http://127.0.0.1:1234/v1/models";
    if let Ok(models_res) = client.get(local_lm_models_url).timeout(std::time::Duration::from_secs(3)).send().await {
        if models_res.status().is_success() {
            if let Ok(models_json) = models_res.json::<serde_json::Value>().await {
                let mut selected_model = None;
                if let Some(data) = models_json.get("data").and_then(|d| d.as_array()) {
                    for m in data {
                        if let Some(id) = m.get("id").and_then(|i| i.as_str()) {
                            if !id.to_lowercase().contains("embed") {
                                selected_model = Some(id.to_string());
                                break;
                            }
                        }
                    }
                    if selected_model.is_none() && !data.is_empty() {
                        selected_model = data[0].get("id").and_then(|i| i.as_str()).map(|s| s.to_string());
                    }
                }

                let mut payload_map = serde_json::Map::new();
                if let Some(model_id) = selected_model {
                    payload_map.insert("model".to_string(), serde_json::Value::String(model_id));
                }
                payload_map.insert("messages".to_string(), serde_json::json!([
                    {"role": "system", "content": SYSTEM_PROMPT_MIMI_LEMMA.trim()},
                    {"role": "user", "content": note.trim()}
                ]));
                payload_map.insert("temperature".to_string(), serde_json::json!(0.1));
                payload_map.insert("max_tokens".to_string(), serde_json::json!(1200));

                let completions_url = "http://127.0.0.1:1234/v1/chat/completions";
                if let Ok(chat_res) = client.post(completions_url).json(&payload_map).send().await {
                    if chat_res.status().is_success() {
                        if let Ok(chat_json) = chat_res.json::<serde_json::Value>().await {
                            if let Some(choices) = chat_json.get("choices").and_then(|c| c.as_array()) {
                                if let Some(choice) = choices.first() {
                                    let msg = choice.get("message");
                                    let content = msg.and_then(|m| m.get("content")).and_then(|c| c.as_str()).unwrap_or("");
                                    let reasoning = msg.and_then(|m| m.get("reasoning_content")).and_then(|c| c.as_str()).unwrap_or("");

                                    let mut tags = parse_llm_json_tags(content);
                                    if tags.is_empty() && !reasoning.is_empty() {
                                        tags = parse_llm_json_tags(reasoning);
                                    }
                                    if !tags.is_empty() {
                                        return Ok(tags);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // 2. Fallback to Lemma API endpoint
    let base_url = api_url.unwrap_or_else(|| "http://192.168.0.130:8000".to_string());
    let endpoint = format!("{}/api/extract_concepts", base_url.trim_end_matches('/'));

    let res = client
        .post(&endpoint)
        .json(&ExtractConceptsRequestPayload { note: &note })
        .send()
        .await
        .map_err(|e| format!("Connection to Lemma API / LM Studio failed ({}): {}", endpoint, e))?;

    if !res.status().is_success() {
        let status = res.status();
        let body = res.text().await.unwrap_or_default();
        return Err(format!("Lemma API error (HTTP {}): {}", status, body));
    }

    let resp = res
        .json::<ExtractConceptsResponsePayload>()
        .await
        .map_err(|e| format!("Failed to parse Lemma API JSON response: {}", e))?;

    Ok(resp.tags)
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
            extract_centroid_api,
            extract_concepts_api
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
