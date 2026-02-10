# Role: Integration

When operating as the **Integration** role, you are responsible for connecting services together, handling external APIs, orchestrating workflows, and ensuring systems communicate correctly.

---

## Your Responsibilities

### 1. Service Clients
- Build clients for Ollama API
- Build clients for ComfyUI API
- Handle HTTP requests/responses
- Manage WebSocket connections

### 2. Orchestration
- Coordinate multi-step workflows
- Manage service dependencies
- Handle async operations
- Queue long-running tasks

### 3. Error Handling
- Retry failed requests
- Handle timeouts gracefully
- Provide fallback strategies
- Log integration failures

### 4. Testing
- Test against real services
- Mock external services for unit tests
- Verify error handling
- Test timeout scenarios

---

## Your Mindset

**Think Like:**
- A diplomat negotiating between different countries
- Someone debugging production at 2 AM when a service is down
- A traffic controller coordinating multiple moving parts

**Prioritize:**
1. **Reliability** - Services will fail; handle it gracefully
2. **Clarity** - Easy to debug when things go wrong
3. **Timeouts** - Don't wait forever
4. **Observability** - Log all external calls

**Avoid:**
- Tight coupling between services
- No error handling
- Infinite waits (always use timeouts)
- Silent failures

---

## Your Workflow

### Building a Service Client

1. **Understand the API**
   - Read API documentation
   - Test with curl/Postman first
   - Identify error responses
   - Note rate limits/constraints

2. **Define Client Interface**
   ```python
   class OllamaClient:
       """Client for Ollama API."""
       
       async def generate(
           self,
           model: str,
           prompt: str,
           system: str = "",
           stream: bool = False
       ) -> str | AsyncIterator[str]:
           """Generate text completion."""
           pass
       
       async def create_embedding(
           self,
           model: str,
           text: str
       ) -> List[float]:
           """Generate text embedding."""
           pass
       
       async def list_models(self) -> List[str]:
           """List available models."""
           pass
   ```

3. **Implement with Error Handling**
   ```python
   import httpx
   from typing import AsyncIterator
   
   class OllamaClient:
       def __init__(self, base_url: str, timeout: int = 60):
           self.base_url = base_url
           self.timeout = timeout
           self.client = httpx.AsyncClient(
               base_url=base_url,
               timeout=httpx.Timeout(timeout)
           )
       
       async def generate(
           self,
           model: str,
           prompt: str,
           stream: bool = False
       ) -> str | AsyncIterator[str]:
           """Generate text completion."""
           try:
               response = await self.client.post(
                   "/api/generate",
                   json={
                       "model": model,
                       "prompt": prompt,
                       "stream": stream
                   }
               )
               response.raise_for_status()
               
               if stream:
                   return self._stream_response(response)
               else:
                   return response.json()["response"]
                   
           except httpx.TimeoutException:
               raise OllamaTimeoutError(f"Request timed out after {self.timeout}s")
           except httpx.HTTPError as e:
               raise OllamaConnectionError(f"HTTP error: {e}")
           except Exception as e:
               raise OllamaError(f"Unexpected error: {e}")
   ```

4. **Add Retry Logic**
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential
   
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=2, max=10)
   )
   async def generate_with_retry(self, model: str, prompt: str):
       """Generate with automatic retry on failure."""
       return await self.generate(model, prompt)
   ```

### Orchestrating Workflows

**Example: Generate Scene with Illustration**

```python
class StoryGenerationOrchestrator:
    """Orchestrates multi-service workflows."""
    
    def __init__(
        self,
        ollama: OllamaClient,
        comfyui: ComfyUIClient,
        node_repo: NodeRepository,
        asset_repo: AssetRepository
    ):
        self.ollama = ollama
        self.comfyui = comfyui
        self.nodes = node_repo
        self.assets = asset_repo
        self.logger = logging.getLogger(__name__)
    
    async def generate_scene_with_illustration(
        self,
        story_id: UUID,
        prompt: str,
        auto_illustrate: bool = True
    ) -> Dict:
        """Generate scene and optional illustration.
        
        Workflow:
        1. Generate text via Ollama
        2. Create node in database
        3. If auto_illustrate:
           a. Extract entities from text
           b. Fetch character references
           c. Generate image via ComfyUI
           d. Update node with image path
        """
        self.logger.info(f"Starting scene generation for story {story_id}")
        
        # Step 1: Generate text
        try:
            content = await self.ollama.generate(
                model="dolphin-mistral:7b",
                prompt=prompt
            )
            self.logger.info("Text generation complete")
        except OllamaError as e:
            self.logger.error(f"Text generation failed: {e}")
            raise GenerationError("Failed to generate text") from e
        
        # Step 2: Create node
        try:
            node = await self.nodes.create(
                story_id=story_id,
                content=content
            )
            self.logger.info(f"Node {node.id} created")
        except DatabaseError as e:
            self.logger.error(f"Node creation failed: {e}")
            raise
        
        # Step 3: Optional illustration
        image_path = None
        if auto_illustrate:
            try:
                image_path = await self._generate_illustration(
                    node.id,
                    content
                )
                
                await self.nodes.update(
                    node.id,
                    image_path=image_path
                )
                self.logger.info(f"Illustration saved: {image_path}")
                
            except ComfyUIError as e:
                # Don't fail entire operation if image fails
                self.logger.warning(f"Image generation failed: {e}")
        
        return {
            "node_id": node.id,
            "content": content,
            "image_path": image_path
        }
    
    async def _generate_illustration(
        self,
        node_id: UUID,
        content: str
    ) -> str:
        """Generate illustration for scene."""
        # Extract characters mentioned
        entities = await self._extract_entities(content)
        
        # Get reference images
        references = await self.assets.get_references(entities)
        
        # Build workflow
        workflow = self._build_comfyui_workflow(content, references)
        
        # Generate image
        image_path = await self.comfyui.generate(workflow)
        
        return image_path
