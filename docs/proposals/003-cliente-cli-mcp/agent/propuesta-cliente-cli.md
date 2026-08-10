# Propuesta: Cliente CLI MCP para VoxelQuest

**Fecha:** 2026-08-09
**Estado:** Propuesta
**Alcance:** Stack Python. No modifica servidor ni contrato MCP. Añade un cliente standalone `vq` con dos modos: comandos deterministas (Typer) y lenguaje natural (LLM configurable).
**Resumen:** Un binario `vq` que unifica los 11 scripts dispersos de `core/python/scripts/`, ofrece subcomandos Typer autogenerados desde `definitions.json`, y añade un modo `vq chat` que traduce lenguaje natural a tools MCP mediante un proveedor LLM OpenAI-compatible configurable en runtime (Ollama Local, Ollama Cloud, o cualquier endpoint custom).

---

## 1. Motivación

### 1.1 Situación actual

El proyecto ya expone MCP correctamente:

| Componente | Archivo | Estado |
|------------|---------|--------|
| Servidor MCP (Python) | `core/python/server/main.py:74` (`POST /mcp`) | ✅ |
| Adaptador stdio (opencode) | `core/python/mcp-client.py` (42 líneas) | ✅ |
| Contrato de tools | `core/shared/tools/definitions.json` (769 líneas, ~55 tools, 12 categorías) | ✅ |
| Scripts de cliente | `core/python/scripts/` (11 scripts: 7 construcción + 4 comportamiento) | ⚠ dispersos, sin interfaz unificada |

**Lo que falta:** un cliente standalone que no requiera opencode.

### 1.2 Problemas de los scripts actuales

- Cada script (`chase.py:13`, `build_house.py:18`) reimplementa su propio `mcp()` HTTP con `urllib`.
- Sin `--help` coherente, sin descubribilidad, sin validación de argumentos.
- Nuevas tools (propuesta 002) requerirían escribir más scripts ad hoc.
- Un agente externo que quiera usar el juego por MCP sin opencode no tiene punto de entrada.

### 1.3 Objetivos

1. **Un binario `vq`** con subcomandos Typer para todas las tools MCP.
2. **`vq chat`** que traduce lenguaje natural a tools MCP usando un LLM configurable.
3. **Recetas** (`vq build house`, `vq ai chase`) que reemplazan los 11 scripts.
4. **Sin tocar el servidor**: el contrato MCP ya está listo; solo añadimos cliente.
5. **Provider-agnostic**: Ollama Local, Ollama Cloud, o cualquier endpoint OpenAI-compatible.

---

## 2. Arquitectura

### 2.1 Estructura de carpetas

```
core/python/
├── cli/                        # NUEVO: cliente standalone
│   ├── vq.py                   # entrypoint Typer principal
│   ├── client.py               # POST /mcp reutilizable (reemplaza mcp() de chase.py/build_house.py)
│   ├── commands/
│   │   ├── player.py           # vq player list|move|attack|look|teleport
│   │   ├── block.py            # vq block place|break|get|fill|clear
│   │   ├── build.py            # vq build house|castle|maze|cathedral|village|fortress|pyramid
│   │   ├── object.py           # vq object create|move|destroy  (propuesta 002)
│   │   ├── ai.py               # vq ai chase|evade|evade-chase|follow
│   │   ├── bt.py               # vq bt load|status|stop
│   │   ├── world.py            # vq world info|view|top-down
│   │   └── chat.py             # vq chat (modo natural)
│   ├── recipes/                # construcciones complejas (secuencias de apply_blocks)
│   │   ├── house.py            # extraído de build_house.py
│   │   ├── castle.py
│   │   ├── fortress.py
│   │   ├── maze.py
│   │   ├── pyramid.py
│   │   ├── village.py
│   │   └── cathedral.py
│   ├── llm/                    # proveedores LLM (OpenAI-compatible)
│   │   ├── base.py             # Protocol LLMProvider
│   │   ├── openai_compat.py    # Ollama Local / Ollama Cloud / Custom
│   │   └── registry.py         # Resuelve provider por --provider o config
│   └── tests/
│       ├── test_client.py
│       ├── test_commands.py
│       └── test_chat.py        # mock LLM
├── scripts/                    # MANTENER durante transición (delegan a cli/)
├── server/                     # NO TOCAR
├── mcp-client.py               # NO TOCAR (adaptador stdio opencode)
└── pyproject.toml              # AMPLIAR: [cli], [llm] optional-dependencies
```

