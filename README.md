# VoiceRecognizor

基于 FunASR Paraformer 的 TTS 合成质量评测平台，提供语音识别、文本比对、CER/WER/相似度统计和 Web 可视化展示。

> 模型权重、运行数据和本地配置不会随仓库提交。首次运行前需要按下面步骤下载模型。

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
├── data/                   # 运行时上传目录，Git忽略
├── models/                 # 本地模型目录，Git忽略
├── results/                # 评测结果目录，Git忽略
├── temp/                   # 临时目录，Git忽略
├── logs/                   # 日志目录，Git忽略
├── requirements.txt        # Python依赖
└── README.md              # 项目说明
```

## 安装和使用

### 环境要求

- Python 3.8+
- Windows / Linux / macOS
- 支持的音频格式: WAV, PCM, MP3, FLAC


#### 需要下载的模型：
1. **Paraformer语音识别模型** (~1.2GB) - 核心识别引擎
2. **VAD语音活动检测模型** (~200MB) - 检测有效语音
3. **标点符号恢复模型** (~500MB) - 添加标点符号


### 快速启动

```bash
git clone https://github.com/Allencc5658/VoiceRecognizor.git
cd VoiceRecognizor

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python download_models.py --download all
python main.py
```

默认访问地址: `http://127.0.0.1:8080`

Linux/macOS 激活虚拟环境:

```bash
source .venv/bin/activate
```

### 📋 模型管理命令

```bash
# 检查模型状态
python download_models.py --check

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

也可以通过环境变量覆盖常用配置：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VOICE_RECOGNIZOR_HOST` | `127.0.0.1` | Web 服务监听地址 |
| `VOICE_RECOGNIZOR_PORT` | `8080` | Web 服务端口 |
| `VOICE_RECOGNIZOR_DEBUG` | `true` | 是否启用 reload/debug |
| `VOICE_RECOGNIZOR_DEVICE` | `cpu` | ASR 推理设备，可设为 `cuda` |
| `VOICE_RECOGNIZOR_USE_LOCAL_MODEL` | `true` | 是否优先使用 `models/` 下的本地模型 |
| `VOICE_RECOGNIZOR_MODELS_DIR` | `./models` | 模型目录 |
| `VOICE_RECOGNIZOR_CORS_ORIGINS` | `*` | 允许的 CORS 来源，多个用逗号分隔 |

## 开源说明

- 仓库不包含模型权重、运行结果、上传数据、日志或本地 `.env` 文件。
- `examples/` 中包含少量示例音频和文本，发布前请确认这些样例可以公开。
- `backend/tn/` 下包含文本标准化相关第三方代码和 `.fst` 资产，请在正式发布前复核许可证要求。

