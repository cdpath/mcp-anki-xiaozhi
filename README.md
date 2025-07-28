# Xiaozhi Anki MCP

## Quick Start | 快速开始

1. Install dependencies | 安装依赖:

```bash
uv sync
```

2. Set up environment variables | 设置环境变量:

```bash
export MCP_ENDPOINT=<your_mcp_endpoint>
```

3. Run the Anki MCP example | 运行Anki MCP示例:

```bash
uv run mcp_pipe.py anki.py
```

## Project Structure | 项目结构

- `mcp_pipe.py`: Main communication pipe that handles WebSocket connections and process management | 处理WebSocket连接和进程管理的主通信管道
- `anki.py`: MCP tool implementation for communicating with AnkiConnect to control AnkiDesktop | 用于与AnkiConnect通信以控制AnkiDesktop的MCP工具实现
- `pyproject.toml`: Project configuration and dependencies | 项目配置和依赖
- `uv.lock`: Lock file for reproducible dependency resolution | 依赖解析锁定文件
# llm.txt
