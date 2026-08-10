# Plan de Ejecución — Cliente CLI MCP

**Fecha:** 2026-08-09
**Estado:** Pendiente aprobación
**Estimación total:** ~20h

---

## Fase 1 — Setup Typer + `client.py` + tests base (2h)

### Objetivo
Esqueleto del binario `vq` con un subcomando funcional (`vq player list`) y cliente MCP reutilizable.

### Tareas

1. **`core/python/pyproject.toml`** (AMPLIAR)
   - Añadir `[project.optional-dependencies].cli = ["typer>=0.12.0"]`
   - Añadir `[project.optional-dependencies].llm = ["openai>=1.30.0"]`
   - Añadir `[project.scripts].vq = "cli.vq:app"`
   - Actualizar `dev` para incluir `cli` y `llm`.

2. **`core/python/cli/__init__.py`** (NUEVO, vacío)

3. **`core/python/cli/vq.py`** (NUEVO)
   - App Typer principal con `--help` y grupo `player` registrado.
   - Flags globales: `--server-url`, `--timeout`, `--json`, `--quiet`, `--verbose`.
   - Comando `vq --version`.

4. **`core/python/cli/client.py`** (NUEVO)
   - `McpClient` class: `call(tool, args)`, `list_tools()`, manejo de errores.
   - Reemplaza `mcp()` de `chase.py:13` y `build_house.py:18`.

5. **`core/python/cli/commands/__init__.py`** (NUEVO, vacío)

6. **`core/python/cli/commands/player.py`** (NUEVO)
   - Subcomando `vq player list` (tool `list_players`).
   - Subcomando `vq player state <id>` (tool `get_player_state`).

7. **`core/python/cli/tests/__init__.py`** (NUEVO, vacío)

8. **`core/python/cli/tests/test_client.py`** (NUEVO)
   - Test `McpClient.call` con mock HTTP.
   - Test `McpClient.list_tools` con mock HTTP.
   - Test manejo de errores (timeout, error MCP).

### Verificación
- [ ] `uv pip install -e ".[cli]"` no falla.
- [ ] `vq --help` muestra ayuda con grupo `player`.
- [ ] `vq player list` (con servidor corriendo) devuelve lista de jugadores.
- [ ] `vq player list --json` devuelve JSON raw.
- [ ] `pytest cli/tests/test_client.py` pasa.

---

## Fase 2 — Subcomandos player/block/world/bt (2h)

### Objetivo
Cobertura de las tools MCP existentes en tools virtuales (recetas) llega después (Fase 3).

### Tareas

1. **`core/python/cli/commands/player.py`** (AMPLIAR)
   - `move`, `attack`, `look`, `teleport`, `gamepad-connect`, `gamepad-input`, `gamepad-disconnect`, `rotation`, `camera`.
   - Mapeo 1:1 desde `definitions.json` categoría `player`.

2. **`core/python/cli/commands/block.py`** (NUEVO)
   - `place`, `break`, `get`, `fill`, `clear`, `apply`, `apply-list`.
   - `apply` lee de `--file`, `--stdin`, o args posicionales.

3. **`core/python/cli/commands/world.py`** (NUEVO)
   - `info`, `view`, `top-down`, `nearby-blocks`, `nearby-entities`, `environment`, `height`.

4. **`core/python/cli/commands/bt.py`** (NUEVO)
   - `load` (lee archivo JSON), `status`, `stop`.

5. **`core/python/cli/commands/nav.py`** (NUEVO)
   - `to` (tool `navigate_to` / `moverse_a`).

6. **`core/python/cli/commands/combat.py`** (NUEVO)
   - `attack`, `kill-all`.

7. **`core/python/cli/commands/inventory.py`** (NUEVO)
   - `select`, `next`, `prev`, `get`, `add`.

8. **`core/python/cli/commands/avatar.py`** (NUEVO)
   - `create`, `walk`, `clear`, `follow`, `list`.

9. **`core/python/cli/commands/config.py`** (NUEVO)
   - `get`, `approval`, `requests`, `approve`.

10. **`core/python/cli/commands/training.py`** (NUEVO)
    - `start`, `stop`.

11. **`core/python/cli/commands/util.py`** (NUEVO)
    - `block-types`, `avatar-colors`, `msg`.

12. **`core/python/cli/vq.py`** (AMPLIAR)
    - Registrar todos los grupos: `app.add_typer(...)`.

