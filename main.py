#!/usr/bin/env python3
"""
TTS语音评测系统启动文件
"""
import sys
import os
import subprocess
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    """检查依赖包"""
    try:
        import fastapi
        import uvicorn
        import librosa
        import soundfile
        import jieba
        import editdistance
        import numpy
        
        print("✓ 核心依赖包检查通过")
        
        try:
            import funasr
            print("✓ FunASR语音识别引擎可用")
            return True
        except ImportError:
            print("⚠ FunASR未安装，语音识别功能将不可用")
            print("请运行: pip install funasr")
            return False
            
    except ImportError as e:
        print(f"✗ 缺少依赖包: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def install_dependencies():
    """安装依赖包"""
    print("正在安装依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ 依赖包安装完成")
        return True
    except subprocess.CalledProcessError:
        print("✗ 依赖包安装失败")
        return False

def check_models():
    """检查模型文件"""
    print("正在检查模型文件...")
    
    try:
        from download_models import ModelDownloader
        downloader = ModelDownloader()
        
        missing_models = []
        for model_key in ["paraformer", "vad", "punc"]:
            if not downloader.check_model_exists(model_key):
                missing_models.append(model_key)
        
        if missing_models:
            print(f"⚠ 发现缺失的模型: {missing_models}")
            print("这些模型是语音识别功能必需的。")
            
            choice = input("是否现在下载缺失的模型? (y/n): ").lower()
            if choice == 'y':
                success = downloader.download_all_models()
                if not success:
                    print("⚠ 部分模型下载失败，系统可能无法正常工作")
                    print("请参考 MODEL_DOWNLOAD.md 了解详细的下载说明")
                    return False
                else:
                    print("✓ 所有模型下载完成")
                    return True
            else:
                print("⚠ 跳过模型下载，语音识别功能将不可用")
                return False
        else:
            print("✓ 所有必需模型已就绪")
            return True
            
    except ImportError:
        print("⚠ 无法导入模型下载器，请手动检查模型文件")
        return True
    except Exception as e:
        print(f"⚠ 模型检查出错: {e}")
        return True
def main():
    """主函数"""
    print("=" * 50)
    print("TTS语音评测系统")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("✗ 需要Python 3.8或更高版本")
        sys.exit(1)
    
    print(f"✓ Python版本: {sys.version.split()[0]}")
    
    # 检查依赖
    if not check_dependencies():
        choice = input("是否自动安装依赖包? (y/n): ").lower()
        if choice == 'y':
            if not install_dependencies():
                sys.exit(1)
        else:
            print("请手动安装依赖包后重试")
            sys.exit(1)
    
    # 检查模型文件
    check_models()
    
    # 创建必要目录
    from backend.config import DATA_DIR, RESULTS_DIR, LOG_CONFIG
    
    DATA_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)
    LOG_CONFIG["file"].parent.mkdir(exist_ok=True)
    
    print("✓ 目录结构检查完成")
    
    # 启动服务器
    try:
        from backend.server import run_server
        print("\n启动Web服务器...")
        print("访问地址: http://127.0.0.1:8080")
        print("按 Ctrl+C 停止服务器")
        print("-" * 50)
        
        run_server()
        
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        print("如果是导入错误，请尝试运行: python -m backend.server")
        sys.exit(1)

if __name__ == "__main__":
    main()
