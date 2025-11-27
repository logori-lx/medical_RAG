# File: server/main.py
import os
import json
import csv
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Optional, Dict

app = FastAPI(title="Git-Guard Cloud Server")

# ==========================================
# [配置] 允许跨域 (CORS) - 确保前端能访问
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# [配置] 文件路径
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 配置文件路径
CONFIG_FILE_PATH = os.path.join(BASE_DIR, "server_config.json")
# [新增] 日志存储路径 (CSV)
LOG_FILE_PATH = os.path.join(BASE_DIR, "commit_history.csv")

# ==========================================
# [默认值] 配置模板
# ==========================================
DEFAULT_CONFIG = {
    "template_format": "[<Module>][<Type>] <Description>",
    "custom_rules": """
    1. <Module> must be one of: [Backend], [Frontend], [Docs], [Config].
       - .py files -> [Backend]
       - .js/.html/.css -> [Frontend]
       - .md -> [Docs]
       - .json/.yaml -> [Config]
    2. <Type> must be one of: [Feat], [Fix], [Refactor].
    3. Description must be start with a lowercase letter.
    """
}

# ==========================================
# [模型] 数据结构
# ==========================================
class CommitLog(BaseModel):
    developer_id: str
    repo_name: str
    commit_msg: str
    risk_level: str
    ai_summary: str

class ProjectConfig(BaseModel):
    template_format: str
    custom_rules: str

# ==========================================
# [辅助函数] 持久化存储
# ==========================================

def load_config_from_disk() -> dict:
    """从磁盘加载配置"""
    if not os.path.exists(CONFIG_FILE_PATH):
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load config: {e}")
        return DEFAULT_CONFIG

def save_config_to_disk(config_data: dict):
    """保存配置到磁盘"""
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Config saved to {CONFIG_FILE_PATH}")
    except Exception as e:
        print(f"❌ Failed to save config: {e}")

def save_log_to_csv(log: CommitLog):
    file_exists = os.path.exists(LOG_FILE_PATH)
    
    try:
        # newline='' 是为了防止 Windows 下出现空行
        with open(LOG_FILE_PATH, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 如果文件不存在，先写入表头
            if not file_exists:
                writer.writerow(["Timestamp", "Developer", "Repo", "Risk", "Message", "AI Summary"])
            
            # 写入数据行
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([
                timestamp,
                log.developer_id,
                log.repo_name,
                log.risk_level,
                log.commit_msg,
                log.ai_summary
            ])
            print(f"✅ Log recorded to {LOG_FILE_PATH}")
    except Exception as e:
        print(f"❌ Failed to write log: {e}")

# ==========================================
# [API] 接口定义
# ==========================================

@app.get("/api/v1/scripts/{script_name}")
def get_script(script_name: str):
    """分发脚本接口"""
    valid_scripts = {
        "analyzer": "analyzer_template.py",
        "indexer": "indexer_template.py"
    }
    if script_name not in valid_scripts:
        raise HTTPException(status_code=404, detail="Script not found")
    
    file_path = os.path.join(BASE_DIR, valid_scripts[script_name])
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail=f"Server file missing: {valid_scripts[script_name]}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return {"code": f.read()}

@app.post("/api/v1/track")
def track_commit(log: CommitLog):
    """
    日志追踪接口 (已修改为持久化存储)
    """
    print(f"📡 [TRACKING] {log.developer_id}: {log.commit_msg}")
    
    # [核心修改] 调用存储函数
    save_log_to_csv(log)
    
    return {"status": "recorded"}

@app.post("/api/v1/config")
def update_config(config: ProjectConfig):
    """管理员接口：更新配置"""
    new_config = config.dict()
    save_config_to_disk(new_config)
    print(f"⚙️  Config Updated: {new_config}")
    return {"status": "updated", "config": new_config}

@app.get("/api/v1/config")
def get_config():
    """Analyzer 接口：获取配置"""
    return load_config_from_disk()

if __name__ == "__main__":
    print(f"🚀 Server Starting...")
    print(f"   - Config File: {CONFIG_FILE_PATH}")
    print(f"   - Log File:    {LOG_FILE_PATH}")
    # 启用 reload 方便调试
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=[BASE_DIR])