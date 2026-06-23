use std::sync::Mutex;
use tauri::{AppHandle, State};

pub struct BackendState {
    pub pid: Mutex<Option<u32>>,
}

impl Default for BackendState {
    fn default() -> Self {
        Self {
            pid: Mutex::new(None),
        }
    }
}

#[tauri::command]
pub async fn start_backend(
    app: AppHandle,
    state: State<'_, BackendState>,
) -> Result<String, String> {
    let mut pid_guard = state.pid.lock().map_err(|e| e.to_string())?;

    if pid_guard.is_some() {
        return Ok("already_running".to_string());
    }

    // Resolve the backend directory relative to the app resource dir.
    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|e| e.to_string())?;
    let backend_dir = resource_dir.join("backend");

    // Prefer a virtualenv if bundled alongside the binary.
    let python = backend_dir
        .join(".venv")
        .join("bin")
        .join("python")
        .to_string_lossy()
        .to_string();

    let child = std::process::Command::new(&python)
        .args(["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8083"])
        .current_dir(&backend_dir)
        .env("DATABASE_URL", data_dir_db(&app)?)
        .spawn()
        .map_err(|e| format!("failed to start backend: {e}"))?;

    *pid_guard = Some(child.id());
    Ok(format!("started:{}", child.id()))
}

#[tauri::command]
pub async fn stop_backend(state: State<'_, BackendState>) -> Result<String, String> {
    let mut pid_guard = state.pid.lock().map_err(|e| e.to_string())?;

    if let Some(pid) = pid_guard.take() {
        #[cfg(unix)]
        unsafe {
            libc::kill(pid as i32, libc::SIGTERM);
        }
        #[cfg(windows)]
        {
            let _ = std::process::Command::new("taskkill")
                .args(["/PID", &pid.to_string(), "/F"])
                .output();
        }
        return Ok(format!("stopped:{pid}"));
    }

    Ok("not_running".to_string())
}

#[tauri::command]
pub async fn backend_status(state: State<'_, BackendState>) -> Result<String, String> {
    let pid_guard = state.pid.lock().map_err(|e| e.to_string())?;
    match *pid_guard {
        Some(pid) => Ok(format!("running:{pid}")),
        None => Ok("stopped".to_string()),
    }
}

fn data_dir_db(app: &AppHandle) -> Result<String, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&data_dir).map_err(|e| e.to_string())?;
    let db_path = data_dir.join("apex.db");
    Ok(format!("sqlite+aiosqlite:///{}", db_path.display()))
}