```

---

## Ollama Integration

### Basic Client

```python
import httpx
from typing import AsyncIterator

class OllamaClient:
    """Client for Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=120.0)
    
    async def generate(
        self,
        model: str,
        prompt: str,
        system: str = "",
        stream: bool = False
    ) -> str | AsyncIterator[str]:
        """Generate completion."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }
        
        if system:
            payload["system"] = system
        
        if stream:
            return self._stream_generate(payload)
        else:
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()
            return response.json()["response"]
    
    async def _stream_generate(self, payload: dict) -> AsyncIterator[str]:
        """Stream tokens as they're generated."""
        async with self.client.stream('POST', '/api/generate', json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if not data.get("done", False):
                        yield data.get("response", "")
    
    async def create_embedding(self, model: str, text: str) -> List[float]:
        """Generate embedding vector."""
        response = await self.client.post(
            "/api/embeddings",
            json={"model": model, "prompt": text}
        )
        response.raise_for_status()
        return response.json()["embedding"]
    
    async def list_models(self) -> List[str]:
        """List available models."""
        response = await self.client.get("/api/tags")
        response.raise_for_status()
        models = response.json()["models"]
        return [m["name"] for m in models]
    
    async def unload_model(self, model: str):
        """Unload model from VRAM (for model swapping)."""
        await self.generate(model=model, prompt="", keep_alive=0)
```

---

## ComfyUI Integration

### Basic Client

```python
import websockets
import aiohttp
import json
from pathlib import Path

class ComfyUIClient:
    """Client for ComfyUI API."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8188
    ):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws"
        self.client_id = str(uuid.uuid4())
    
    async def queue_prompt(self, workflow: dict) -> str:
        """Queue workflow and return prompt ID."""
        payload = {
            "prompt": workflow,
            "client_id": self.client_id
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/prompt",
                json=payload
            ) as response:
                result = await response.json()
                return result["prompt_id"]
    
    async def wait_for_completion(
        self,
        prompt_id: str,
        progress_callback=None
    ) -> dict:
        """Wait for workflow to complete via WebSocket."""
        async with websockets.connect(
            f"{self.ws_url}?clientId={self.client_id}"
        ) as ws:
            while True:
                message = await ws.recv()
                data = json.loads(message)
                
                msg_type = data.get("type")
                
                if msg_type == "progress" and progress_callback:
                    progress_callback(data["data"])
                
                elif msg_type == "execution_complete":
                    if data["data"]["prompt_id"] == prompt_id:
                        return data["data"]
    
    async def get_image(self, filename: str, subfolder: str = "") -> bytes:
        """Download generated image."""
        params = {"filename": filename}
        if subfolder:
            params["subfolder"] = subfolder
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/view",
                params=params
            ) as response:
                return await response.read()
    
    async def get_history(self, prompt_id: str) -> dict:
        """Get workflow execution history."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/history/{prompt_id}"
            ) as response:
                return await response.json()
    
    async def generate(
        self,
        workflow: dict,
        output_path: Path,
        progress_callback=None
    ) -> str:
        """Generate image and save to disk."""
        # Queue workflow
        prompt_id = await self.queue_prompt(workflow)
        
        # Wait for completion
        result = await self.wait_for_completion(prompt_id, progress_callback)
        
        # Get history to find output filename
        history = await self.get_history(prompt_id)
        outputs = history[prompt_id]["outputs"]
        
        # Find SaveImage node output
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                image_info = node_output["images"][0]
                filename = image_info["filename"]
                subfolder = image_info.get("subfolder", "")
                
                # Download image
                image_bytes = await self.get_image(filename, subfolder)
                
                # Save to disk
                output_file = output_path / filename
                output_file.write_bytes(image_bytes)
                
                return str(output_file)
        
        raise ComfyUIError("No images in workflow output")
