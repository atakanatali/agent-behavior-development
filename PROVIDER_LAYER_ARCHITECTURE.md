# LLM Provider Layer Architecture

## Overview

The LLM Provider Layer is a unified interface for the ABD orchestration engine to interact with multiple LLM providers including Anthropic Claude, OpenAI, and any provider supported by LiteLLM.

**Location:** `/orchestify/providers/`

## Components

### 1. Base Classes and Data Models (`base.py`)

#### LLMMessage
```python
@dataclass
class LLMMessage:
    role: str  # 'system', 'user', 'assistant'
    content: str
```
Represents a single message in an LLM conversation.

#### LLMResponse
```python
@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_input: int
    tokens_output: int
    finish_reason: str
    raw_response: Any = None
```
Response from an LLM provider with token tracking and provider metadata.

#### TokenUsage
```python
@dataclass
class TokenUsage:
    total_input: int = 0
    total_output: int = 0
    total_cost_usd: float = 0.0
    call_count: int = 0
```
Tracks cumulative token usage and costs across API calls.

#### LLMProvider (Abstract Base Class)
```python
class LLMProvider(ABC):
    async def complete(messages, model=None, temperature=0.7, max_tokens=8192, 
                       tools=None, thinking=False) -> LLMResponse
    async def stream(messages, model=None, temperature=0.7, 
                     max_tokens=8192) -> AsyncIterator[str]
    
    @property
    def provider_type(self) -> str  # 'anthropic', 'openai', 'litellm'
    
    def supports_tools(self) -> bool
    def supports_thinking(self) -> bool
    def supports_code_execution(self) -> bool
    
    def get_usage(self) -> TokenUsage
    def reset_usage()
```

### 2. Claude Provider (`claude.py`)

**Class:** `ClaudeProvider(LLMProvider)`

**Capabilities:**
- Single completions and streaming
- Tool/function calling (supports_tools = True)
- Extended thinking for compatible models (supports_thinking = True)
- Vision capabilities (with image content)

**Key Features:**
- Environment variable substitution for API key (${VAR_NAME})
- Automatic cost calculation based on token pricing
- Extended thinking support for Claude models that support it
- Comprehensive error handling (RateLimitError, APIConnectionError, etc.)

**Pricing (Approximate):**
- Claude 3.5 Sonnet: $3/1M input, $15/1M output
- Claude 3.5 Haiku: $0.80/1M input, $4/1M output
- Claude 3 Opus: $15/1M input, $75/1M output

**Model Validation:**
- Validates model starts with "claude-"
- Thinking support detection based on model ID

### 3. OpenAI Provider (`openai_provider.py`)

**Class:** `OpenAIProvider(LLMProvider)`

**Capabilities:**
- Single completions and streaming
- Tool/function calling (supports_tools = True)
- Vision capabilities

**Key Features:**
- Environment variable substitution for API key
- Automatic cost calculation based on token pricing
- Support for custom base URLs (proxies, enterprise deployments)
- Tool calling via function_calling mechanism
- Stream context manager for proper resource management

**Pricing (Approximate):**
- GPT-4o: $5/1M input, $15/1M output
- GPT-4 Turbo: $10/1M input, $30/1M output
- GPT-4: $30/1M input, $60/1M output
- GPT-3.5 Turbo: $0.50/1M input, $1.50/1M output

**Model Validation:**
- Models typically start with "gpt-", "text-", or "code-"
- Flexible model matching for custom deployments

### 4. LiteLLM Provider (`litellm_provider.py`)

**Class:** `LiteLLMProvider(LLMProvider)`

**Capabilities:**
- Universal adapter for any LiteLLM-supported provider
- Tool/function calling (supports_tools = True)
- Extended thinking support (supports_thinking = True)
- Single completions and streaming

**Key Features:**
- Routes to any provider LiteLLM supports (Azure, Cohere, Replicate, etc.)
- Environment variable substitution
- Custom API endpoint support
- Fallback provider for unsupported backends
- Cost tracking via LiteLLM's built-in mechanisms

**Supported Backends:**
- Azure OpenAI
- Cohere
- Replicate
- Together AI
- Hugging Face
- Local models (via Ollama, Vllm, etc.)
- And more...

### 5. Provider Registry (`registry.py`)

**Class:** `ProviderRegistry`