13. **`core/python/cli/tests/test_commands.py`** (NUEVO)
    - Test cada subcomando con mock `McpClient`.
    - Test `--json` output.

### Verificación
- [ ] `vq --help` muestra todos los grupos.
- [ ] `vq player --help` muestra todos los subcomandos de player.
- [ ] `vq block place 10 25 10 3` coloca un bloque (con servidor).
- [ ] `vq block apply --file blocks.json` aplica lote.
- [ ] `vq bt status` devuelve estado del BT.
- [ ] `pytest cli/tests/test_commands.py` pasa.

---

## Fase 3 — Migración 7 scripts de construcción a recipes/ (3h)

### Objetivo
Recetas de construcción como funciones importables. Subcomando `vq build <receta>`.

### Tareas

1. **`core/python/cli/recipes/__init__.py`** (NUEVO, vacío)

2. **`core/python/cli/recipes/house.py`** (NUEVO)
   - Extraer `build_house()` y `clear_site()` de `scripts/build_house.py`.
   - Función `build_house(client: McpClient, cx: int, cz: int, clear: bool = False) -> dict`.
   - Misma lógica de bloques que `build_house.py:59-121`.
   - Misma estrategia de lotes (`BATCH=400`) que `build_house.py:150`.

3. **`core/python/cli/recipes/castle.py`** (NUEVO)
   - Extraer de `scripts/build_castle.py`.

4. **`core/python/cli/recipes/fortress.py`** (NUEVO)
   - Extraer de `scripts/build_fortress.py`.

5. **`core/python/cli/recipes/maze.py`** (NUEVO)
   - Extraer de `scripts/build_maze.py`.

6. **`core/python/cli/recipes/pyramid.py`** (NUEVO)
   - Extraer de `scripts/build_pyramid.py`.

7. **`core/python/cli/recipes/village.py`** (NUEVO)
   - Extraer de `scripts/build_village.py`.

8. **`core/python/cli/recipes/cathedral.py`** (NUEVO)
   - Extraer de `scripts/build_gothic_cathedral.py`.

9. **`core/python/cli/commands/build.py`** (NUEVO)
   - Subcomando `vq build house|castle|fortress|maze|pyramid|village|cathedral [cx] [cz] [--clear] [--size S]`.
   - `vq build list` muestra recetas disponibles.
   - Cada subcomando llama a la función de `recipes/`.

10. **`core/python/cli/vq.py`** (AMPLIAR)
    - Registrar grupo `build`.

11. **Wrappers de transición** (`core/python/scripts/build_*.py`)
    - Cada script se convierte en wrapper: `subprocess.run([sys.executable, "-m", "cli.vq", "build", "house"] + sys.argv[1:])`.
    - Mantienen compatibilidad con flujos existentes.

12. **`core/python/cli/tests/test_recipes.py`** (NUEVO)
    - Test `build_house` con mock `McpClient`: verifica que llama `apply_blocks` con bloques correctos.
    - Test `build_maze` con tamaño específico: verifica dimensiones.

### Verificación
- [ ] `vq build house 10 8 --clear` produce la misma casa que `python3 scripts/build_house.py 10 8 --clear`.
- [ ] `vq build castle 20 20` produce el mismo castillo.
- [ ] `vq build list` muestra 7 recetas.
- [ ] `python3 scripts/build_house.py 10 8` sigue funcionando (wrapper).
- [ ] `pytest cli/tests/test_recipes.py` pasa.

---

## Fase 4 — Migración 4 scripts de comportamiento a `ai.py` (2h)

### Objetivo
Bucles de IA como subcomandos `vq ai chase|evade|evade-chase|follow`.

### Tareas

1. **`core/python/cli/commands/ai.py`** (NUEVO)
   - `vq ai chase [--target 1] [--iters 40] [--player-id 2] [--interval 0.15]`
     - Mismo bucle que `chase.py:89-109`.
     - Usa `McpClient` en lugar de `mcp()` ad hoc.
   - `vq ai evade [--iters 60] [--player-id 2]`
     - Mismo bucle que `evade.py`.
   - `vq ai evade-chase [--iters 100] [--player-id 2]`
     - Mismo bucle que `evade_chase.py`.
   - `vq ai follow [--target 1] [--distance 3] [--player-id 2]`
     - Mismo bucle que `follow_p1_distance.py`.

2. **`core/python/cli/vq.py`** (AMPLIAR)
   - Registrar grupo `ai`.

