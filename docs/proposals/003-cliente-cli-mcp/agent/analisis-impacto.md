# Análisis de Impacto — Cliente CLI MCP

**Fecha:** 2026-08-09
**Estado:** Diagnóstico

---

## 1. Punto de partida

### Infraestructura MCP existente

| Componente | Archivo | Líneas | Estado |
|------------|---------|--------|--------|
| Servidor MCP (Python) | `core/python/server/main.py:74` | 110 | ✅ |
| Handler MCP | `core/python/server/mcp/server.py` | 247 | ✅ |
| Adaptador stdio (opencode) | `core/python/mcp-client.py` | 42 | ✅ |
| Contrato de tools | `core/shared/tools/definitions.json` | 769 | ✅ |
| Config opencode (global) | `~/.config/opencode/opencode.json` | — | ✅ |
| Config opencode (proyecto) | `opencode.json` | — | ✅ |

### Scripts de cliente existentes

| Script | Líneas | Función | Duplicación |
|--------|--------|---------|-------------|
| `scripts/build_house.py` | 162 | Construye casa | `mcp()` propio (l.18) |
| `scripts/build_castle.py` | ~150 | Construye castillo | `mcp()` propio |
| `scripts/build_fortress.py` | ~150 | Construye fortaleza | `mcp()` propio |
| `scripts/build_maze.py` | ~120 | Construye laberinto | `mcp()` propio |
| `scripts/build_pyramid.py` | ~100 | Construye pirámide | `mcp()` propio |
| `scripts/build_village.py` | ~200 | Construye aldea | `mcp()` propio |
| `scripts/build_gothic_cathedral.py` | ~250 | Construye catedral | `mcp()` propio |
| `scripts/chase.py` | 115 | Persigue jugador | `mcp()` propio (l.13) |
| `scripts/evade.py` | ~100 | Huye de enemigos | `mcp()` propio |
| `scripts/evade_chase.py` | ~120 | Bucle evade+chase | `mcp()` propio |
| `scripts/follow_p1_distance.py` | ~80 | Sigue a jugador | `mcp()` propio |

**Total:** ~1550 líneas en 11 scripts, cada uno con su propia función `mcp()` HTTP duplicada.

### Entorno Python

| Aspecto | Estado |
|---------|--------|
| Python | 3.12 (`core/python/.venv/`) |
| `click` | ✅ instalado (8.4.2, transitivo) |
| `typer` | ❌ no instalado |
| `openai` SDK | ❌ no instalado |
| `httpx` | ✅ instalado (0.28.1) |
| `python-dotenv` | ✅ instalado (1.2.2) |
| `pydantic_settings` | ✅ instalado (2.14.2) |
| `mcp` | ✅ instalado (1.28.1, dev dep) |
| SDKs LLM (`anthropic`, `openai`) | ❌ ninguno |
| `.env` | ❌ no existe |
| Function-calling LLM en Python | ❌ ninguno |

### Ollama local

| Modelo | Tamaño | Tool-use |
|--------|--------|----------|
| `qwen2.5-coder:7b` | 4.7 GB | ✅ |
| `qwen3:8b` | 5.2 GB | ✅ |
| `qwen3.5:9b` | 6.6 GB | ✅ |
| `llama3.2` | 2.0 GB | ✅ |
| `deepseek-r1:8b` | 5.2 GB | ✅ |
| `phi3.5` | 2.2 GB | ✅ |

### Configuración opencode (ya activa)

- `opencode-go/deepseek-v4-pro` (suscripción OpenCode Go).
- `opencode-go/deepseek-v4-flash` (small model).
- Provider `ollama` con `baseURL: http://localhost:11434/v1`.
- MCP `voxelquest` habilitado via `mcp-client.py`.

---

## 2. Gap analysis

