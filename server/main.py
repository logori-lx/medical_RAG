# File: server/main.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Optional

app = FastAPI(title="Git-Guard Cloud Server (Distribution Only)")

# --- 数据模型 ---
class CommitLog(BaseModel):
    developer_id: str
    repo_name: str
    commit_msg: str
    risk_level: str
    ai_summary: str

# --- API 接口 ---

@app.get("/api/v1/scripts/{script_name}")
def get_script(script_name: str):
    """
    通用脚本分发接口。
    客户端可以通过这个接口下载 analyzer 或 indexer。
    """
    # 允许下载的文件白名单
    valid_scripts = {
        "analyzer": "analyzer_template.py",
        "indexer": "indexer_template.py"
    }
    
    if script_name not in valid_scripts:
        raise HTTPException(status_code=404, detail="Script not found")
    
    # 获取文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, valid_scripts[script_name])
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail=f"Server file missing: {valid_scripts[script_name]}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return {"code": f.read()}

@app.post("/api/v1/track")
def track_commit(log: CommitLog):
    """只负责接收日志，不再触发后台任务"""
    print(f"📡 [TRACKING] {log.repo_name} | {log.developer_id}: {log.commit_msg}")
    return {"status": "recorded"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)