3. **Wrappers de transición** (`core/python/scripts/chase.py`, `evade.py`, etc.)
   - Cada script se convierte en wrapper a `vq ai <subcomando>`.

4. **`core/python/cli/tests/test_ai.py`** (NUEVO)
   - Test `chase` con mock `McpClient`: verifica que llama `gamepad_input` con valores esperados.
   - Test `evade` con mock.

### Verificación
- [ ] `vq ai chase --target 1 --iters 5` persigue al jugador 1.
- [ ] `vq ai evade --iters 5` huye de enemigos.
- [ ] `python3 scripts/chase.py` sigue funcionando (wrapper).
- [ ] `pytest cli/tests/test_ai.py` pasa.

---

## Fase 5 — Cliente LLM provider-agnostic + config (3h)

### Objetivo
Infraestructura LLM lista para `vq chat`. Sin UI todavía; solo `llm/` y config.

### Tareas

1. **`core/python/cli/llm/__init__.py`** (NUEVO, vacío)

2. **`core/python/cli/llm/base.py`** (NUEVO)
   - `Protocol LLMProvider`: `chat(messages, tools) -> LLMResponse`.
   - Dataclasses `ToolCall`, `LLMResponse`.

3. **`core/python/cli/llm/openai_compat.py`** (NUEVO)
   - `OpenAICompatProvider`: usa `openai.OpenAI(base_url, api_key, model)`.
   - `chat()`: llama `client.chat.completions.create(model, messages, tools)`.
   - Parsea `tool_calls` del response.

4. **`core/python/cli/llm/registry.py`** (NUEVO)
   - `resolve_provider(provider: str, model: str, base_url: str, api_key: str) -> LLMProvider`.
   - Soporta: `ollama_local`, `ollama_cloud`, `custom`.
   - Defaults por provider:
     - `ollama_local`: `base_url=http://localhost:11434/v1`, `api_key="ollama"` (dummy).
     - `ollama_cloud`: `base_url` configurable, `api_key` requerida.
     - `custom`: `base_url` y `api_key` requeridas.

5. **`core/python/cli/config.py`** (NUEVO)
   - Carga `~/.vq/config.toml` (con `tomllib` stdlib Python 3.11+).
   - Override con variables de entorno `VQ_*`.
   - Estructura: `ServerConfig`, `LLMConfig`, `ChatConfig`.

6. **`core/python/pyproject.toml`** (AMPLIAR)
   - Añadir `tomli` para Python <3.11 compat (aunque `requires-python>=3.12` ya tiene `tomllib`).

7. **`core/python/cli/tests/test_llm.py`** (NUEVO)
   - Test `OpenAICompatProvider` con mock `openai.OpenAI`.
   - Test `resolve_provider` con distintos providers.
   - Test config loading desde TOML mock.

### Verificación
- [ ] `uv pip install -e ".[cli,llm]"` no falla.
- [ ] `OpenAICompatProvider` con mock devuelve `LLMResponse` con `tool_calls`.
- [ ] `resolve_provider("ollama_local", "qwen2.5-coder:7b", ...)` devuelve provider correcto.
- [ ] `~/.vq/config.toml` se carga correctamente.
- [ ] Variables `VQ_*` sobreescriben config.
- [ ] `pytest cli/tests/test_llm.py` pasa.

---

## Fase 6 — `vq chat`: REPL + prompt engineering + dry-run + confirm (5h)

### Objetivo
Modo interactivo de lenguaje natural. El usuario escribe prompts, el LLM decide tools, el CLI ejecuta.

### Tareas

1. **`core/python/cli/commands/chat.py`** (NUEVO)
   - Subcomando `vq chat`.
   - Flags: `--provider`, `--model`, `--base-url`, `--api-key`, `--dry-run`, `--confirm`, `--auto`, `--history-file`.
   - Bucle REPL:
     - `input("> ")` → prompt del usuario.
     - Construir `messages`: `[system_prompt, *history, user_prompt]`.
     - Llamar `provider.chat(messages, tools)`.
     - Si `tool_calls`:
       - `--dry-run`: mostrar plan, pedir `y/n`.
       - `--confirm` + tool destructiva: pedir `y/n`.
       - Ejecutar cada tool_call vía `execute_tool_call()`.
       - Enviar resultados al LLM como `tool` role.
       - LLM genera respuesta legible.
     - Mostrar respuesta.
     - Guardar en historial.
   - Comandos especiales: `/quit`, `/clear`, `/history`, `/tools`, `/provider <p>`.