| Necesidad | Estado actual | Gap |
|-----------|---------------|-----|
| Cliente MCP standalone (sin opencode) | ❌ | **Total** |
| CLI con `--help` autogenerado | ❌ | **Total** |
| Unificación de 11 scripts dispersos | ❌ (11 scripts con `mcp()` duplicado) | **Total** |
| Validación de argumentos | ❌ (cada script parsea args ad hoc) | **Total** |
| Modo lenguaje natural sin opencode | ❌ | **Total** |
| Provider LLM configurable | Parcial (solo opencode) | **Alto** |
| Recetas como tools virtuales para LLM | ❌ | **Total** |
| Dry-run / confirmación | ❌ | **Total** |
| Historial conversacional | ❌ | **Total** |
| Output JSON para scripting | ❌ | **Total** |

### Observaciones clave

1. **El servidor MCP no se toca.** El contrato ya está listo (`definitions.json` + `mcp/server.py`). El CLI es puro consumidor vía `POST /mcp`.
2. **`mcp-client.py` (adaptador stdio) no se toca.** Sigue siendo el puente opencode↔servidor. El CLI `vq` es un cliente paralelo.
3. **Los 11 scripts duplican `mcp()` HTTP.** Unificación en `client.py` elimina ~150 líneas de duplicación.
4. **`click` ya está en `.venv`.** Añadir Typer encima es trivial.
5. **Ollama Local está operativo.** 6 modelos con tool-use verificado. No requiere API key ni coste.
6. **OpenAI-compatible es estándar.** Un solo SDK (`openai`) sirve para Ollama Local, Ollama Cloud, y cualquier endpoint custom.
7. **OpenCode Go no es consumible externamente.** Es una suscripción vinculada a opencode; no expone endpoint HTTP público. Para DeepSeek V4 fuera de opencode se necesita API key directa.

---

## 3. Impacto por archivo

### Nuevos (~40 archivos)

| Archivo | Líneas est. | Razón |
|---------|-------------|-------|
| `cli/vq.py` | ~80 | Entrypoint Typer |
| `cli/client.py` | ~100 | `McpClient` reutilizable |
| `cli/config.py` | ~80 | Config TOML + env vars |
| `cli/commands/player.py` | ~120 | 11 subcomandos |
| `cli/commands/block.py` | ~100 | 7 subcomandos |
| `cli/commands/build.py` | ~80 | 8 subcomandos (recetas) |
| `cli/commands/object.py` | ~100 | 13 subcomandos (propuesta 002) |
| `cli/commands/ai.py` | ~200 | 4 bucles de comportamiento |
| `cli/commands/bt.py` | ~40 | 3 subcomandos |
| `cli/commands/world.py` | ~60 | 7 subcomandos |
| `cli/commands/nav.py` | ~20 | 1 subcomando |
| `cli/commands/combat.py` | ~30 | 2 subcomandos |
| `cli/commands/inventory.py` | ~50 | 5 subcomandos |
| `cli/commands/avatar.py` | ~60 | 5 subcomandos |
| `cli/commands/config.py` | ~40 | 4 subcomandos |
| `cli/commands/training.py` | ~30 | 2 subcomandos |
| `cli/commands/util.py` | ~30 | 3 subcomandos |
| `cli/commands/chat.py` | ~300 | REPL + LLM + tools virtuales + dry-run + confirm |
| `cli/recipes/house.py` | ~120 | Extraído de `build_house.py` |
| `cli/recipes/castle.py` | ~120 | Extraído |
| `cli/recipes/fortress.py` | ~120 | Extraído |
| `cli/recipes/maze.py` | ~100 | Extraído |
| `cli/recipes/pyramid.py` | ~80 | Extraído |
| `cli/recipes/village.py` | ~180 | Extraído |
| `cli/recipes/cathedral.py` | ~200 | Extraído |
| `cli/llm/base.py` | ~40 | Protocol + dataclasses |
| `cli/llm/openai_compat.py` | ~80 | Implementación OpenAI-compatible |
| `cli/llm/registry.py` | ~60 | Resolver provider |
| `cli/tests/test_client.py` | ~80 | Tests cliente |
| `cli/tests/test_commands.py` | ~150 | Tests subcomandos |
| `cli/tests/test_recipes.py` | ~100 | Tests recetas |
| `cli/tests/test_ai.py` | ~80 | Tests bucles IA |
| `cli/tests/test_llm.py` | ~80 | Tests LLM provider |
| `cli/tests/test_chat.py` | ~120 | Tests chat con mock LLM |
| **Total nuevo** | **~2900** | |