### 2.2 Binario `vq`

Entryoint Typer con grupos de subcomandos:

```python
# cli/vq.py (esquema)
import typer
from cli.commands import player, block, build, object, ai, bt, world, chat

app = typer.Typer(help="VoxelQuest CLI — controla el mundo voxel desde terminal")
app.add_typer(player.app, name="player")
app.add_typer(block.app, name="block")
app.add_typer(build.app, name="build")
app.add_typer(object.app, name="object")
app.add_typer(ai.app, name="ai")
app.add_typer(bt.app, name="bt")
app.add_typer(world.app, name="world")
app.add_typer(chat.app, name="chat")

if __name__ == "__main__":
    app()
```

Instalación:
```bash
cd core/python
uv pip install -e ".[cli]"        # solo comandos
uv pip install -e ".[cli,llm]"    # comandos + chat natural
```

Entry point en `pyproject.toml`:
```toml
[project.scripts]
vq = "cli.vq:app"
```

### 2.3 `client.py` — núcleo reutilizable

Reemplaza las funciones `mcp()` duplicadas en `chase.py:13`, `build_house.py:18`, y los 9 scripts restantes.

```python
# cli/client.py (esquema)
import json, urllib.request
from typing import Any

DEFAULT_URL = "http://localhost:9000/mcp"
_rpc_id = 0

class McpClient:
    def __init__(self, url: str = DEFAULT_URL, timeout: int = 30):
        self.url = url
        self.timeout = timeout

    def call(self, tool: str, args: dict | None = None) -> dict:
        global _rpc_id
        _rpc_id += 1
        body = {
            "jsonrpc": "2.0", "id": _rpc_id,
            "method": "tools/call",
            "params": {"name": tool, "arguments": args or {}}
        }
        req = urllib.request.Request(
            self.url, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            resp = json.loads(r.read().decode())
            if "error" in resp:
                raise McpError(resp["error"])
            content = resp.get("content", [])
            if content and isinstance(content[0], dict) and "text" in content[0]:
                return json.loads(content[0]["text"])
            return resp.get("result", {})

    def list_tools(self) -> list[dict]:
        global _rpc_id
        _rpc_id += 1
        body = {"jsonrpc": "2.0", "id": _rpc_id, "method": "tools/list"}
        req = urllib.request.Request(
            self.url, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            resp = json.loads(r.read().decode())
            return resp.get("result", {}).get("tools", [])
```

Todos los subcomandos y `vq chat` usan `McpClient`. Sin dependencias nuevas (stdlib + opcionalmente `openai`).

### 2.4 Generación dinámica de subcomandos

Los subcomandos Typer se generan desde `tools/list` al arrancar `vq`, no se hardcodean. Esto significa que cuando se añadan las 15 tools de la propuesta 002, aparecen automáticamente como subcomandos sin tocar `vq`.

```python
# cli/commands/player.py (ejemplo)
import typer
from cli.client import McpClient

app = typer.Typer(help="Gestión de jugadores")
client = McpClient()

@app.command("list")
def list_players():
    """Listar todos los jugadores."""
    result = client.call("list_players")
    typer.echo(result)

@app.command("move")
def move_player(
    player_id: int = typer.Argument(...),
    x: float = typer.Argument(...),
    y: float = typer.Argument(0.0),
    z: float = typer.Argument(...),
):
    """Teletransportar jugador a (x,y,z)."""
    result = client.call("set_player_position",
                          {"player_id": player_id, "x": x, "y": y, "z": z})
    typer.echo(result)
```

---

## 3. Modo comandos (`vq <comando>`)

### 3.1 Subcomandos por categoría

Mapeo directo desde las categorías de `definitions.json`:

