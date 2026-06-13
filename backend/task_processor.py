import logging
import asyncio
from typing import Dict, List, Optional, Callable
from pathlib import Path
from datetime import datetime
import json
import sys

# 修复相对导入问题
try:
    from .asr_engine import get_asr_engine
    from .evaluator import TTSEvaluator
    from .file_manager import file_manager
    from .config import EVALUATION_CONFIG
except ImportError:
    # 如果相对导入失败，使用绝对导入
    from backend.asr_engine import get_asr_engine
    from backend.evaluator import TTSEvaluator
    from backend.file_manager import file_manager
    from backend.config import EVALUATION_CONFIG

logger = logging.getLogger(__name__)

class TaskProgress:
    """任务进度跟踪"""
    
    def __init__(self, total_steps: int):
        self.total_steps = total_steps
        self.current_step = 0
        self.current_stage = "初始化"
        self.progress_percentage = 0.0
        self.start_time = datetime.now()
        self.estimated_time_remaining = None
        self.callbacks = []
    
    def add_callback(self, callback: Callable):
        """添加进度回调函数"""
        self.callbacks.append(callback)
    
    async def update(self, step: int = None, stage: str = None):
        """更新进度"""
        if step is not None:
            self.current_step = step
        
        if stage is not None:
            self.current_stage = stage
        
        self.progress_percentage = min(100.0, (self.current_step / self.total_steps) * 100)
        
        # 估算剩余时间
        if self.current_step > 0:
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            avg_time_per_step = elapsed_time / self.current_step
            remaining_steps = self.total_steps - self.current_step
            self.estimated_time_remaining = avg_time_per_step * remaining_steps
        
        # 通知回调函数
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self)
                else:
                    # 对于同步回调函数，在异步环境中运行
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, callback, self)
            except Exception as e:
                logger.warning(f"Progress callback error: {str(e)}")
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_steps": self.total_steps,
            "current_step": self.current_step,
            "current_stage": self.current_stage,
            "progress_percentage": self.progress_percentage,
            "start_time": self.start_time.isoformat(),
            "estimated_time_remaining": self.estimated_time_remaining
        }