### Modificados

| Archivo | Cambio | Riesgo |
|---------|--------|--------|
| `core/python/pyproject.toml` | +`[cli]`, +`[llm]`, +`[project.scripts]` | Bajo |
| `core/python/scripts/build_house.py` | → wrapper `vq build house` | Bajo (transición) |
| `core/python/scripts/build_castle.py` | → wrapper | Bajo |
| `core/python/scripts/build_fortress.py` | → wrapper | Bajo |
| `core/python/scripts/build_maze.py` | → wrapper | Bajo |
| `core/python/scripts/build_pyramid.py` | → wrapper | Bajo |
| `core/python/scripts/build_village.py` | → wrapper | Bajo |
| `core/python/scripts/build_gothic_cathedral.py` | → wrapper | Bajo |
| `core/python/scripts/chase.py` | → wrapper `vq ai chase` | Bajo |
| `core/python/scripts/evade.py` | → wrapper | Bajo |
| `core/python/scripts/evade_chase.py` | → wrapper | Bajo |
| `core/python/scripts/follow_p1_distance.py` | → wrapper | Bajo |
| `core/docs/MANUAL_MCP.md` | +sección "Cliente CLI `vq`" | Bajo |
| `core/AGENTS.md` | +tabla propuestas (003) | Bajo |
| `core/CHANGELOG.md` | +entrada Unreleased/Added | Bajo |
| `core/README.md` | +sección CLI | Bajo |

### No tocados (importante)

- `core/python/server/main.py` — **no se toca**. El endpoint `/mcp` queda igual.
- `core/python/server/mcp/server.py` — **no se toca**. Los handlers existentes quedan igual.
- `core/python/mcp-client.py` — **no se toca**. Adaptador stdio para opencode sigue funcionando.
- `core/shared/tools/definitions.json` — **no se toca**. Solo se lee.
- `core/web/` — **no se toca**. Cliente web no afectado.
- Stack Node.js — **no se toca**. Fuera de alcance.
- `core/python/server/engine/` — **no se toca**. Motor del juego no afectado.
- `core/python/scripts/update_changelog.py` — **no se toca**. Tooling de desarrollo, no gameplay.
- `core/python/scripts/kill-port.sh` — **no se toca**. Utilidad.

---

## 4. Reducción de duplicación

### Antes

```
scripts/build_house.py:18    def mcp(method, params, timeout=15): ...
scripts/build_castle.py:~18  def mcp(method, params, timeout=15): ...  # duplicado
scripts/build_fortress.py    def mcp(...): ...                         # duplicado
scripts/chase.py:13          def mcp(method, params): ...              # duplicado
scripts/evade.py             def mcp(...): ...                         # duplicado
... (11 scripts, 11 funciones mcp() duplicadas)
```

### Después

```
cli/client.py    class McpClient: def call(tool, args): ...
                  (única fuente)
cli/commands/*.py    usan McpClient
cli/recipes/*.py     usan McpClient
cli/commands/chat.py usa McpClient
```

**Eliminadas:** ~150 líneas de `mcp()` duplicadas a través de 11 scripts.

---

## 5. Impacto en rendimiento

### CLI por comandos

- **Sin LLM:** latencia = 1 HTTP request a `/mcp` (localhost, <5ms). Despreciable.
- **Recetas:** lotes de 400 bloques vía `apply_blocks`. Misma performance que scripts actuales.
- **Bucles IA:** mismo intervalo (0.15s) que scripts actuales. Sin overhead adicional.

### `vq chat`

