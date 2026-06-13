# VoiceRecognizor

基于 FunASR Paraformer 的 TTS 合成质量评测平台，提供语音识别、文本比对、CER/WER/相似度统计和 Web 可视化展示。

模型权重、运行数据和本地配置不会随仓库提交。首次运行前需要按下面步骤下载模型。

## 功能概览

- 支持 WAV、PCM、MP3、FLAC 等常见音频格式。
- 支持上传音频和文本文件，或指定本地目录进行批量评测。
- 使用 Paraformer 进行语音识别，并结合 VAD、标点恢复模型提升识别结果可读性。
- 计算 CER、WER、相似度等指标，提供文件级明细和汇总统计。
- 通过 WebSocket 实时推送任务进度。
- 支持历史会话管理和 JSON 结果导出。

## 系统架构

```text
VoiceRecognizor/
|-- backend/                 # 后端 Python 模块
|   |-- __init__.py          # 模块初始化
|   |-- config.py            # 配置文件
|   |-- asr_engine.py        # 语音识别引擎
|   |-- evaluator.py         # 文本评测模块
|   |-- file_manager.py      # 文件管理模块
|   |-- task_processor.py    # 任务处理模块
|   `-- server.py            # Web 服务器
|-- frontend/                # 前端 Web 页面
|   |-- index.html           # 主页面
|   |-- style.css            # 样式文件
|   `-- script.js            # JavaScript 脚本
|-- examples/                # 示例音频和文本
|-- data/                    # 运行时上传目录，Git 忽略
|-- models/                  # 本地模型目录，Git 忽略
|-- results/                 # 评测结果目录，Git 忽略
|-- temp/                    # 临时目录，Git 忽略
|-- logs/                    # 日志目录，Git 忽略
|-- requirements.txt         # Python 依赖
`-- README.md                # 项目说明
```

## 环境要求

- Python 3.8+
- Windows / Linux / macOS
- 可选 CUDA 环境，用于 GPU 推理

需要下载的模型：

1. Paraformer 语音识别模型，约 1.2GB。
2. VAD 语音活动检测模型，约 200MB。
3. 标点符号恢复模型，约 500MB。

## 快速启动

```bash
git clone https://github.com/Allencc5658/VoiceRecognizor.git
cd VoiceRecognizor

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python download_models.py --download all
python main.py
```

默认访问地址：`http://127.0.0.1:8080`

Linux/macOS 激活虚拟环境：

```bash
source .venv/bin/activate
```

## 模型管理命令

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

## 使用流程

1. 准备音频文件和对应文本文件，文件名需要匹配，例如 `audio01.wav` 对应 `audio01.txt`。
2. 打开 Web 页面后选择上传文件，或指定本地目录。
3. 设置任务名称，启动评测任务。
4. 在页面中实时查看处理进度、当前阶段和剩余时间。
5. 评测完成后查看汇总统计、CER/WER 分布图表、文件级结果和文本差异。
6. 按需导出 JSON 结果，或在历史记录中管理已有会话。

## API 接口

- `POST /api/upload-directory`：上传文件夹进行评测。
- `POST /api/start-evaluation`：使用本地目录开始评测。
- `GET /api/task-status/{session_id}`：获取任务状态。
- `GET /api/task-results/{session_id}`：获取任务结果。
- `GET /api/sessions`：列出所有会话。
- `DELETE /api/sessions/{session_id}`：删除会话。
- `GET /api/download-results/{session_id}`：下载结果文件。
- `WS /ws`：实时进度推送。

## 评测指标说明

### CER

字符错误率，计算公式：

```text
CER = (插入字符数 + 删除字符数 + 替换字符数) / 原始字符总数
```

### WER

词错误率，计算公式：

```text
WER = (插入词数 + 删除词数 + 替换词数) / 原始词总数
```

### Similarity

基于编辑距离的文本相似度：

```text
相似度 = 1 - (编辑距离 / max(原始文本长度, 识别文本长度))
```

## 配置说明

主要配置项在 `backend/config.py` 中，也可以通过环境变量覆盖常用配置。可以复制 `.env.example` 为 `.env` 后按需修改。

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VOICE_RECOGNIZOR_HOST` | `127.0.0.1` | Web 服务监听地址 |
| `VOICE_RECOGNIZOR_PORT` | `8080` | Web 服务端口 |
| `VOICE_RECOGNIZOR_DEBUG` | `true` | 是否启用 reload/debug |
| `VOICE_RECOGNIZOR_DEVICE` | `cpu` | ASR 推理设备，可设为 `cuda` |
| `VOICE_RECOGNIZOR_USE_LOCAL_MODEL` | `true` | 是否优先使用 `models/` 下的本地模型 |
| `VOICE_RECOGNIZOR_MODELS_DIR` | `./models` | 模型目录 |
| `VOICE_RECOGNIZOR_CORS_ORIGINS` | `*` | 允许的 CORS 来源，多个用逗号分隔 |

## 开源发布说明

- 仓库不包含模型权重、运行结果、上传数据、日志或本地 `.env` 文件。
- `examples/` 中包含少量示例音频和文本，发布前请确认这些样例可以公开。
- `backend/tn/` 下包含文本标准化相关第三方代码和 `.fst` 资产，请在正式发布前复核许可证要求。
- 第三方组件和资产说明见 `THIRD_PARTY_NOTICES.md`。
- 发布前请根据你的开源策略补充 `LICENSE` 文件。