class EvaluationTask:
    """评测任务"""
    
    def __init__(self):
        self.asr_engine = get_asr_engine()
        self.evaluator = TTSEvaluator()
        self.sessions = {}  # 活动会话
    
    async def start_evaluation(self, 
                             directory_path: str,
                             task_name: str = None,
                             progress_callback: Callable = None) -> str:
        """
        开始评测任务
        """
        logger.info(f"Starting evaluation task for directory: {directory_path}")
        
        # 创建会话
        session_id = file_manager.create_task_session(task_name)
        
        try:
            # 1. 扫描文件
            logger.info("Scanning directory...")
            file_scan_result = file_manager.scan_directory(directory_path)
            
            # 2. 匹配音频和文本文件
            logger.info("Matching audio and text files...")
            file_pairs = file_manager.match_audio_text_pairs(
                file_scan_result["audio_files"],
                file_scan_result["text_files"]
            )
            
            if not file_pairs:
                raise ValueError("No matching audio-text pairs found")
            
            # 3. 复制文件到会话目录
            logger.info("Copying files to session directory...")
            copied_files = file_manager.copy_files_to_session(session_id, file_pairs)
            
            # 4. 保存任务元数据
            metadata = {
                "session_id": session_id,
                "task_name": task_name or session_id,
                "source_directory": directory_path,
                "total_files": len(file_pairs),
                "start_time": datetime.now().isoformat(),
                "status": "running",
                "config": EVALUATION_CONFIG.copy()
            }
            file_manager.save_task_metadata(session_id, metadata)
            
            # 5. 创建进度跟踪
            total_steps = len(file_pairs)
            progress = TaskProgress(total_steps)
            
            if progress_callback:
                progress.add_callback(progress_callback)
            
            # 将任务添加到活动会话
            self.sessions[session_id] = {
                "progress": progress,
                "metadata": metadata,
                "status": "running"
            }
            
            # 6. 启动异步处理
            asyncio.create_task(self._process_evaluation(session_id, copied_files, progress))
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to start evaluation: {str(e)}")
            # 更新状态为失败
            if session_id in self.sessions:
                self.sessions[session_id]["status"] = "failed"
            raise
    
    async def _process_evaluation(self, session_id: str, file_pairs: List[Dict], progress: TaskProgress):
        """
        处理评测任务
        """
        try:
            await progress.update(0, "正在初始化ASR引擎...")
            
            # 初始化ASR引擎
            if self.asr_engine.model is None:
                self.asr_engine.initialize()
            
            evaluation_results = []
            
            # 逐个处理文件
            for i, file_info in enumerate(file_pairs):
                try:
                    await progress.update(i, f"正在处理第 {i+1} 个文件...")
                    
                    # 语音识别
                    audio_path = Path(file_info["session_audio_path"])
                    asr_result = self.asr_engine.recognize_single(audio_path)
                    
                    if asr_result["success"]:
                        # 文本评测
                        original_text = file_info["original_text"]
                        recognized_text = asr_result["recognized_text"]
                        
                        eval_result = self.evaluator.evaluate_single(original_text, recognized_text)
                        
                        # 组合结果
                        combined_result = {
                            "file_index": i,
                            "audio_file": Path(file_info["session_audio_path"]).name,  # 保存session中的实际文件名
                            "audio_file_path": file_info["original_audio_path"],  # 完整路径用于内部处理
                            "text_file": file_info["original_text_path"],
                            "original_text": original_text,
                            "recognized_text": recognized_text,
                            "processing_time": asr_result["processing_time"],
                            "cer": eval_result.cer,
                            "wer": eval_result.wer,
                            "similarity": eval_result.similarity,
                            "exact_match": eval_result.exact_match,
                            "char_operations": {
                                "insertions": eval_result.char_insertions,
                                "deletions": eval_result.char_deletions,
                                "substitutions": eval_result.char_substitutions
                            },
                            "word_operations": {
                                "insertions": eval_result.word_insertions,
                                "deletions": eval_result.word_deletions,
                                "substitutions": eval_result.word_substitutions
                            },
                            "diff_details": eval_result.diff_details,
                            "success": True,
                            "error": None
                        }
                    else:
                        # ASR失败的情况
                        combined_result = {
                            "file_index": i,
                            "audio_file": Path(file_info["session_audio_path"]).name,  # 保存session中的实际文件名
                            "audio_file_path": file_info["original_audio_path"],  # 完整路径用于内部处理
                            "text_file": file_info["original_text_path"],
                            "original_text": file_info["original_text"],
                            "recognized_text": "",
                            "processing_time": asr_result["processing_time"],
                            "cer": float('inf'),
                            "wer": float('inf'),
                            "similarity": 0.0,
                            "exact_match": False,
                            "char_operations": {"insertions": 0, "deletions": 0, "substitutions": 0},
                            "word_operations": {"insertions": 0, "deletions": 0, "substitutions": 0},
                            "diff_details": [],
                            "success": False,
                            "error": asr_result["error"]
                        }
                    
                    evaluation_results.append(combined_result)
                    
                    # 更新进度到当前完成的文件数
                    await progress.update(i + 1, f"已完成第 {i+1} 个文件")
                    
                except Exception as e:
                    logger.error(f"Error processing file {i}: {str(e)}")
                    # 添加错误结果
                    file_info = file_pairs[i]
                    error_result = {
                        "file_index": i,
                        "audio_file": Path(file_info["session_audio_path"]).name if "session_audio_path" in file_info else Path(file_info["original_audio_path"]).name,  # 保存session中的实际文件名
                        "audio_file_path": file_info["original_audio_path"],  # 完整路径用于内部处理
                        "text_file": file_info["original_text_path"],
                        "original_text": file_info["original_text"],
                        "recognized_text": "",
                        "processing_time": 0.0,
                        "cer": float('inf'),
                        "wer": float('inf'),
                        "similarity": 0.0,
                        "exact_match": False,
                        "char_operations": {"insertions": 0, "deletions": 0, "substitutions": 0},
                        "word_operations": {"insertions": 0, "deletions": 0, "substitutions": 0},
                        "diff_details": [],
                        "success": False,
                        "error": str(e)
                    }
                    evaluation_results.append(error_result)
                    
                    # 即使出错也要更新进度
                    await progress.update(i + 1, f"处理第 {i+1} 个文件时出错")
            
            # 完成处理
            await progress.update(len(file_pairs), "正在计算汇总统计...")
            
            # 计算汇总统计
            from .evaluator import EvaluationResult
            eval_result_objects = []
            
            for result in evaluation_results:
                if result["success"]:
                    eval_obj = EvaluationResult(
                        original_text=result["original_text"],
                        recognized_text=result["recognized_text"],
                        cer=result["cer"],
                        wer=result["wer"],
                        similarity=result["similarity"],
                        exact_match=result["exact_match"],
                        char_insertions=result["char_operations"]["insertions"],
                        char_deletions=result["char_operations"]["deletions"],
                        char_substitutions=result["char_operations"]["substitutions"],
                        word_insertions=result["word_operations"]["insertions"],
                        word_deletions=result["word_operations"]["deletions"],
                        word_substitutions=result["word_operations"]["substitutions"],
                        diff_details=result["diff_details"]
                    )
                    eval_result_objects.append(eval_obj)
            
            summary_stats = self.evaluator.calculate_summary_statistics(eval_result_objects)
            
            # 保存结果
            file_manager.save_evaluation_results(session_id, evaluation_results)
            file_manager.save_summary_statistics(session_id, summary_stats)
            
            # 更新会话状态
            if session_id in self.sessions:
                self.sessions[session_id]["status"] = "completed"
                self.sessions[session_id]["results"] = evaluation_results
                self.sessions[session_id]["statistics"] = summary_stats
            
            # 更新元数据
            metadata = file_manager.load_session_results(session_id)["metadata"]
            metadata["status"] = "completed"
            metadata["end_time"] = datetime.now().isoformat()
            metadata["total_processing_time"] = (datetime.now() - datetime.fromisoformat(metadata["start_time"])).total_seconds()
            file_manager.save_task_metadata(session_id, metadata)
            
            # 最终进度更新
            await progress.update(len(file_pairs), "评测完成")
            
            logger.info(f"Evaluation task completed: {session_id}")
            
        except Exception as e:
            logger.error(f"Evaluation task failed: {str(e)}")
            
            # 更新失败状态
            if session_id in self.sessions:
                self.sessions[session_id]["status"] = "failed"
                self.sessions[session_id]["error"] = str(e)
            
            # 更新元数据
            try:
                metadata = file_manager.load_session_results(session_id)["metadata"]
                metadata["status"] = "failed"
                metadata["error"] = str(e)
                metadata["end_time"] = datetime.now().isoformat()
                file_manager.save_task_metadata(session_id, metadata)
            except Exception:
                pass
    
    def get_task_status(self, session_id: str) -> Optional[Dict]:
        """
        获取任务状态
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            status = {
                "session_id": session_id,
                "status": session["status"],
                "progress": session["progress"].to_dict() if "progress" in session else None,
                "metadata": session.get("metadata"),
                "error": session.get("error")
            }
            return status
        else:
            # 尝试从文件加载
            session_data = file_manager.load_session_results(session_id)
            if session_data and session_data["metadata"]:
                return {
                    "session_id": session_id,
                    "status": session_data["metadata"].get("status", "unknown"),
                    "progress": None,
                    "metadata": session_data["metadata"],
                    "error": session_data["metadata"].get("error")
                }
        
        return None
    
    def get_task_results(self, session_id: str) -> Optional[Dict]:
        """
        获取任务结果
        """
        if session_id in self.sessions and self.sessions[session_id]["status"] == "completed":
            return {
                "session_id": session_id,
                "results": self.sessions[session_id]["results"],
                "statistics": self.sessions[session_id]["statistics"]
            }
        else:
            # 从文件加载
            return file_manager.load_session_results(session_id)
    
    def cancel_task(self, session_id: str) -> bool:
        """
        取消任务
        """
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "cancelled"
            return True
        
        return False

# 全局任务管理器
task_manager = EvaluationTask()