- **Ollama Local, CPU:** 5-15s por prompt (modelo 7-9B). Limitante pero tolerable para uso interactivo.
- **Ollama Local, GPU:** 1-3s por prompt. Aceptable.
- **Ollama Cloud:** 1-3s por prompt + latencia red.
- **Tokens:** catálogo de ~55 tools × ~100 tokens/tool = ~5500 tokens en system prompt. Coste por interacción: ~6000-8000 tokens input + ~500-2000 tokens output. Con recetas como tools virtuales, se reduce a ~15 tools virtuales + ~55 nativas = ~7000 tokens.

### Servidor

- **Sin impacto.** El CLI es cliente; el servidor no recibe más carga que la que el usuario genere.

---

## 6. Impacto en dependencias

| Dependencia | Tamaño | Grupo | Necesario para |
|-------------|--------|-------|----------------|
| `typer>=0.12.0` | ~200KB (+ `click` ya instalado) | `[cli]` | Todos los subcomandos |
| `openai>=1.30.0` | ~500KB | `[llm]` | Solo `vq chat` |

Instalación modular:
- `uv pip install -e ".[cli]"` → comandos sin LLM.
- `uv pip install -e ".[cli,llm]"` → comandos + chat.
- Sin `openai` instalado, `vq chat` falla con mensaje claro: "instala con `uv pip install -e '.[llm]'`".

No se añaden dependencias al servidor. `pyproject.toml` crece solo en optional-dependencies.

---

## 7. Impacto en contrato MCP y scripts

### `definitions.json`

**No se modifica.** El CLI lee `tools/list` en runtime y genera subcomandos dinámicamente. Nuevas tools (propuesta 002) aparecen automáticamente.

### Scripts existentes

Durante la transición, los 11 scripts se convierten en wrappers de 3 líneas que delegan a `vq`:

```python
# scripts/build_house.py (versión transición)
"""Wrapper: python3 scripts/build_house.py → vq build house"""
import subprocess, sys
subprocess.run([sys.executable, "-m", "cli.vq", "build", "house"] + sys.argv[1:])
```

**Retrocompatible:** flujos existentes (`python3 scripts/build_house.py 10 8 --clear`) siguen funcionando.

### opencode

`opencode.json` sigue apuntando a `mcp-client.py`. **Sin conflicto**: opencode y `vq` son clientes paralelos del mismo servidor. Pueden usarse simultáneamente.

---

## 8. Riesgos detallados

| # | Riesgo | Prob | Impacto | Mitigación |
|---|--------|------|---------|------------|
| R1 | Modelos locales 7-9B fallan en tool-use complejo | Med | Med | Prompt few-shot por categoría; `--provider ollama-cloud` como fallback; `--dry-run` para detectar errores |
| R2 | Sin provider por defecto frusta al usuario | Med | Bajo | Mensaje claro al arrancar sin `--provider`; `~/.vq/config.toml` persiste la elección; `vq chat --help` muestra ejemplos |
| R3 | Latencia 5-15s en CPU frustra | Med | Med | Spinner + streaming de tokens; documentar requisito GPU; `--provider ollama-cloud` como alternativa |
| R4 | Tool-use ambiguo elige tool equivocada | Med | Alto | `--dry-run` recomendado por defecto; validar argumentos antes de enviar; sistema de confirmación |
| R5 | Migración de scripts rompe flujos existentes | Bajo | Med | Scripts viejos se mantienen como wrappers; `vq build house` produce mismo resultado que `build_house.py` |
| R6 | Typer añade dependencia | Bajo | Bajo | ~200KB; `click` ya en `.venv`; opcional via `[cli]` |
| R7 | `openai` SDK pesa | Bajo | Bajo | Opcional via `[llm]`; solo si se usa `vq chat` |
| R8 | `tomllib` no disponible (Python <3.11) | Bajo | Bajo | `requires-python>=3.12` ya garantiza `tomllib` stdlib |
| R9 | Ollama no está corriendo | Med | Bajo | `vq chat` detecta conexión y muestra mensaje: "arranca Ollama con `ollama serve`" |
| R10 | Servidor del juego no está corriendo | Med | Bajo | Todos los subcomandos detectan conexión y muestran: "arranca el servidor con `./start.sh python`" |

