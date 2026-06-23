use std::path::PathBuf;
use tauri::AppHandle;

#[tauri::command]
pub async fn export_database(app: AppHandle, dest_path: String) -> Result<String, String> {
    let src = db_path(&app)?;

    if !src.exists() {
        return Err("Database file not found".to_string());
    }

    let dest = PathBuf::from(&dest_path);
    if let Some(parent) = dest.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }

    std::fs::copy(&src, &dest).map_err(|e| format!("copy failed: {e}"))?;

    Ok(format!("exported:{}", dest.display()))
}

#[tauri::command]
pub async fn import_database(app: AppHandle, src_path: String) -> Result<String, String> {
    let src = PathBuf::from(&src_path);
    if !src.exists() {
        return Err("Source file not found".to_string());
    }

    let dest = db_path(&app)?;
    if let Some(parent) = dest.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }

    // Backup current db before overwriting.
    if dest.exists() {
        let backup = dest.with_extension("db.bak");
        std::fs::copy(&dest, backup).map_err(|e| format!("backup failed: {e}"))?;
    }

    std::fs::copy(&src, &dest).map_err(|e| format!("import failed: {e}"))?;

    Ok("imported".to_string())
}

#[tauri::command]
pub async fn database_info(app: AppHandle) -> Result<serde_json::Value, String> {
    let path = db_path(&app)?;

    let (exists, size_bytes) = if path.exists() {
        let meta = std::fs::metadata(&path).map_err(|e| e.to_string())?;
        (true, meta.len())
    } else {
        (false, 0u64)
    };

    Ok(serde_json::json!({
        "path": path.display().to_string(),
        "exists": exists,
        "size_bytes": size_bytes,
        "size_mb": (size_bytes as f64) / 1_048_576.0,
    }))
}

fn db_path(app: &AppHandle) -> Result<PathBuf, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|e| e.to_string())?;
    Ok(data_dir.join("apex.db"))
}
