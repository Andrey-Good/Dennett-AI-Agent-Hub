#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // The actual app entrypoint lives in lib.rs (run()).
    dennet_app::run();
}
