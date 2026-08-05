import { invoke } from "@tauri-apps/api/core";
import { ReadingLog, NewReadingLog, UpdateLogPayload } from "../types";

export async function getLogs(): Promise<ReadingLog[]> {
  return await invoke<ReadingLog[]>("get_logs");
}

export async function addLog(log: NewReadingLog): Promise<ReadingLog> {
  return await invoke<ReadingLog>("add_log", { log });
}

export async function updateLog(payload: UpdateLogPayload): Promise<ReadingLog> {
  return await invoke<ReadingLog>("update_log", { payload });
}

export async function deleteLog(id: string): Promise<void> {
  await invoke<void>("delete_log", { id });
}

export async function getResonanceItems(): Promise<ReadingLog[]> {
  return await invoke<ReadingLog[]>("get_resonance_items");
}

export async function batchAddLogs(logs: NewReadingLog[]): Promise<number> {
  return await invoke<number>("batch_add_logs", { logs });
}