**Key Methods:**
```python
def register(provider_id: str, provider: LLMProvider) -> None
    # Register a provider instance

def get(provider_id: str) -> LLMProvider
    # Get provider by ID

def get_for_agent(agent_id: str, agents_config: AgentsConfig) -> LLMProvider
    # Get provider configured for a specific agent

@classmethod
def from_config(providers_config: ProvidersConfig, 
                validate_connectivity: bool = False) -> ProviderRegistry
    # Create registry from config with auto-initialization

def list_providers() -> list[str]
    # Get all registered provider IDs

def get_total_usage() -> dict[str, TokenUsage]
    # Get cumulative usage for all providers

def get_usage_summary() -> dict[str, Any]
    # Get human-readable usage summary with aggregated metrics

def reset_all_usage() -> None
    # Reset usage metrics for all providers
```

**Features:**
- Auto-detection of provider type from config
- Provider initialization from ProviderConfig objects
- Error handling and validation
- Comprehensive usage tracking and reporting
- Support for health checks (optional)

## Configuration Integration

Providers integrate with the existing config system:

```python
# From orchestify/core/config.py
class ProviderConfig(BaseModel):
    type: str  # 'anthropic', 'openai', or 'litellm'
    api_key: str  # Supports ${ENV_VAR} substitution
    default_model: str
    max_tokens: int
    base_url: Optional[str] = None

class ProvidersConfig(BaseModel):
    providers: Dict[str, ProviderConfig]
```

**Example YAML Configuration:**
```yaml
providers:
  claude_main:
    type: anthropic
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-3-5-sonnet
    max_tokens: 8192
  
  openai_main:
    type: openai
    api_key: ${OPENAI_API_KEY}
    default_model: gpt-4o
    max_tokens: 8192
    
  azure:
    type: litellm
    api_key: ${AZURE_API_KEY}
    default_model: azure/gpt-4
    base_url: https://myorg.openai.azure.com
```

## Usage Examples

### Basic Usage

```python
from orchestify.providers import ProviderRegistry, LLMMessage
from orchestify.core.config import load_config
from pathlib import Path

# Load config and create registry
config = load_config(Path("config"))
registry = ProviderRegistry.from_config(config.providers)

# Get a provider
provider = registry.get("claude_main")

# Create a message
message = LLMMessage(role="user", content="Hello, Claude!")

# Get a completion
response = await provider.complete(
    messages=[message],
    temperature=0.7,
    max_tokens=1024
)

print(f"Response: {response.content}")
print(f"Tokens used: {response.tokens_input + response.tokens_output}")
```

### With Tool Calling

```python
# Define tools
tools = [
    {
        "name": "get_weather",
        "description": "Get weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
            },
            "required": ["location"],
        },
    }
]

# Get provider with tool support
if provider.supports_tools():
    response = await provider.complete(
        messages=[message],
        tools=tools
    )
```

### With Streaming

```python
# Stream a response
async for chunk in provider.stream(
    messages=[message],
    max_tokens=2048
):
    print(chunk, end="", flush=True)
```

### Usage Tracking

```python
# Get usage for a single provider
usage = provider.get_usage()
print(f"Total cost: ${usage.total_cost_usd:.2f}")
print(f"Calls made: {usage.call_count}")

# Get usage across all providers
summary = registry.get_usage_summary()
print(f"Total cost across all: ${summary['total']['cost_usd']:.2f}")

# Reset usage
registry.reset_all_usage()
```

## Architecture Benefits

1. **Unified Interface:** Single API for multiple LLM providers
2. **Extensibility:** Easy to add new providers by extending LLMProvider
3. **Cost Tracking:** Automatic token and cost tracking per provider
4. **Configuration-Driven:** Providers initialized from YAML config
5. **Error Handling:** Comprehensive exception handling and logging
6. **Type Safety:** Full type hints throughout
7. **Async/Await:** Native async support for all operations
8. **Streaming Support:** Token-efficient streaming for long responses
9. **Tool Support:** Unified tool/function calling interface
10. **Extended Thinking:** Extensible support for advanced model features

## Error Handling

All providers implement comprehensive error handling:

- **RateLimitError:** API rate limits exceeded
- **APIConnectionError:** Network connectivity issues
- **APIError:** General API failures
- **ValueError:** Invalid parameters or configuration
- **KeyError:** Provider or agent not found in registry

## Logging

All components use Python's standard logging:

```python
import logging

logger = logging.getLogger(__name__)
# Logs at DEBUG, INFO, WARNING, and ERROR levels
```

Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

1. Provider health checks and connection validation
2. Rate limit handling with exponential backoff
3. Request batching for cost optimization
4. Model compatibility matrix
5. Token estimation before making requests
6. Request/response caching layer
7. Cost forecasting and budget alerts
8. Provider failover and circuit breaking