2. **`core/python/cli/commands/chat.py` — Prompt del sistema**
   - Cargar `tools/list` al iniciar.
   - Incluir catálogo en el prompt.
   - Reglas: español/inglés, recetas优先, confirmación destructivas.
   - Few-shot examples por categoría.

3. **`core/python/cli/commands/chat.py` — Tools virtuales**
   - `VIRTUAL_TOOLS` dict: `build_house`, `build_castle`, ..., `ai_chase`, `ai_evade`, `ai_follow`.
   - `execute_tool_call(call, client)`: si `call.name in VIRTUAL_TOOLS`, ejecuta receta; si no, `client.call()`.
   - Schema de tools virtuales en formato OpenAI.

4. **`core/python/cli/commands/chat.py` — Tools destructivas**
   - Lista hardcodeada fase 1: `break_block`, `clear_area`, `destroy_object`, `kill_all_monsters`, `avatars_clear`.
   - Si `--confirm` y tool en lista, pedir `y/n`.
   - Futuro: campo `"destructive": true` en `definitions.json`.

5. **`core/python/cli/commands/chat.py` — Historial**
   - `~/.vq/chat_history.jsonl`: una línea por interacción (prompt + response + tool_calls).
   - Cargar historial al iniciar para contexto.
   - Comando `/clear` vacía historial en memoria (no archivo).

6. **`core/python/cli/commands/chat.py` — Streaming**
   - Si el LLM soporta streaming, mostrar tokens incrementalmente.
   - Spinner mientras espera respuesta.

7. **`core/python/cli/tests/test_chat.py`** (NUEVO)
   - Test con `MockLLMProvider` que devuelve `tool_calls` predeterminadas.
   - Test `--dry-run`: no ejecuta, muestra plan.
   - Test `--confirm`: pide confirmación para `break_block`.
   - Test tools virtuales: `build_house` ejecuta receta.

### Verificación
- [ ] `vq chat --provider ollama-local --model qwen2.5-coder:7b` arranca REPL.
- [ ] "listar jugadores" → LLM llama `list_players` → CLI ejecuta → muestra resultado.
- [ ] "construye una casa en (10, 8)" → LLM llama `build_house` → receta ejecuta.
- [ ] `--dry-run` muestra plan sin ejecutar.
- [ ] `--confirm` pide `y/n` antes de `break_block`.
- [ ] `/quit` sale limpio.
- [ ] `/tools` muestra catálogo.
- [ ] Historial se guarda en `~/.vq/chat_history.jsonl`.
- [ ] `pytest cli/tests/test_chat.py` pasa con mock LLM.

---

## Fase 7 — Tests + documentación (3h)

### Objetivo
Cobertura de tests completa y documentación lista para usuarios.

### Tareas

1. **`core/python/cli/tests/`** (AMPLIAR)
   - Tests E2E con servidor real (si arranca) o mock completo.
   - Test integración: `vq player list` + `vq block place` + `vq block get` en secuencia.
   - Cobertura ≥ 80% en `client.py`, `commands/`, `llm/`.

2. **`core/docs/MANUAL_MCP.md`** (AMPLIAR)
   - Sección "Cliente CLI `vq`":
     - Instalación: `uv pip install -e ".[cli]"`, `uv pip install -e ".[cli,llm]"`.
     - Comandos: tabla de subcomandos con ejemplos.
     - Chat: providers, configuración, ejemplos.
     - Recetas: cómo usar `vq build <receta>`.
     - Scripting: `--json` output, pipes.

3. **`core/docs/MANUAL_MCP.md`** — Sección "Crear recetas personalizadas"
   - Cómo añadir una nueva receta a `cli/recipes/`.
   - Cómo exponerla como tool virtual en `vq chat`.

4. **`core/AGENTS.md`** (AMPLIAR)
   - Mencionar `vq` CLI en sección de entrypoints.
   - Tabla de propuestas: añadir 003.

5. **`core/CHANGELOG.md`** (AMPLIAR)
   - Entrada `[Unreleased] / Added`: "Cliente CLI `vq` con subcomandos Typer y modo chat natural".

6. **`core/README.md`** (AMPLIAR)
   - Sección "CLI" con quickstart.

7. **`core/python/README.md`** (NUEVO o AMPLIAR)
   - Documentación del CLI con ejemplos.

