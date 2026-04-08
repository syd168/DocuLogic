from fastapi import WebSocket
from typing import Dict, List
import json


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        self.active_connections[job_id] = websocket
    
    def disconnect(self, job_id: str):
        if job_id in self.active_connections:
            del self.active_connections[job_id]
    
    async def send_progress(self, job_id: str, message: str, progress: int):
        if job_id in self.active_connections:
            try:
                await self.active_connections[job_id].send_text(
                    json.dumps({
                        "type": "progress",
                        "message": message,
                        "progress": progress,
                        "job_id": job_id
                    })
                )
            except Exception as e:
                print(f"Error sending progress to {job_id}: {e}")
                self.disconnect(job_id)
    
    async def send_error(self, job_id: str, error_message: str):
        if job_id in self.active_connections:
            try:
                await self.active_connections[job_id].send_text(
                    json.dumps({
                        "type": "error",
                        "message": error_message,
                        "job_id": job_id
                    })
                )
            except Exception as e:
                if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                    print(f"Error sending error to {job_id}: {e}")
                self.disconnect(job_id)
    
    async def send_completion(
        self,
        job_id: str,
        result_files: dict,
        *,
        partial: bool = False,
        user_stopped: bool = False,
    ):
        if job_id in self.active_connections:
            try:
                await self.active_connections[job_id].send_text(
                    json.dumps({
                        "type": "completion",
                        "result_files": result_files,
                        "job_id": job_id,
                        "partial": partial,
                        "user_stopped": user_stopped,
                    })
                )
            except Exception as e:
                if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                    print(f"Error sending completion to {job_id}: {e}")
                self.disconnect(job_id)


# 全局连接管理器实例
manager = ConnectionManager()