| Categoría | Subcomando | Ejemplos |
|-----------|------------|----------|
| `player` | `vq player` | `list`, `move`, `state`, `attack`, `look`, `teleport` |
| `world` | `vq block` | `place`, `break`, `get`, `fill`, `clear` |
| `building` | `vq build` | `house`, `castle`, `maze`, `cathedral`, `village`, `fortress`, `pyramid` |
| `objects` (propuesta 002) | `vq object` | `create`, `move`, `destroy`, `list` |
| `bt` | `vq bt` | `load`, `status`, `stop` |
| `vision` | `vq world` | `info`, `view`, `top-down`, `nearby` |
| `navigation` | `vq ai` | `chase`, `evade`, `evade-chase`, `follow` (bucles) |
| `config` | `vq config` | `get`, `set-approval` |
| `inventory` | `vq inventory` | `add`, `select`, `list` |
| `combat` | `vq combat` | `attack`, `kill-all-monsters` |
| `avatar` | `vq avatar` | `create`, `walk`, `clear`, `list` |
| `training` | `vq training` | `start`, `stop` |

### 3.2 Recetas compuestas

Las 7 recetas de construcción se implementan como funciones importables en `recipes/`:

```python
# cli/recipes/house.py (esquema, extraído de build_house.py)
from cli.client import McpClient

def build_house(client: McpClient, cx: int = 10, cz: int = 8, clear: bool = False):
    """Construye una casa habitable cerca del spawn."""
    if clear:
        clear_site(client, cx, cz)
    blocks = compute_house_blocks(cx, cz)
    # Enviar en lotes (igual que build_house.py:150)
    BATCH = 400
    for i in range(0, len(blocks), BATCH):
        client.call("apply_blocks", {"blocks": blocks[i:i+BATCH]}, timeout=120)
    return {"blocks_placed": len(blocks)}
```

Los subcomandos `vq build <receta>` son wrappers Typer que llaman a estas funciones.

### 3.3 Bucles de comportamiento (`vq ai`)

Los 4 scripts de IA (`chase.py`, `evade.py`, `evade_chase.py`, `follow_p1_distance.py`) se convierten en subcomandos que mantienen su bucle de control:

```python
# cli/commands/ai.py (esquema)
@app.command("chase")
def chase(
    target_id: int = typer.Option(1, "--target", "-t"),
    iterations: int = typer.Option(40, "--iters", "-n"),
):
    """Persigue al jugador objetivo usando gamepad virtual."""
    # Mismo bucle que chase.py:89-109
    client = McpClient()
    if not ensure_gamepad(client, 2):
        raise typer.Exit(1)
    for i in range(iterations):
        # ... lógica de chase.py
        time.sleep(0.15)
```

---

## 4. Modo lenguaje natural (`vq chat`)

### 4.1 Diseño provider-agnostic

**Sin provider por defecto.** El usuario debe elegir explícitamente para evitar sorpresas (p. ej. gastar Ollama Cloud sin saberlo).

```bash
vq chat --provider ollama-local --model qwen2.5-coder:7b
vq chat --provider ollama-cloud --model qwen3.5:9b
vq chat --provider custom --base-url https://api.deepseek.com/v1 --model deepseek-chat --api-key $DEEPSEEK_KEY
```

O vía `~/.vq/config.toml` (persiste la elección):
```toml
[llm]
provider = "ollama_local"   # obligatorio: ollama_local | ollama_cloud | custom
model = "qwen2.5-coder:7b"
base_url = "http://localhost:11434/v1"
# api_key = "..."  # solo ollama_cloud / custom
```

### 4.2 Proveedores soportados

| Provider | Acceso | API key | Coste | Latencia tool-use |
|----------|-------|---------|-------|---------------------|
| **Ollama Local** | `http://localhost:11434/v1` | No | 0€ | 5-15s CPU, 1-3s GPU |
| **Ollama Cloud** | Endpoint cloud | Requerida | Por uso | ~1-3s |
| **Custom** | Cualquier OpenAI-compatible | Según endpoint | Según proveedor | Variable |

Modelos locales con tool-use verificados (via `ollama show <model> | grep tools`):
- `qwen2.5-coder:7b`, `qwen3:8b`, `qwen3.5:9b`, `llama3.2`, `deepseek-r1:8b`, `phi3.5`

### 4.3 Arquitectura LLM

