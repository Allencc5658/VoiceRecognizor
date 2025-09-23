# TTS语音评测系统

基于Paraformer的高精度TTS合成质量评测平台，提供完整的语音识别、文本比对和可视化展示功能。

## 系统架构

```
VoiceRecognizor/
├── backend/                 # 后端Python模块
│   ├── __init__.py         # 模块初始化
│   ├── config.py           # 配置文件
│   ├── asr_engine.py       # 语音识别引擎
│   ├── evaluator.py        # 文本评测模块
│   ├── file_manager.py     # 文件管理模块
│   ├── task_processor.py   # 任务处理模块
│   └── server.py           # Web服务器
├── frontend/               # 前端Web页面
│   ├── index.html          # 主页面
│   ├── style.css           # 样式文件
│   └── script.js           # JavaScript脚本
├── data/                   # 数据目录
├── results/                # 结果存储目录
├── requirements.txt        # Python依赖
└── README.md              # 项目说明
```

## 安装和使用

### 环境要求

- Python 3.8+
- 支持的音频格式: WAV, PCM, MP3, FLAC


#### 需要下载的模型：
1. **Paraformer语音识别模型** (~1.2GB) - 核心识别引擎
2. **VAD语音活动检测模型** (~200MB) - 检测有效语音
3. **标点符号恢复模型** (~500MB) - 添加标点符号


### 快速启动

1. **下载项目**
   ```bash
   # 如果是Git仓库
   git clone <repository_url>
   cd VoiceRecognizor
   ```

4. **下载模型 **
   
   ```bash
   # 下载所有模型
   python download_models.py --download all
   
   # 下载单个模型
   python download_models.py --download paraformer
   ```
   
3. **安装依赖**
   
   ```bash
   # 安装依赖
   pip install -r requirements.txt
   
   
   # 启动服务器
   python main.py
   ```
   
4. **访问系统**
   
   打开浏览器访问: http://127.0.0.1:8080

### 📋 模型管理命令

```bash
# 检查模型状态
python check_models.py

# 下载所有模型
python download_models.py --download all

# 下载单个模型
python download_models.py --download paraformer
python download_models.py --download vad  
python download_models.py --download punc

# 列出模型状态
python download_models.py --list
```

### 使用流程

1. **准备数据**
   - 准备音频文件 (.wav, .pcm, .mp3, .flac)
   - 准备对应的文本文件 (.txt)
   - 确保音频文件和文本文件名称匹配 (如: audio01.wav 对应 audio01.txt)

2. **开始评测**
   - 访问"开始评测"页面
   - 选择上传文件或指定本地目录
   - 设置任务名称 (可选)
   - 点击"开始评测"

3. **监控进度**
   - 实时查看处理进度
   - 查看当前处理阶段和剩余时间
   - 可随时取消任务

4. **查看结果**
   - 评测完成后查看汇总统计
   - 查看CER/WER分布图表
   - 查看详细的文件级别结果
   - 查看文本差异对比

5. **结果管理**
   - 导出评测结果 (JSON格式)
   - 查看历史评测记录
   - 删除不需要的会话

## API接口

### 主要接口

- `POST /api/upload-directory` - 上传文件夹进行评测
- `POST /api/start-evaluation` - 使用本地目录开始评测
- `GET /api/task-status/{session_id}` - 获取任务状态
- `GET /api/task-results/{session_id}` - 获取任务结果
- `GET /api/sessions` - 列出所有会话
- `DELETE /api/sessions/{session_id}` - 删除会话
- `GET /api/download-results/{session_id}` - 下载结果文件

### WebSocket

- `WS /ws` - 实时进度推送

## 评测指标说明

### CER (Character Error Rate)
字符错误率，计算公式：
```
CER = (插入字符数 + 删除字符数 + 替换字符数) / 原始字符总数
```

### WER (Word Error Rate)
词错误率，计算公式：
```
WER = (插入词数 + 删除词数 + 替换词数) / 原始词总数
```

### 相似度 (Similarity)
基于编辑距离的文本相似度：
```
相似度 = 1 - (编辑距离 / max(原始文本长度, 识别文本长度))
```

## 配置说明

主要配置项在 `backend/config.py` 中：

- **音频配置**: 支持的格式、采样率等
- **ASR配置**: Paraformer模型配置、设备选择
- **评测配置**: 启用的评测指标
- **Web配置**: 服务器地址、端口、上传限制