8. **Linting/typecheck**
   - `ruff check cli/`
   - `mypy cli/` (si está configurado).

### Verificación
- [ ] `pytest cli/tests/` pasa con cobertura ≥ 80%.
- [ ] `MANUAL_MCP.md` tiene sección "Cliente CLI `vq`".
- [ ] `AGENTS.md` menciona `vq` y la propuesta 003.
- [ ] `CHANGELOG.md` actualizado.
- [ ] `ruff check cli/` no reporta errores.
- [ ] `vq --help` es claro y completo.

---

## Resumen de archivos tocados

| Archivo | Acción |
|---------|--------|
| `core/python/cli/__init__.py` | NUEVO |
| `core/python/cli/vq.py` | NUEVO |
| `core/python/cli/client.py` | NUEVO |
| `core/python/cli/config.py` | NUEVO |
| `core/python/cli/commands/__init__.py` | NUEVO |
| `core/python/cli/commands/player.py` | NUEVO |
| `core/python/cli/commands/block.py` | NUEVO |
| `core/python/cli/commands/build.py` | NUEVO |
| `core/python/cli/commands/object.py` | NUEVO (placeholder, se llena con propuesta 002) |
| `core/python/cli/commands/ai.py` | NUEVO |
| `core/python/cli/commands/bt.py` | NUEVO |
| `core/python/cli/commands/world.py` | NUEVO |
| `core/python/cli/commands/nav.py` | NUEVO |
| `core/python/cli/commands/combat.py` | NUEVO |
| `core/python/cli/commands/inventory.py` | NUEVO |
| `core/python/cli/commands/avatar.py` | NUEVO |
| `core/python/cli/commands/config.py` | NUEVO |
| `core/python/cli/commands/training.py` | NUEVO |
| `core/python/cli/commands/util.py` | NUEVO |
| `core/python/cli/commands/chat.py` | NUEVO |
| `core/python/cli/recipes/__init__.py` | NUEVO |
| `core/python/cli/recipes/house.py` | NUEVO |
| `core/python/cli/recipes/castle.py` | NUEVO |
| `core/python/cli/recipes/fortress.py` | NUEVO |
| `core/python/cli/recipes/maze.py` | NUEVO |
| `core/python/cli/recipes/pyramid.py` | NUEVO |
| `core/python/cli/recipes/village.py` | NUEVO |
| `core/python/cli/recipes/cathedral.py` | NUEVO |
| `core/python/cli/llm/__init__.py` | NUEVO |
| `core/python/cli/llm/base.py` | NUEVO |
| `core/python/cli/llm/openai_compat.py` | NUEVO |
| `core/python/cli/llm/registry.py` | NUEVO |
| `core/python/cli/tests/__init__.py` | NUEVO |
| `core/python/cli/tests/test_client.py` | NUEVO |
| `core/python/cli/tests/test_commands.py` | NUEVO |
| `core/python/cli/tests/test_recipes.py` | NUEVO |
| `core/python/cli/tests/test_ai.py` | NUEVO |
| `core/python/cli/tests/test_llm.py` | NUEVO |
| `core/python/cli/tests/test_chat.py` | NUEVO |
| `core/python/pyproject.toml` | AMPLIAR |
| `core/python/scripts/build_*.py` (7 archivos) | AMPLIAR (wrappers transición) |
| `core/python/scripts/chase.py` | AMPLIAR (wrapper) |
| `core/python/scripts/evade.py` | AMPLIAR (wrapper) |
| `core/python/scripts/evade_chase.py` | AMPLIAR (wrapper) |
| `core/python/scripts/follow_p1_distance.py` | AMPLIAR (wrapper) |
| `core/docs/MANUAL_MCP.md` | AMPLIAR |
| `core/AGENTS.md` | AMPLIAR |
| `core/CHANGELOG.md` | AMPLIAR |
| `core/README.md` | AMPLIAR |

---

## Dependencias entre fases

```
Fase 1 ──► Fase 2 ──► Fase 3 ──► Fase 7
                │           │
                └──► Fase 4 ┘
                │
                └──► Fase 5 ──► Fase 6 ──► Fase 7
```

- Fases 3 y 4 pueden ir en paralelo después de Fase 2.
- Fase 5 requiere Fase 2 (usa `client.py`).
- Fase 6 requiere Fases 3 y 5 (tools virtuales + LLM).
- Fase 7 requiere todas las anteriores.