Un único SDK: `openai>=1.30.0` (funciona con cualquier endpoint OpenAI-compatible).

```
cli/llm/
├── base.py           # Protocol LLMProvider
├── openai_compat.py  # Implementa los 3 providers vía openai SDK
└── registry.py       # Resuelve provider por --provider o config.toml
```

```python
# cli/llm/base.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall]

class LLMProvider(Protocol):
    def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse: ...
```

```python
# cli/llm/openai_compat.py (esquema)
from openai import OpenAI
from cli.llm.base import LLMProvider, LLMResponse, ToolCall
import json

class OpenAICompatProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, tools=tools
        )
        msg = resp.choices[0].message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id, name=tc.function.name,
                    arguments=json.loads(tc.function.arguments)
                ))
        return LLMResponse(content=msg.content or "", tool_calls=tool_calls)
```

### 4.4 Pipeline `vq chat`

```
1. Al iniciar: GET tools/list al servidor del juego → catálogo de tools
2. Bucle REPL:
   a. Usuario escribe prompt en español/inglés
   b. Construir messages: [system_prompt_con_tools, user_prompt]
   c. Llamar a LLM vía OpenAI-compatible /v1/chat/completions con tools
   d. LLM responde con tool_calls (o texto)
   e. Si tool_calls:
      - --dry-run: mostrar plan y pedir confirmación
      - --confirm + tool destructiva: pedir confirmación
      - Ejecutar cada tool_call: POST /mcp tools/call
      - Enviar resultados de vuelta al LLM como tool role
      - LLM genera respuesta natural legible
   f. Mostrar respuesta
3. Historial: ~/.vq/chat_history.jsonl (sesión persistente)
```

### 4.5 Prompt del sistema

```
Eres un asistente que controla un mundo voxel (VoxelQuest).
Tienes estas herramientas disponibles:
[catálogo tools/list con descripción y inputSchema]

Reglas:
- Interpreta intenciones en español o inglés.
- Para construcciones complejas, usa recetas compuestas (build_house, build_castle...)
  en vez de llamadas individuales a place_block.
- Si la intención es ambigua, pregunta antes de actuar.
- Tools destructivas (break_block, destroy_object, kill_all_monsters)
  requieren confirmación del usuario.
- Responde en el idioma del usuario.
```

### 4.6 Tools virtuales (recetas como tools para el LLM)

Las recetas (`recipes/house.py`, `recipes/castle.py`, ...) se exponen al LLM como "tools virtuales" con su schema. Esto reduce tokens y errores:

```python
# En vq chat, al construir el catálogo de tools para el LLM:
virtual_tools = [
    {
        "type": "function",
        "function": {
            "name": "build_house",
            "description": "Construye una casa en (cx, cz). Usa apply_blocks por lotes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cx": {"type": "integer", "description": "Centro X"},
                    "cz": {"type": "integer", "description": "Centro Z"},
                    "clear": {"type": "boolean", "description": "Limpiar sitio antes"}
                },
                "required": ["cx", "cz"]
            }
        }
    },
    # ... build_castle, build_maze, etc.
]
```

Cuando el LLM llama `build_house`, el CLI ejecuta `recipes/house.py:build_house()` en lugar de 50 `place_block` individuales.

### 4.7 Flags de seguridad

```bash
vq chat --dry-run                # muestra plan antes de ejecutar
vq chat --confirm                # pide confirmación para tools destructivas
vq chat --auto                    # ejecuta sin confirmación (peligroso)
```

Tools destructivas se marcan en `definitions.json` con un campo opcional `"destructive": true` (extensión al contrato, no rompe nada). En la fase 1 se mantiene una lista hardcodeada: `break_block`, `clear_area`, `destroy_object`, `kill_all_monsters`, `avatars_clear`.

---

## 5. Migración de scripts existentes

### 5.1 Estrategia

Los 11 scripts en `core/python/scripts/` se migran a `cli/`:

