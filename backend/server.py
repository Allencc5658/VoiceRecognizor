import logging
import asyncio
import json
from typing import Optional, List
from pathlib import Path, PurePosixPath
import mimetypes
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 修复相对导入问题
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from .config import WEB_CONFIG, BASE_DIR
    from .task_processor import task_manager
    from .file_manager import file_manager, upload_manager
except ImportError:
    # 如果相对导入失败，使用绝对导入
    from backend.config import WEB_CONFIG, BASE_DIR
    from backend.task_processor import task_manager
    from backend.file_manager import file_manager, upload_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="TTS语音评测系统",
    description="基于Paraformer的TTS合成质量评测系统",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=WEB_CONFIG.get("cors_origins", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception:
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        
        # 移除断开的连接
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# 静态文件服务
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

@app.get("/favicon.ico")
async def favicon():
    """favicon处理"""
    favicon_path = frontend_dir / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    else:
        # 返回一个简单的透明图标
        return Response(content=b"", media_type="image/x-icon")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """首页"""
    try:
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        else:
            return HTMLResponse("""
            <html>
                <head><title>TTS语音评测系统</title></head>
                <body>
                    <h1>TTS语音评测系统</h1>
                    <p>前端页面正在开发中...</p>
                    <p>API文档: <a href="/docs">/docs</a></p>
                </body>
            </html>
            """)
    except Exception as e:
        logger.error(f"Serve index failed: {str(e)}")
        return HTMLResponse(f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", status_code=500)

# API路由
@app.post("/api/upload-directory")
async def upload_directory(files: List[UploadFile] = File(...), task_name: Optional[str] = Form(None)):
    """
    上传文件夹进行评测
    """
    try:
        # 创建临时目录
        temp_dir = upload_manager.upload_dir / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_dir.mkdir(exist_ok=True)
        
        # 保存上传的文件
        uploaded_files = []
        for file in files:
            if file.filename:
                safe_name = PurePosixPath(file.filename.replace("\\", "/")).name
                file_path = temp_dir / safe_name
                counter = 1
                while file_path.exists():
                    file_path = temp_dir / f"{Path(safe_name).stem}_{counter}{Path(safe_name).suffix}"
                    counter += 1
                # 创建父目录
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
                
                uploaded_files.append(str(file_path))
        
        # 生成session_id（提前）
        session_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建进度回调函数 (启用WebSocket广播)
        async def progress_callback(progress):
            try:
                logger.info(f"Progress for {session_id}: {progress.progress_percentage}%")
                # 广播进度信息到所有WebSocket连接
                message = json.dumps({
                    "type": "progress",
                    "session_id": session_id,
                    "data": progress.to_dict()
                })
                await manager.broadcast(message)
            except Exception as e:
                logger.error(f"Progress callback failed: {str(e)}")
        
        # 开始评测任务
        actual_session_id = await task_manager.start_evaluation(
            directory_path=str(temp_dir),
            task_name=task_name,
            progress_callback=progress_callback
        )
        
        return JSONResponse({
            "success": True,
            "session_id": actual_session_id,
            "message": f"任务已开始，共上传 {len(uploaded_files)} 个文件"
        })
        
    except Exception as e:
        logger.error(f"Upload directory failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/start-evaluation")
async def start_evaluation(directory_path: str = Form(...), task_name: Optional[str] = Form(None)):
    """
    开始评测任务（使用本地目录）
    """
    try:
        # 生成session_id（提前）
        session_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建进度回调函数 (启用WebSocket广播)
        async def progress_callback(progress):
            try:
                logger.info(f"Progress for {session_id}: {progress.progress_percentage}%")
                # 广播进度信息到所有WebSocket连接
                message = json.dumps({
                    "type": "progress",
                    "session_id": session_id,
                    "data": progress.to_dict()
                })
                await manager.broadcast(message)
            except Exception as e:
                logger.error(f"Progress callback failed: {str(e)}")
        
        actual_session_id = await task_manager.start_evaluation(
            directory_path=directory_path,
            task_name=task_name,
            progress_callback=progress_callback
        )
        
        return JSONResponse({
            "success": True,
            "session_id": actual_session_id,
            "message": "评测任务已开始"
        })
        
    except Exception as e:
        logger.error(f"Start evaluation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/task-status/{session_id}")
async def get_task_status(session_id: str):
    """
    获取任务状态
    """
    try:
        status = task_manager.get_task_status(session_id)
        
        if status is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return JSONResponse({
            "success": True,
            "data": status
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task status failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/task-results/{session_id}")
async def get_task_results(session_id: str):
    """
    获取任务结果
    """
    try:
        results = task_manager.get_task_results(session_id)
        
        if results is None:
            raise HTTPException(status_code=404, detail="任务结果不存在")
        
        return JSONResponse({
            "success": True,
            "data": results
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task results failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def list_sessions():
    """
    列出所有会话
    """
    try:
        sessions = file_manager.list_sessions()
        
        return JSONResponse({
            "success": True,
            "data": sessions
        })
        
    except Exception as e:
        logger.error(f"List sessions failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    删除会话
    """
    try:
        success = file_manager.delete_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return JSONResponse({
            "success": True,
            "message": "会话已删除"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cancel-task/{session_id}")
async def cancel_task(session_id: str):
    """
    取消任务
    """
    try:
        success = task_manager.cancel_task(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在或无法取消")
        
        return JSONResponse({
            "success": True,
            "message": "任务已取消"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel task failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download-results/{session_id}")
async def download_results(session_id: str):
    """
    下载结果文件
    """
    try:
        results_file = file_manager.get_session_dir(session_id) / "evaluation_results.json"
        
        if not results_file.exists():
            raise HTTPException(status_code=404, detail="结果文件不存在")
        
        return FileResponse(
            path=str(results_file),
            filename=f"evaluation_results_{session_id}.json",
            media_type='application/json'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download results failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/audio/{filename}")
async def get_audio_file(session_id: str, filename: str):
    """
    获取指定会话的音频文件
    """
    try:
        import urllib.parse
        
        # 解码文件名
        filename = Path(urllib.parse.unquote(filename)).name
        
        # 构建音频文件路径
        session_dir = file_manager.get_session_dir(session_id)
        audio_file = session_dir / "audio" / filename
        
        # 如果audio目录不存在，尝试在results目录中直接查找
        if not audio_file.exists():
            audio_file = session_dir / filename
        
        # 如果还是不存在，尝试在temp目录中查找
        if not audio_file.exists():
            temp_dirs = list(session_dir.glob("temp_*"))
            for temp_dir in temp_dirs:
                potential_file = temp_dir / filename
                if potential_file.exists():
                    audio_file = potential_file
                    break
        
        if not audio_file.exists():
            raise HTTPException(status_code=404, detail=f"音频文件不存在: {filename}")
        
        # 检查文件类型
        if not audio_file.suffix.lower() in ['.wav', '.mp3', '.flac', '.m4a', '.ogg']:
            raise HTTPException(status_code=400, detail="不支持的音频文件格式")
        
        # 设置正确的媒体类型
        media_type_map = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg'
        }
        media_type = media_type_map.get(audio_file.suffix.lower(), 'audio/mpeg')
        
        return FileResponse(
            path=str(audio_file),
            filename=filename,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get audio file failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket端点
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket连接，用于实时推送进度信息
    """
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接活跃
            data = await websocket.receive_text()
            
            # 可以处理客户端发送的消息
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 健康检查
@app.get("/api/health")
async def health_check():
    """
    健康检查
    """
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

# 系统信息
@app.get("/api/system-info")
async def get_system_info():
    """
    获取系统信息
    """
    try:
        from .asr_engine import FUNASR_AVAILABLE
        
        # 支持的音频格式
        supported_formats = [".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"]
        
        return JSONResponse({
            "success": True,
            "data": {
                "funasr_available": FUNASR_AVAILABLE,
                "supported_audio_formats": supported_formats,
                "active_sessions": len(task_manager.sessions),
                "total_sessions": len(file_manager.list_sessions())
            }
        })
        
    except Exception as e:
        logger.error(f"Get system info failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 目录浏览
@app.get("/api/browse-directory")
async def browse_directory(path: str = None):
    """
    浏览目录内容
    """
    try:
        import os
        from pathlib import Path
        
        # 如果没有提供路径，使用当前用户目录
        if not path:
            path = str(Path.home())
        
        # 修复Windows路径问题
        path = path.replace('\\', '/')
        if path.startswith('C:') and not path.startswith('C:/'):
            path = path.replace('C:', 'C:/')
        
        # 验证路径是否存在
        directory = Path(path)
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"目录不存在: {path}")
        
        items = []
        try:
            # 列出目录内容
            for item in directory.iterdir():
                try:
                    if item.is_dir():
                        items.append({
                            "name": item.name,
                            "type": "directory",
                            "path": str(item),
                            "size": None
                        })
                    elif item.is_file():
                        # 只显示音频和文本文件
                        if item.suffix.lower() in ['.wav', '.mp3', '.flac', '.m4a', '.aac', '.ogg', '.txt']:
                            items.append({
                                "name": item.name,
                                "type": "file",
                                "path": str(item),
                                "size": item.stat().st_size,
                                "extension": item.suffix
                            })
                except (PermissionError, OSError):
                    continue
        except PermissionError:
            raise ValueError(f"没有权限访问目录: {path}")
        
        # 排序：目录在前，然后按名称排序
        items.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
        
        # 添加父目录选项（除了根目录）
        parent_dir = directory.parent
        if directory != parent_dir:
            items.insert(0, {
                "name": "..",
                "type": "parent",
                "path": str(parent_dir),
                "size": None
            })
        
        return JSONResponse({
            "success": True,
            "data": {
                "current_path": str(directory),
                "items": items
            }
        })
        
    except Exception as e:
        logger.error(f"Browse directory failed: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=400)

def run_server():
    """
    运行服务器
    """
    uvicorn.run(
        "backend.server:app",
        host=WEB_CONFIG["host"],
        port=WEB_CONFIG["port"],
        reload=WEB_CONFIG["debug"],
        log_level="info"
    )

if __name__ == "__main__":
    run_server()
