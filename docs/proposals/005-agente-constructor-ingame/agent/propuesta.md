# Propuesta: Agente constructor in-game

**Fecha:** 2026-09-06
**Estado:** Propuesta (no implementado)
**Alcance:** Stack Python. Añade un agente autónomo dentro del servidor que ejecuta objetivos de construcción usando las tools MCP in-process (incluido `build_csg` de la propuesta 004).
**Resumen:** Un "cerebro" LLM dentro del servidor que recibe objetivos en lenguaje natural ("construye una catedral en X"), decide qué tools llamar y las ejecuta directamente sobre el game_loop, sin pasar por opencode ni por HTTP. opencode sigue siendo un cliente MCP paralelo y puede dirigir al agente vía tools nuevas.

---

## 1. Motivación

### 1.1 Situación actual

Hoy, construir algo nuevo requiere que un agente externo (opencode) genere un script Python o llame a `build_csg` vía HTTP. El servidor es pasivo: solo responde a peticiones.

### 1.2 Objetivos

1. **Agente constructor**: un bucle autónomo dentro del servidor que interpreta objetivos y ejecuta tools MCP in-process.
2. **Provider-agnostic**: LLM OpenAI-compatible. Default Ollama local; cambio trivial a cloud (Ollama Cloud, DeepSeek V4 Flash, etc.) vía config/env.
3. **No invasivo**: opt-in (disabled por defecto), task async separado del game loop, whitelist de tools, presupuesto, log JSONL.
4. **opencode intacto**: sigue como cliente MCP paralelo; además puede dirigir al agente vía `agent_task`/`agent_status`/`agent_stop`.

---

## 2. Arquitectura

```
opencode/chat/web ──agent_task("construye catedral en X")──► Servidor
                                                              │
                                              ┌───────────────┴──────────────┐
                                              │  Agent loop (asyncio task)    │
                                              │  sense → LLM → tool_calls    │
                                              │  dispatch in-process a       │
                                              │  build_csg, get_view...     │
                                              └──────────────────────────────┘
```

| Componente | Archivo (propuesto) | Responsabilidad |
|---|---|---|
| Cerebro | `core/python/server/agent/brain.py` | Cliente LLM OpenAI-compatible (httpx) |
| Bucle | `core/python/server/agent/loop.py` | Objetivo → plan → ejecutar → observar |
| Despacho | `core/python/server/agent/dispatcher.py` | Invoca handlers MCP in-process con whitelist |
| Config | `core/python/server/agent/config.py` | Proveedor, modelo, presupuesto, tools permitidas |

### 2.1 Configuración LLM

- **Default**: Ollama local (`http://localhost:11434/v1`, sin API key).
- **Cambio a cloud** vía variables de entorno (sin tocar código):
  - `VQ_AGENT_BASE_URL` (p.ej. endpoint Ollama Cloud o `https://api.deepseek.com/v1`)
  - `VQ_AGENT_MODEL` (p.ej. `deepseek-v4-flash`)
  - `VQ_AGENT_API_KEY`
- **Opt-in**: `VQ_AGENT_ENABLED=true` (disabled por defecto).

### 2.2 Seguridad

| Riesgo | Mitigación |
|---|---|
| Agente autónomo mutando el mundo | Whitelist de tools (solo construcción/visión), presupuesto (máx bloques/llamadas por tarea) |
| Bloquear el game loop | Task asyncio separado; el tick 20Hz nunca espera al LLM (latencia 1-15s) |
| No-determinismo / debugging | Log JSONL de cada tool_call del agente |
| Coste/tokens | Presupuesto por tarea; Ollama local como default |

### 2.3 Tools MCP nuevas

| Tool | Función |
|---|---|
| `agent_task` | Envía un objetivo al agente (texto + posición opcional + presupuesto) |
| `agent_status` | Estado del agente: tarea actual, progreso, tools usadas |
| `agent_stop` | Cancela la tarea en curso |

---

## 3. Sinergias

- **Propuesta 004 (CSG)**: el agente usa `build_csg`/`preview_csg` como manos. CSG compacto = menos tokens, menos errores.
- **Propuesta 003 (CLI `vq`)**: `vq chat` y el agente in-game comparten el diseño LLM provider-agnostic.
- **BT engine**: el agente puede delegar comportamientos reactivos (seguir, esquivar) al BT mientras el LLM planifica.

---

## 4. Fases propuestas

| Fase | Entrega |
|---|---|
| 1 | Dispatcher in-process (invocar handlers MCP sin HTTP) + tests |
| 2 | Cerebro LLM (httpx → OpenAI-compatible) + config provider-agnostic |
| 3 | Bucle objetivo→plan→ejecutar→observar con whitelist y presupuesto |
| 4 | Tools `agent_task`/`agent_status`/`agent_stop` + log JSONL |
| 5 | Documentación (MANUAL_MCP, AGENTS, CHANGELOG) |

---

## 5. Criterios de éxito

- [ ] `agent_task("construye una casa en (10,8)")` ejecuta `build_csg` con `house.json`.
- [ ] Cambiar de Ollama local a DeepSeek V4 Flash solo requiere variables de entorno.
- [ ] El game loop no se bloquea durante la planificación del agente.
- [ ] El agente no puede llamar tools fuera de la whitelist.
- [ ] `agent_status` muestra progreso y `agent_stop` cancela.
- [ ] opencode sigue funcionando como cliente MCP sin cambios.