| Script actual | Destino | Subcomando |
|---------------|---------|------------|
| `build_house.py` | `cli/recipes/house.py` + `cli/commands/build.py` | `vq build house` |
| `build_castle.py` | `cli/recipes/castle.py` + `cli/commands/build.py` | `vq build castle` |
| `build_fortress.py` | `cli/recipes/fortress.py` | `vq build fortress` |
| `build_maze.py` | `cli/recipes/maze.py` | `vq build maze` |
| `build_pyramid.py` | `cli/recipes/pyramid.py` | `vq build pyramid` |
| `build_village.py` | `cli/recipes/village.py` | `vq build village` |
| `build_gothic_cathedral.py` | `cli/recipes/cathedral.py` | `vq build cathedral` |
| `chase.py` | `cli/commands/ai.py` | `vq ai chase` |
| `evade.py` | `cli/commands/ai.py` | `vq ai evade` |
| `evade_chase.py` | `cli/commands/ai.py` | `vq ai evade-chase` |
| `follow_p1_distance.py` | `cli/commands/ai.py` | `vq ai follow` |

### 5.2 Transición

Los scripts originales se mantienen durante una versión como wrappers:

```python
# scripts/build_house.py (versión transición)
"""Wrapper: python3 scripts/build_house.py → vq build house"""
import subprocess, sys
subprocess.run([sys.executable, "-m", "cli.vq", "build", "house"] + sys.argv[1:])
```

Esto permite que flujos existentes sigan funcionando mientras los usuarios migran a `vq`.

### 5.3 `update_changelog.py`

Este script (`scripts/update_changelog.py`) es tooling de desarrollo, no gameplay. **Se mantiene en `scripts/`** sin migrar.

---

## 6. Configuración

### 6.1 `~/.vq/config.toml`

```toml
[server]
url = "http://localhost:9000/mcp"
timeout = 30

[llm]
provider = "ollama_local"   # ollama_local | ollama_cloud | custom
model = "qwen2.5-coder:7b"
base_url = "http://localhost:11434/v1"
# api_key = "..."  # solo ollama_cloud / custom

[chat]
dry_run = false
confirm = true
history_file = "~/.vq/chat_history.jsonl"
```

### 6.2 Variables de entorno (override)

```bash
VQ_SERVER_URL=http://localhost:9001/mcp
VQ_LLM_PROVIDER=ollama_cloud
VQ_LLM_MODEL=qwen3.5:9b
VQ_LLM_API_KEY=sk-...
VQ_CHAT_CONFIRM=false
```

### 6.3 Resolución de configuración

Prioridad (mayor a menor):
1. Flags CLI (`--provider`, `--model`, ...)
2. Variables de entorno (`VQ_*`)
3. `~/.vq/config.toml`
4. Defaults del código

---

## 7. Dependencias

### 7.1 Añadir a `pyproject.toml`

```toml
[project.optional-dependencies]
cli = [
    "typer>=0.12.0",      # CLI framework
]
llm = [
    "openai>=1.30.0",     # SDK OpenAI-compatible (sirve para Ollama Local/Cloud y custom)
]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "mcp>=1.0.0",
    "typer>=0.12.0",
    "openai>=1.30.0",
]
```

### 7.2 Instalación modular

```bash
uv pip install -e ".[cli]"           # solo comandos (Typer)
uv pip install -e ".[cli,llm]"       # comandos + chat natural
uv pip install -e ".[dev,cli,llm]"  # desarrollo completo
```

### 7.3 Entry point

```toml
[project.scripts]
vq = "cli.vq:app"
```

---

## 8. Sinergias con otras propuestas

### 8.1 Propuesta 002 (objetos móviles)

Las 15 tools nuevas de la propuesta 002 aparecen automáticamente como subcomandos `vq object *` porque se generan dinámicamente desde `tools/list`. Sin tocar código del CLI.

### 8.2 opencode

`opencode.json` sigue apuntando a `mcp-client.py` (adaptador stdio). **No hay conflicto**: opencode y `vq` son clientes paralelos del mismo servidor MCP.

### 8.3 Recetas como tools virtuales

`vq chat` puede invocar `vq build house` como "tool virtual" → menos tokens, menos errores, menos latencia. El LLM ve `build_house` como una sola tool con schema simple, no 50 `place_block`.

---

## 9. Diferencias vs. opencode