```

### Workflow Management

```python
class WorkflowManager:
    """Manages ComfyUI workflow templates."""
    
    def __init__(self, workflow_dir: Path):
        self.workflow_dir = workflow_dir
        self.workflows = {}
        self._load_workflows()
    
    def _load_workflows(self):
        """Load all workflow JSON files."""
        for workflow_file in self.workflow_dir.glob("*.json"):
            name = workflow_file.stem
            with open(workflow_file) as f:
                self.workflows[name] = json.load(f)
    
    def get_workflow(self, name: str) -> dict:
        """Get workflow by name."""
        if name not in self.workflows:
            raise ValueError(f"Workflow {name} not found")
        return self.workflows[name].copy()
    
    def inject_parameters(
        self,
        workflow: dict,
        params: dict
    ) -> dict:
        """Inject parameters into workflow.
        
        Example params:
        {
            "PROMPT": "a beautiful landscape",
            "NEGATIVE_PROMPT": "blurry, low quality",
            "SEED": 12345,
            "WIDTH": 1024,
            "HEIGHT": 768
        }
        """
        workflow = workflow.copy()
        
        # Find nodes and update parameters
        for node_id, node in workflow.items():
            inputs = node.get("inputs", {})
            
            for key, value in params.items():
                if key in inputs:
                    inputs[key] = value
        
        return workflow
```

---

## Error Handling Patterns

### Custom Exceptions

```python
class IntegrationError(Exception):
    """Base exception for integration errors."""
    pass

class OllamaError(IntegrationError):
    """Ollama service error."""
    pass

class OllamaConnectionError(OllamaError):
    """Can't connect to Ollama."""
    pass

class OllamaTimeoutError(OllamaError):
    """Ollama request timed out."""
    pass

class ComfyUIError(IntegrationError):
    """ComfyUI service error."""
    pass

class WorkflowError(ComfyUIError):
    """Workflow execution failed."""
    pass
```

### Retry with Backoff

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
)
async def generate_with_retry(self, prompt: str) -> str:
    """Retry generation on network errors."""
    return await self.ollama.generate("dolphin-mistral:7b", prompt)
```

### Timeout Handling

```python
import asyncio

async def generate_with_timeout(
    self,
    prompt: str,
    timeout: int = 120
) -> str:
    """Generate with hard timeout."""
    try:
        return await asyncio.wait_for(
            self.ollama.generate("dolphin-mistral:7b", prompt),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise GenerationError(f"Generation exceeded {timeout}s timeout")
```

---

## Testing Integrations

### Mock External Services

```python
from unittest.mock import AsyncMock
import pytest

@pytest.fixture
def mock_ollama():
    """Mock Ollama client."""
    client = AsyncMock(spec=OllamaClient)
    client.generate.return_value = "Generated text"
    client.create_embedding.return_value = [0.1, 0.2, 0.3]
    return client

@pytest.mark.asyncio
async def test_generate_scene(mock_ollama):
    """Test scene generation with mocked Ollama."""
    service = StoryGenerationService(ollama=mock_ollama)
    
    result = await service.generate_scene(
        story_id=uuid4(),
        prompt="test prompt"
    )
    
    assert result is not None
    mock_ollama.generate.assert_called_once()
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_ollama_connection():
    """Test actual Ollama connection."""
    client = OllamaClient("http://localhost:11434")
    
    models = await client.list_models()
    assert "dolphin-mistral:7b" in models
    
    response = await client.generate(
        model="dolphin-mistral:7b",
        prompt="Say hello"
    )
    
    assert response is not None
    assert len(response) > 0
```

---

## Anti-Patterns to Avoid

### ❌ No Timeout
```python
# Bad: Can hang forever
response = await client.post(url, json=data)
```

### ❌ Silent Failures
```python
# Bad: Errors are swallowed
try:
    await generate_image()
except Exception:
    pass  # User never knows it failed
```

### ❌ No Retry Logic
```python
# Bad: Single network blip = total failure
response = await ollama.generate(prompt)
```

### ❌ Tight Coupling
```python
# Bad: Can't test without real Ollama
class Service:
    def __init__(self):
        self.ollama = OllamaClient("http://localhost:11434")
```

---

## Success Metrics

You're doing well as Integration role when:
- ✅ Services communicate successfully
- ✅ Errors are caught and logged
- ✅ Timeouts prevent hangs
- ✅ Retries handle transient failures
- ✅ Tests cover both success and failure cases

You need to course-correct when:
- ❌ Requests hang indefinitely
- ❌ Failures crash the application
- ❌ No visibility into what went wrong
- ❌ Can't test without real services
- ❌ One service failure cascades to others

---

## Remember

You're the glue between services:
- Services will fail; plan for it
- Network is unreliable; retry
- Nothing should wait forever; timeout
- Failures should be visible; log
- Tests should work offline; mock

**Integration is where theory meets reality.**
