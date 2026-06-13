import os
import logging
import asyncio
from typing import List, Dict, Optional, Union
from pathlib import Path
import soundfile as sf
import librosa
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time

# FunASR imports
try:
    from funasr import AutoModel
    from funasr.utils.postprocess_utils import rich_transcription_postprocess
    FUNASR_AVAILABLE = True
except ImportError:
    FUNASR_AVAILABLE = False
    logging.warning("FunASR not available. Please install it for ASR functionality.")

# 修复相对导入问题
try:
    from .config import ASR_CONFIG, AUDIO_CONFIG
except ImportError:
    from backend.config import ASR_CONFIG, AUDIO_CONFIG

logger = logging.getLogger(__name__)

class AudioProcessor:
    """音频预处理器"""
    
    def __init__(self):
        self.target_sr = AUDIO_CONFIG["sample_rate"]
        self.target_channels = AUDIO_CONFIG["channels"]
    
    def load_audio(self, audio_path: Union[str, Path]) -> np.ndarray:
        """
        加载音频文件并进行预处理
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            # 根据文件扩展名处理
            if audio_path.suffix.lower() == '.pcm':
                # PCM文件需要指定参数
                audio_data = np.fromfile(audio_path, dtype=np.int16)
                audio_data = audio_data.astype(np.float32) / 32768.0
                sr = self.target_sr
            else:
                # 其他格式使用librosa加载
                audio_data, sr = librosa.load(
                    str(audio_path), 
                    sr=self.target_sr, 
                    mono=True
                )
            
            # 确保音频长度不为零
            if len(audio_data) == 0:
                raise ValueError(f"Empty audio file: {audio_path}")
            
            # 归一化
            audio_data = librosa.util.normalize(audio_data)
            
            logger.info(f"Loaded audio: {audio_path}, duration: {len(audio_data)/sr:.2f}s")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error loading audio {audio_path}: {str(e)}")
            raise

class ParaformerASR:
    """Paraformer语音识别器"""
    
    def __init__(self):
        self.model = None
        self.audio_processor = AudioProcessor()
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    def initialize(self):
        """初始化Paraformer模型"""
        if not FUNASR_AVAILABLE:
            raise RuntimeError("FunASR is not available. Please install funasr package.")
        
        try:
            logger.info("Initializing Paraformer model...")
            
            # 检查是否使用本地模型
            if ASR_CONFIG.get("use_local_model", False):
                model_path = ASR_CONFIG.get("model_path")
                vad_model_path = ASR_CONFIG.get("vad_model_path")
                punc_model_path = ASR_CONFIG.get("punc_model_path")
                
                if model_path and model_path.exists():
                    logger.info(f"Using local model: {model_path}")
                    
                    # 检查VAD和PUNC模型是否存在
                    if (vad_model_path and vad_model_path.exists() and 
                        punc_model_path and punc_model_path.exists()):
                        logger.info(f"Using VAD model: {vad_model_path}")
                        logger.info(f"Using PUNC model: {punc_model_path}")
                        self.model = AutoModel(
                            model=str(model_path),
                            vad_model=str(vad_model_path),
                            punc_model=str(punc_model_path),
                            device=ASR_CONFIG["device"],
                            disable_update=True
                        )
                    else:
                        logger.warning("VAD or PUNC model not found, using basic model")
                        self.model = AutoModel(
                            model=str(model_path),
                            device=ASR_CONFIG["device"],
                            disable_update=True
                        )
                else:
                    logger.warning(f"Local model not found: {model_path}")
                    logger.info("Falling back to online model...")
                    self.model = AutoModel(
                        model=ASR_CONFIG["model_name"],
                        model_revision=ASR_CONFIG["model_revision"],
                        device=ASR_CONFIG["device"]
                    )
            else:
                # 使用在线模型
                self.model = AutoModel(
                    model=ASR_CONFIG["model_name"],
                    model_revision=ASR_CONFIG["model_revision"],
                    device=ASR_CONFIG["device"]
                )
            
            logger.info("Paraformer model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Paraformer: {str(e)}")
            raise
    
    def recognize_single(self, audio_path: Union[str, Path]) -> Dict:
        """
        识别单个音频文件
        """
        if self.model is None:
            self.initialize()
        
        start_time = time.time()
        
        try:
            # 加载音频
            audio_data = self.audio_processor.load_audio(audio_path)
            
            # 进行识别
            result = self.model.generate(
                input=audio_data,
                batch_size=ASR_CONFIG["batch_size"]
            )
            
            # 提取文本结果
            if isinstance(result, list) and len(result) > 0:
                text = result[0].get("text", "")
            else:
                text = ""
            
            # 后处理
            text = self._postprocess_text(text)
            
            processing_time = time.time() - start_time
            
            return {
                "file_path": str(audio_path),
                "recognized_text": text,
                "processing_time": processing_time,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Recognition failed for {audio_path}: {str(e)}")
            return {
                "file_path": str(audio_path),
                "recognized_text": "",
                "processing_time": processing_time,
                "success": False,
                "error": str(e)
            }
    
    def _postprocess_text(self, text: str) -> str:
        """文本后处理"""
        if not text:
            return ""
        
        # 移除多余的空格
        text = " ".join(text.split())
        
        # 移除标点符号（可选）
        # text = re.sub(r'[^\w\s]', '', text)
        
        return text.strip()
    
    async def recognize_batch(self, audio_files: List[Union[str, Path]], 
                            progress_callback=None) -> List[Dict]:
        """
        批量识别音频文件
        """
        results = []
        total_files = len(audio_files)
        
        for i, audio_file in enumerate(audio_files):
            # 在线程池中执行识别
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, 
                self.recognize_single, 
                audio_file
            )
            
            results.append(result)
            
            # 更新进度
            if progress_callback:
                progress = (i + 1) / total_files * 100
                await progress_callback(progress, i + 1, total_files)
        
        return results
    
    def cleanup(self):
        """清理资源"""
        if self.executor:
            self.executor.shutdown(wait=True)

# 全局ASR实例
asr_engine = ParaformerASR()

def get_asr_engine() -> ParaformerASR:
    """获取ASR引擎实例"""
    return asr_engine
