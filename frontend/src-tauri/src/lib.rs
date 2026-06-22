mod commands;

use commands::{
    BackendState,
    backend_status, start_backend, stop_backend,
    database_info, export_database, import_database,
};
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .manage(BackendState::default())
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            backend_status,
            export_database,
            import_database,
            database_info,
        ])
        .setup(|app| {
            // Auto-start the backend when the app launches.
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let state = app_handle.state::<BackendState>();
                if let Err(e) = start_backend(app_handle.clone(), state).await {
                    eprintln!("backend auto-start failed: {e}");
                }
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let app_handle = window.app_handle().clone();
                tauri::async_runtime::spawn(async move {
                    let state = app_handle.state::<BackendState>();
                    let _ = stop_backend(state).await;
                });
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running APEX AI");
}