---

## 9. Alternativas consideradas y descartadas

### A. Usar opencode como único cliente natural
- **Pros:** ya funciona, sin código nuevo.
- **Cons:** requiere TUI/editor; no configurable por juego; sin recetas; sin `--help`; sin scripting.
- **Decisión:** opencode se mantiene como cliente válido, pero `vq` ofrece alternativa standalone.

### B. Click puro (sin Typer)
- **Pros:** `click` ya instalado, 0 dependencias nuevas.
- **Cons:** decoradores verbosos, menos ergonomía para 25+ subcomandos, `--help` menos rico.
- **Decisión:** Typer por ergonomía; `click` sigue como dependencia transitiva.

### C. argparse stdlib
- **Pros:** 0 dependencias.
- **Cons:** para 25+ subcomandos se vuelve inmanejable; sin `--help` autogenerado rico; sin validación de tipos.
- **Decisión:** descartado por complejidad.

### D. SDKs nativos por proveedor (`anthropic`, `ollama` Python SDK)
- **Pros:** acceso a features específicas de cada proveedor.
- **Cons:** 3 SDKs distintos; mantenimiento alto; `anthropic` no es necesario (no se usa el proveedor).
- **Decisión:** un solo SDK `openai` (OpenAI-compatible) sirve para todos los providers.

### E. LangChain / LlamaIndex
- **Pros:** abstracción madura para LLM + tools.
- **Cons:** dependencias pesadas (~50MB+), abstracción excesiva para este caso, curva de aprendizaje.
- **Decisión:** implementación directa con `openai` SDK; más control, menos dependencias.

### F. MCP SDK de Python (`mcp>=1.0.0`, ya en dev deps)
- **Pros:** ya instalado; estándar MCP.
- **Cons:** orientado a servidores, no a clientes consumer. El CLI necesita cliente HTTP simple + LLM, no servidor MCP.
- **Decisión:** se usa para inspiración de protocolo, pero el CLI consume vía HTTP directo (`client.py`).

### G. Sin modo chat (solo comandos)
- **Pros:** ~9h en vez de ~20h; sin dependencias LLM.
- **Cons:** no cubre el requisito de lenguaje natural del usuario.
- **Decisión:** descartado; el usuario pidió ambos modos.

---

## 10. Compatibilidad con propuestas existentes

### Propuesta 001 (reorganización)
- **Sin conflicto.** El CLI se añade en `core/python/cli/`, estructura ya prevista por la propuesta 001.

### Propuesta 002 (objetos móviles)
- **Sinergia total.** Las 15 tools nuevas de la propuesta 002 aparecen automáticamente como subcomandos `vq object *` porque se generan dinámicamente desde `tools/list`. El CLI no necesita tocar código para soportarlas.
- `vq chat` expondrá las tools de objetos al LLM automáticamente.

### Propuesta 003 (esta propuesta)
- **Auto-contenida.** No requiere que 002 esté implementada para funcionar. Cuando 002 se implemente, el CLI la soporta sin cambios.

---

## 11. Compatibilidad con guardado/carga

No aplica. El CLI es stateless; no persiste estado del juego. El historial de `vq chat` es la única persistencia (`~/.vq/chat_history.jsonl`), pero es conversacional, no de juego.

---

## 12. Conclusión

El impacto es **casi exclusivamente aditivo**: ~40 archivos nuevos, 0 archivos del servidor modificados, 11 scripts convertidos a wrappers (transición reversible). El único riesgo real es **R4** (tool-use ambiguo), mitigado con `--dry-run` y `--confirm`.

La propuesta reduce duplicación (~150 líneas de `mcp()` eliminadas), unifica 11 scripts dispersos bajo un binario con `--help` autogenerado, y añade modo lenguaje natural sin acoplarse a un proveedor LLM específico.

**Viabilidad:** ALTA para ambos modos. El CLI por comandos es trivial (Typer + `urllib`). El modo chat es viable con Ollama Local (ya operativo) y escalable a Ollama Cloud / custom sin tocar código.