| Aspecto | opencode | `vq` |
|---------|---------|-------|
| Requiere TUI/editor | Sí | No (terminal simple) |
| Configurable por juego | No | Sí (prompts, recetas, reglas) |
| Recetas compuestas | No (solo tools atómicas) | Sí (`vq build house`) |
| Historial del juego | No | Sí (`~/.vq/chat_history.jsonl`) |
| Dry-run / confirmación | Limitado | Nativo |
| Provider LLM | El de opencode | Cualquier OpenAI-compatible |
| Descubribilidad (`--help`) | No | Sí (Typer autogenera) |
| Sin LLM (solo comandos) | No | Sí (`vq player list` sin LLM) |

---

## 10. Decisión de diseño: por qué OpenAI-compatible y no SDKs nativos

- **Un solo SDK** (`openai`) funciona con los 3 providers (Ollama Local, Ollama Cloud, custom).
- **No requiere `anthropic` SDK**: evita dependencia adicional.
- **Estándar**: Ollama expone `/v1/chat/completions` compatible con OpenAI.
- **Futuro**: cualquier proveedor nuevo (DeepSeek, Mistral, Groq...) que soporte OpenAI-compatible se añade con `--provider custom --base-url ...` sin tocar código.

---

## 11. Fases de implementación

Ver `plan-ejecucion.md` para detalle. Resumen:

| Fase | Entrega | Horas |
|------|---------|-------|
| 1 | Setup Typer + `client.py` + tests base | 2 |
| 2 | Subcomandos player/block/world/bt (generados desde definitions.json) | 2 |
| 3 | Migración 7 scripts de construcción a recipes/ | 3 |
| 4 | Migración 4 scripts de comportamiento a `ai.py` | 2 |
| 5 | Cliente LLM provider-agnostic + config | 3 |
| 6 | `vq chat`: REPL + prompt engineering + dry-run + confirm | 5 |
| 7 | Tests + documentación | 3 |

**Total:** ~20h

---

## 12. Riesgos y mitigaciones

| Riesgo | Prob | Impacto | Mitigación |
|--------|------|---------|------------|
| Modelos locales 7-9B fallan en tool-use complejo | Med | Med | Prompt few-shot; `--provider ollama-cloud` como fallback |
| Sin provider por defecto frusta al usuario | Med | Bajo | Mensaje claro al arrancar sin `--provider`; `~/.vq/config.toml` persiste |
| Latencia 5-15s en CPU | Med | Med | Spinner + streaming; documentar requisito GPU |
| Tool-use ambiguo elige tool equivocada | Med | Alto | `--dry-run` recomendado; validar args antes de enviar |
| Migración de scripts rompe flujos existentes | Bajo | Med | Scripts viejos se mantienen como wrappers durante transición |
| Typer añade dependencia | Bajo | Bajo | ~200KB; `click` ya está en `.venv` |
| `openai` SDK pesa | Bajo | Bajo | Opcional (grupo `[llm]`); solo si se usa `vq chat` |

---

## 13. Criterios de éxito

- [ ] `vq --help` muestra todos los subcomandos disponibles.
- [ ] `vq player list` funciona sin LLM, sin API keys, sin opencode.
- [ ] `vq build house 10 8` produce la misma casa que `python3 scripts/build_house.py 10 8`.
- [ ] `vq chat --provider ollama-local --model qwen2.5-coder:7b "construye una casa en (10,8)"` ejecuta `vq build house`.
- [ ] `vq chat --dry-run` muestra el plan sin ejecutar.
- [ ] `vq chat --confirm` pide confirmación antes de `break_block`.
- [ ] Nuevas tools de la propuesta 002 aparecen como subcomandos sin tocar código del CLI.
- [ ] Tests cubren `client.py`, subcomandos principales, y `vq chat` con mock LLM.
- [ ] Scripts originales siguen funcionando como wrappers durante la transición.

---

## 14. Próximos pasos (post-implementación)

1. **Autocompletado** (Typer + shell completion para bash/zsh/fish).
2. **Recetas personalizadas** (`vq build custom --from-file my_house.json`).
3. **Macros** (`vq macro record` / `vq macro play <name>`).
4. **Modo observador** (`vq watch` muestra estado del mundo en tiempo real).
5. **Integración con BT** (`vq bt chat` — chat natural para diseñar behavior trees).