# File: server/main.py
import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Optional, Dict

app = FastAPI(title="Git-Guard Cloud Server")

# --- 配置文件路径 ---
# 获取当前脚本所在目录，确保文件生成在 server 文件夹内
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH = os.path.join(BASE_DIR, "server_config.json")

# --- 默认配置 (当文件不存在时使用) ---
# --- 默认配置 (更适合敏捷开发的严格版本) ---
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
# --- 数据模型 ---
class CommitLog(BaseModel):
    developer_id: str
    repo_name: str
    commit_msg: str
    risk_level: str
    ai_summary: str

class ProjectConfig(BaseModel):
    template_format: str
    custom_rules: str

# --- 辅助函数：持久化存储 ---

def load_config_from_disk() -> dict:
    """从磁盘加载配置，如果失败则返回默认值"""
    if not os.path.exists(CONFIG_FILE_PATH):
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load config file: {e}. Using defaults.")
        return DEFAULT_CONFIG

def save_config_to_disk(config_data: dict):
    """将配置写入磁盘"""
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Config saved to {CONFIG_FILE_PATH}")
    except Exception as e:
        print(f"❌ Failed to save config: {e}")

# --- API 接口 ---

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
    """日志追踪接口"""
    print(f"📡 [TRACKING] {log.developer_id}: {log.commit_msg}")
    return {"status": "recorded"}

# --- [修改后] 配置管理接口 ---

@app.post("/api/v1/config")
def update_config(config: ProjectConfig):
    """
    管理员接口：更新提交规范模板，并持久化到磁盘
    """
    # 转换为字典
    new_config = config.dict()
    
    # 写入文件
    save_config_to_disk(new_config)
    
    print(f"⚙️  Config Updated: {new_config}")
    return {"status": "updated", "config": new_config}

@app.get("/api/v1/config")
def get_config():
    """
    Analyzer 接口：总是从磁盘读取最新配置
    """
    current_config = load_config_from_disk()
    return current_config

if __name__ == "__main__":
    # 启动时打印一下当前配置
    print(f"🚀 Server Starting... Current Config: {load_config_from_disk()}")
    uvicorn.run(app, host="0.0.0.0", port=8000)