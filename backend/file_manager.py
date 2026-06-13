import os
import logging
import asyncio
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import json
import hashlib
from datetime import datetime
import shutil
import re

# 修复相对导入问题
try:
    from .config import AUDIO_CONFIG, DATA_DIR, RESULTS_DIR
except ImportError:
    from backend.config import AUDIO_CONFIG, DATA_DIR, RESULTS_DIR

logger = logging.getLogger(__name__)

class FileManager:
    """文件管理器"""
    
    def __init__(self):
        self.supported_audio_formats = set(AUDIO_CONFIG["supported_formats"])
        self.text_formats = {".txt"}
        self.results_root = RESULTS_DIR.resolve()

    def _sanitize_session_id(self, session_id: str) -> str:
        """将用户输入的任务名转换为安全的目录名。"""
        session_id = (session_id or "").strip()
        session_id = re.sub(r"[^0-9A-Za-z_.\-\u4e00-\u9fff]+", "_", session_id)
        session_id = session_id.strip("._- ")
        return session_id[:80] or f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def get_session_dir(self, session_id: str) -> Path:
        """解析会话目录，并防止路径穿越。"""
        safe_session_id = self._sanitize_session_id(session_id)
        if safe_session_id != session_id:
            raise ValueError("Invalid session_id")

        session_dir = (RESULTS_DIR / safe_session_id).resolve()
        if session_dir != self.results_root and self.results_root not in session_dir.parents:
            raise ValueError("Invalid session path")
        return session_dir
    
    def scan_directory(self, directory_path: str) -> Dict[str, List[Path]]:
        """
        扫描目录，分类音频文件和文本文件
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        audio_files = []
        text_files = []
        
        # 递归扫描目录
        for file_path in directory_path.rglob("*"):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                
                if suffix in self.supported_audio_formats:
                    audio_files.append(file_path)
                elif suffix in self.text_formats:
                    text_files.append(file_path)
        
        logger.info(f"Found {len(audio_files)} audio files and {len(text_files)} text files")
        
        return {
            "audio_files": sorted(audio_files),
            "text_files": sorted(text_files)
        }
    
    def match_audio_text_pairs(self, audio_files: List[Path], text_files: List[Path]) -> List[Tuple[Path, Path, str]]:
        """
        匹配音频文件和对应的文本文件
        返回: [(audio_path, text_path, original_text), ...]
        """
        pairs = []
        
        # 创建文本文件映射 (去除扩展名作为key)
        text_map = {}
        for text_file in text_files:
            stem = text_file.stem.lower()
            text_map[stem] = text_file
        
        # 匹配音频文件
        for audio_file in audio_files:
            audio_stem = audio_file.stem.lower()
            
            if audio_stem in text_map:
                text_file = text_map[audio_stem]
                try:
                    # 读取文本内容
                    with open(text_file, 'r', encoding='utf-8') as f:
                        original_text = f.read().strip()
                    
                    pairs.append((audio_file, text_file, original_text))
                    logger.debug(f"Matched: {audio_file.name} <-> {text_file.name}")
                    
                except Exception as e:
                    logger.warning(f"Failed to read text file {text_file}: {str(e)}")
            else:
                logger.warning(f"No matching text file found for audio: {audio_file.name}")
        
        logger.info(f"Successfully matched {len(pairs)} audio-text pairs")
        return pairs
    
    def create_task_session(self, task_name: str = None) -> str:
        """
        创建任务会话ID
        """
        session_id = self._sanitize_session_id(task_name or f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # 创建会话目录
        session_dir = self.get_session_dir(session_id)
        base_session_id = session_id
        counter = 1
        while session_dir.exists():
            session_id = f"{base_session_id}_{counter}"
            session_dir = self.get_session_dir(session_id)
            counter += 1

        session_dir.mkdir(exist_ok=True)
        
        return session_id
    
    def save_task_metadata(self, session_id: str, metadata: Dict):
        """
        保存任务元数据
        """
        session_dir = self.get_session_dir(session_id)
        metadata_file = session_dir / "metadata.json"
        session_dir.mkdir(exist_ok=True)
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
    
    def save_evaluation_results(self, session_id: str, results: List[Dict]):
        """
        保存评测结果
        """
        session_dir = self.get_session_dir(session_id)
        results_file = session_dir / "evaluation_results.json"
        session_dir.mkdir(exist_ok=True)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    def save_summary_statistics(self, session_id: str, statistics: Dict):
        """
        保存汇总统计
        """
        session_dir = self.get_session_dir(session_id)
        stats_file = session_dir / "summary_statistics.json"
        session_dir.mkdir(exist_ok=True)
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, indent=2, ensure_ascii=False, default=str)
    
    def load_session_results(self, session_id: str) -> Optional[Dict]:
        """
        加载会话结果
        """
        session_dir = self.get_session_dir(session_id)
        
        if not session_dir.exists():
            return None
        
        result = {
            "session_id": session_id,
            "metadata": None,
            "results": None,
            "statistics": None
        }
        
        # 加载元数据
        metadata_file = session_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                result["metadata"] = json.load(f)
        
        # 加载评测结果
        results_file = session_dir / "evaluation_results.json"
        if results_file.exists():
            with open(results_file, 'r', encoding='utf-8') as f:
                result["results"] = json.load(f)
        
        # 加载统计信息
        stats_file = session_dir / "summary_statistics.json"
        if stats_file.exists():
            with open(stats_file, 'r', encoding='utf-8') as f:
                result["statistics"] = json.load(f)
        
        return result
    
    def list_sessions(self) -> List[Dict]:
        """
        列出所有会话
        """
        sessions = []
        
        for session_dir in RESULTS_DIR.iterdir():
            if session_dir.is_dir():
                metadata_file = session_dir / "metadata.json"
                
                session_info = {
                    "session_id": session_dir.name,
                    "created_time": datetime.fromtimestamp(session_dir.stat().st_ctime).isoformat(),
                    "has_results": (session_dir / "evaluation_results.json").exists()
                }
                
                # 尝试加载元数据
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            session_info.update(metadata)
                    except Exception:
                        pass
                
                sessions.append(session_info)
        
        # 按创建时间排序
        sessions.sort(key=lambda x: datetime.fromisoformat(x["created_time"]), reverse=True)
        
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        """
        session_dir = self.get_session_dir(session_id)
        
        if session_dir.exists():
            try:
                shutil.rmtree(session_dir)
                logger.info(f"Deleted session: {session_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete session {session_id}: {str(e)}")
                return False
        
        return False
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """
        计算文件哈希值
        """
        hash_md5 = hashlib.md5()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def copy_files_to_session(self, session_id: str, file_pairs: List[Tuple[Path, Path, str]]) -> List[Dict]:
        """
        将文件复制到会话目录
        """
        session_dir = self.get_session_dir(session_id)
        audio_dir = session_dir / "audio"
        text_dir = session_dir / "text"
        
        audio_dir.mkdir(exist_ok=True)
        text_dir.mkdir(exist_ok=True)
        
        copied_files = []
        
        for i, (audio_path, text_path, original_text) in enumerate(file_pairs):
            try:
                # 复制音频文件
                audio_dest = audio_dir / f"{i:04d}_{audio_path.name}"
                shutil.copy2(audio_path, audio_dest)
                
                # 复制文本文件
                text_dest = text_dir / f"{i:04d}_{text_path.name}"
                shutil.copy2(text_path, text_dest)
                
                file_info = {
                    "index": i,
                    "original_audio_path": str(audio_path),
                    "original_text_path": str(text_path),
                    "session_audio_path": str(audio_dest),
                    "session_text_path": str(text_dest),
                    "original_text": original_text,
                    "audio_hash": self.calculate_file_hash(audio_path),
                    "text_hash": self.calculate_file_hash(text_path)
                }
                
                copied_files.append(file_info)
                
            except Exception as e:
                logger.error(f"Failed to copy file pair {i}: {str(e)}")
        
        return copied_files

class UploadManager:
    """上传文件管理器"""
    
    def __init__(self):
        self.upload_dir = DATA_DIR / "uploads"
        self.upload_dir.mkdir(exist_ok=True)
    
    async def save_uploaded_file(self, file_data: bytes, filename: str) -> Path:
        """
        保存上传的文件
        """
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.upload_dir / f"{timestamp}_{filename}"
        
        # 异步写入文件
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._write_file, file_path, file_data)
        
        return file_path
    
    def _write_file(self, file_path: Path, file_data: bytes):
        """
        写入文件
        """
        with open(file_path, 'wb') as f:
            f.write(file_data)
    
    def cleanup_old_uploads(self, days: int = 7):
        """
        清理旧的上传文件
        """
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        
        for file_path in self.upload_dir.rglob("*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    logger.info(f"Cleaned up old upload: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up {file_path}: {str(e)}")

# 全局实例
file_manager = FileManager()
upload_manager = UploadManager()
