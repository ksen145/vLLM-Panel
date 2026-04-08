# vLLM Panel

Multiplatform management UI for vLLM with OpenAI-compatible API.

## Quick Start

### One-line install and run

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/ksen145/vLLM-Panel/main/run.sh | bash
```

**Windows (PowerShell):**
```powershell
curl -sSL https://raw.githubusercontent.com/ksen145/vLLM-Panel/main/run.bat -o run.bat && run.bat
```

The script clones the repo, creates a virtual environment, installs dependencies, and starts the server.

### Manual install

```bash
git clone https://github.com/ksen145/vLLM-Panel.git
cd vLLM-Panel
pip install -r requirements.txt
pip install vllm        # Linux/Windows
pip install mlx-lm      # macOS (Apple Silicon)
python main.py
```

Open: `http://localhost:8500`

## Agent Integration

Use the OpenAI Python SDK or any compatible client:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8001/v1", api_key="not-needed")

response = client.chat.completions.create(
    model="your-model",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

### Tool Calling

Tool calling works natively through vLLM's OpenAI-compatible API:

```python
response = client.chat.completions.create(
    model="your-model",
    messages=[{"role": "user", "content": "What is the weather in London?"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"]
            }
        }
    }]
)
print(response.choices[0].message.tool_calls)
```

## Pages

| Page | Description |
|------|-------------|
| **Home** | Overview, quick links, platform info |
| **Server** | Configure and launch vLLM, view logs |
| **Chat** | Chat with model, test tool calling, streaming |
| **Models** | View cached models, launch, delete |
| **Search** | Search and download models from HuggingFace |
| **Status** | Real-time CPU, GPU, memory metrics |

## API Endpoints

### Panel API (:8500)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/info` | Panel info |
| POST | `/api/server/start` | Start vLLM server |
| POST | `/api/server/stop` | Stop vLLM server |
| GET | `/api/server/status` | Server status |
| GET | `/api/server/logs` | Server logs |
| POST | `/api/chat/completions` | Proxy to vLLM chat |
| POST | `/api/generate` | Proxy to vLLM completions |
| GET | `/api/models/local` | Cached models |
| GET | `/api/models/search` | Search HuggingFace |
| POST | `/api/models/download` | Download model |
| DELETE | `/api/models/{model}` | Delete model |
| GET | `/api/metrics` | System metrics |

### vLLM API (:8001)

Full OpenAI-compatible API at `http://localhost:8001/v1`:

- `GET /v1/models` - List models
- `POST /v1/chat/completions` - Chat with tool calling support
- `POST /v1/completions` - Text completions
- `POST /v1/embeddings` - Embeddings

## Project Structure

```
vLLM Panel/
├── main.py                  # FastAPI backend (Panel)
├── requirements.txt         # Dependencies
├── vllm-panel.bat           # Windows launcher
├── vllm-panel-linux.sh      # Linux launcher
├── vllm-panel-macos.sh      # macOS launcher
├── static/
│   ├── index.html           # SPA
│   ├── css/style.css
│   └── js/app.js
└── README.md
```

## License

MIT
