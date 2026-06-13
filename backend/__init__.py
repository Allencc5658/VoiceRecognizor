"""
TTS语音评测系统后端模块
"""

__version__ = "1.0.0"
__author__ = "TTS Evaluation System"

# 导入主要类和函数
from .config import *
from .asr_engine import get_asr_engine, ParaformerASR
from .evaluator import TTSEvaluator, EvaluationResult, TextComparator
from .file_manager import file_manager, upload_manager
from .task_processor import task_manager, EvaluationTask
from .server import app

__all__ = [
    # 配置
    "BASE_DIR", "DATA_DIR", "RESULTS_DIR",
    "AUDIO_CONFIG", "ASR_CONFIG", "EVALUATION_CONFIG", "WEB_CONFIG",
    
    # ASR引擎
    "get_asr_engine", "ParaformerASR",
    
    # 评测器
    "TTSEvaluator", "EvaluationResult", "TextComparator",
    
    # 文件管理
    "file_manager", "upload_manager",
    
    # 任务处理
    "task_manager", "EvaluationTask",
    
    # Web应用
    "app"
]
