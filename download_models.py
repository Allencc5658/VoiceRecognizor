import os
import sys
from pathlib import Path
import subprocess
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 模型配置
MODELS_CONFIG = {
    "paraformer": {
        "model_id": "damo/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "local_path": "models/paraformer",
        "description": "Paraformer中文语音识别模型",
        "files": [
            "model.pt",
            "config.yaml", 
            "tokens.json",
            "am.mvn"
        ]
    },
    "vad": {
        "model_id": "damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        "local_path": "models/vad",
        "description": "语音活动检测(VAD)模型",
        "files": [
            "model.pt",
            "config.yaml"
        ]
    },
    "punc": {
        "model_id": "damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        "local_path": "models/punc", 
        "description": "标点符号恢复模型",
        "files": [
            "model.pt",
            "config.yaml",
            "tokens.json"
        ]
    }
}

class ModelDownloader:
    """模型下载器"""
    
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.models_dir = self.base_dir / "models"
        self.models_dir.mkdir(exist_ok=True)
    
    def check_modelscope_hub(self):
        """检查modelscope-hub是否已安装"""
        try:
            import modelscope
            logger.info("✓ modelscope已安装")
            return True
        except ImportError:
            logger.warning("✗ modelscope未安装")
            return False
    
    def install_modelscope(self):
        """安装modelscope"""
        logger.info("正在安装modelscope...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "modelscope[audio]", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"
            ])
            logger.info("✓ modelscope安装成功")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ modelscope安装失败: {e}")
            return False
    
    def download_model(self, model_key):
        """下载指定模型"""
        if model_key not in MODELS_CONFIG:
            logger.error(f"未知模型: {model_key}")
            return False
        
        model_config = MODELS_CONFIG[model_key]
        model_id = model_config["model_id"]
        # 修复路径问题：直接使用绝对路径
        local_path = self.models_dir / model_key  # 直接使用model_key作为文件夹名
        
        logger.info(f"正在下载模型: {model_config['description']}")
        logger.info(f"模型ID: {model_id}")
        logger.info(f"本地路径: {local_path}")
        
        try:
            from modelscope import snapshot_download
            
            # 确保目标目录存在
            local_path.mkdir(parents=True, exist_ok=True)
            
            # 下载模型 - 修复参数配置
            snapshot_download(
                model_id=model_id,
                local_dir=str(local_path),
                ignore_file_pattern=[r'\.git.*', r'README\.md']
            )
            
            logger.info(f"✓ 模型下载成功: {model_key}")
            
            # 验证文件
            missing_files = []
            for file_name in model_config["files"]:
                file_path = local_path / file_name
                if not file_path.exists():
                    missing_files.append(file_name)
            
            if missing_files:
                logger.warning(f"缺少文件: {missing_files}")
                return False
            else:
                logger.info(f"✓ 模型文件验证完成: {model_key}")
                return True
                
        except Exception as e:
            logger.error(f"✗ 模型下载失败: {e}")
            return False
    
    def check_model_exists(self, model_key):
        """检查模型是否已存在"""
        if model_key not in MODELS_CONFIG:
            return False
        
        model_config = MODELS_CONFIG[model_key]
        # 修复路径问题：使用与下载时相同的路径逻辑
        local_path = self.models_dir / model_key
        
        if not local_path.exists():
            return False
        
        # 检查关键文件是否存在
        for file_name in model_config["files"]:
            file_path = local_path / file_name
            if not file_path.exists():
                return False
        
        return True
    
    def download_all_models(self):
        """下载所有模型"""
        logger.info("开始下载所有必需的模型...")
        
        # 检查并安装modelscope
        if not self.check_modelscope_hub():
            if not self.install_modelscope():
                logger.error("无法安装modelscope，请手动安装")
                return False
        
        success_count = 0
        total_count = len(MODELS_CONFIG)
        
        for model_key in MODELS_CONFIG:
            if self.check_model_exists(model_key):
                logger.info(f"✓ 模型已存在，跳过下载: {model_key}")
                success_count += 1
            else:
                if self.download_model(model_key):
                    success_count += 1
                else:
                    logger.error(f"✗ 模型下载失败: {model_key}")
        
        logger.info(f"模型下载完成: {success_count}/{total_count}")
        return success_count == total_count
    
    def list_models(self):
        """列出所有模型状态"""
        print("\n模型状态检查:")
        print("=" * 60)
        
        for model_key, config in MODELS_CONFIG.items():
            status = "✓ 已下载" if self.check_model_exists(model_key) else "✗ 未下载"
            print(f"{config['description']:30} {status}")
            print(f"  模型ID: {config['model_id']}")
            print(f"  本地路径: models/{model_key}")  # 修复显示路径
            print()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TTS评测系统模型下载工具")
    parser.add_argument("--list", action="store_true", help="列出所有模型状态")
    parser.add_argument("--download", choices=list(MODELS_CONFIG.keys()) + ["all"], 
                       help="下载指定模型或所有模型")
    parser.add_argument("--check", action="store_true", help="检查模型完整性")
    
    args = parser.parse_args()
    
    downloader = ModelDownloader()
    
    if args.list:
        downloader.list_models()
    elif args.download:
        if args.download == "all":
            downloader.download_all_models()
        else:
            downloader.download_model(args.download)
    elif args.check:
        downloader.list_models()
    else:
        # 默认行为：检查并下载缺失的模型
        print("TTS评测系统模型下载工具")
        print("正在检查模型状态...")
        
        downloader.list_models()
        
        # 检查是否有缺失的模型
        missing_models = []
        for model_key in MODELS_CONFIG:
            if not downloader.check_model_exists(model_key):
                missing_models.append(model_key)
        
        if missing_models:
            print(f"\n发现 {len(missing_models)} 个缺失的模型:")
            for model_key in missing_models:
                print(f"  - {MODELS_CONFIG[model_key]['description']}")
            
            choice = input("\n是否现在下载缺失的模型? (y/n): ").lower()
            if choice == 'y':
                downloader.download_all_models()
            else:
                print("跳过模型下载。注意：系统可能无法正常工作。")
        else:
            print("\n✓ 所有模型已就绪！")

if __name__ == "__main__":
    main()
