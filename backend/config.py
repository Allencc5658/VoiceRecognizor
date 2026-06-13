import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


# 基础路径配置
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
TEMP_DIR = BASE_DIR / "temp"
MODELS_DIR = Path(os.getenv("VOICE_RECOGNIZOR_MODELS_DIR", "models")).expanduser()
if not MODELS_DIR.is_absolute():
    MODELS_DIR = BASE_DIR / MODELS_DIR

# 确保目录存在
for dir_path in [DATA_DIR, RESULTS_DIR, TEMP_DIR, MODELS_DIR]:
    dir_path.mkdir(exist_ok=True)

# 音频配置
AUDIO_CONFIG = {
    "supported_formats": [".wav", ".pcm", ".mp3", ".flac"],
    "sample_rate": 16000,
    "channels": 1,
    "chunk_size": 1024
}

# Paraformer配置
ASR_CONFIG = {
    "model_name": "paraformer-zh",
    "model_revision": "v2.0.4",
    "model_path": MODELS_DIR / "paraformer",  # 本地模型路径
    "vad_model_path": MODELS_DIR / "vad",     # VAD模型路径
    "punc_model_path": MODELS_DIR / "punc",   # 标点符号模型路径
    "batch_size": 1,
    "device": os.getenv("VOICE_RECOGNIZOR_DEVICE", "cpu"),
    "language": "zh",
    "use_local_model": _env_bool("VOICE_RECOGNIZOR_USE_LOCAL_MODEL", True)
}

# 评测指标配置
EVALUATION_CONFIG = {
    "calculate_cer": True,
    "calculate_wer": True,
    "calculate_similarity": True,
    "similarity_threshold": 0.8
}

# Web服务配置
WEB_CONFIG = {
    "host": os.getenv("VOICE_RECOGNIZOR_HOST", "127.0.0.1"),
    "port": _env_int("VOICE_RECOGNIZOR_PORT", 8080),
    "debug": _env_bool("VOICE_RECOGNIZOR_DEBUG", True),
    "upload_max_size": _env_int("VOICE_RECOGNIZOR_UPLOAD_MAX_SIZE", 100 * 1024 * 1024),
    "allowed_extensions": {".wav", ".pcm", ".mp3", ".flac", ".txt"},
    "cors_origins": [
        origin.strip()
        for origin in os.getenv("VOICE_RECOGNIZOR_CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": BASE_DIR / "logs" / "tts_evaluation.log"
}

# 确保日志目录存在
LOG_CONFIG["file"].parent.mkdir(exist_ok=True)
