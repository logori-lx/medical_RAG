# File: server/main.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Optional, Dict

app = FastAPI(title="Git-Guard Cloud Server")

# --- 数据模型 ---
class CommitLog(BaseModel):
    developer_id: str
    repo_name: str
    commit_msg: str
    risk_level: str
    ai_summary: str

# [新增] 项目配置模型
class ProjectConfig(BaseModel):
    template_format: str  # 例如: "[Type][Scope] Description"
    custom_rules: str     # 例如: "Type must be one of: feat, fix, docs."

# --- 内存存储 (生产环境请换成数据库) ---
# 默认配置
GLOBAL_CONFIG = {
    "template_format": "<type>(<scope>): <subject>",
    "custom_rules": "Follow Angular Conventional Commits. Use lowercase."
}

# --- API 接口 ---

@app.get("/api/v1/scripts/{script_name}")
def get_script(script_name: str):
    """分发脚本接口 (保持不变)"""
    valid_scripts = {
        "analyzer": "analyzer_template.py",
        "indexer": "indexer_template.py"
    }
    if script_name not in valid_scripts:
        raise HTTPException(status_code=404, detail="Script not found")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, valid_scripts[script_name])
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail=f"Server file missing: {valid_scripts[script_name]}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return {"code": f.read()}

@app.post("/api/v1/track")
def track_commit(log: CommitLog):
    """日志追踪接口 (保持不变)"""
    print(f"📡 [TRACKING] {log.developer_id}: {log.commit_msg}")
    return {"status": "recorded"}

# --- [新增] 配置管理接口 ---

@app.post("/api/v1/config")
def update_config(config: ProjectConfig):
    """
    管理员接口：更新提交规范模板
    前端可以通过这个接口把 [Backend][Sprint2] 这种格式发过来
    """
    global GLOBAL_CONFIG
    GLOBAL_CONFIG["template_format"] = config.template_format
    GLOBAL_CONFIG["custom_rules"] = config.custom_rules
    print(f"⚙️  Config Updated: {GLOBAL_CONFIG}")
    return {"status": "updated", "config": GLOBAL_CONFIG}

@app.get("/api/v1/config")
def get_config():
    """
    Analyzer 接口：获取当前规范
    """
    return GLOBAL_CONFIG

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)