# Fase 3: Motor de Behavior Tree (Node.js) - COMPLETADA

**Fecha:** 2026-07-14  
**Estado:** Completada

## Resumen

Implementado motor de Árboles de Comportamiento en Node.js con parser de JSON, resolución de variables del Blackboard, estado RUNNING, y tick loop a 10Hz. Integrado en voxelquest-server.js con endpoint POST /bt.

## Archivos Creados/Modificados

| Archivo | Cambio |
|---------|--------|
| `bt-engine.js` | **Nuevo**: `BehaviorTree`, `BTNode`, `createActionCatalog`, validación de schema |
| `voxelquest-server.js` | Integración BT: `loadBehaviorTree()`, `startBtTick()`, `stopBtTick()`, `btRelay()`, handlers `bt_load`/`bt_status`/`bt_stop`, blackboard en estado sync |
| `js/game-client.js` | `syncState()` ahora incluye entidades (enemigos) para el blackboard |

## Detalles Técnicos

### bt-engine.js

**Node types:**
- `Selector`: OR — prueba hijos, SUCCESS si alguno tiene éxito
- `Secuencia`: AND — prueba hijos, FAILURE si alguno falla
- `Condicion`: evalúa variable del Blackboard con operadores (`menor_que`, `mayor_que`, `igual_a`, `verdadero`, `falso`)
- `Accion`: ejecuta función del catálogo con parámetros resueltos

**Resolución de Blackboard:**
- Parámetros string que coinciden con claves del Blackboard se sustituyen en runtime
- `target_enemigo_x` → `14.0` (valor actual del blackboard)

**Estado RUNNING:**
- `moverse_a` retorna RUNNING (para evitar comandos duplicados)
- El motor guarda `runningAction = tipo + params` en el árbol
- En el siguiente tick, si la misma acción con los mismos params es evaluada, retorna RUNNING sin ejecutar
- Al cambiar de rama (condiciones diferentes), `runningAction` se limpia automáticamente

**Validación:**
- Depth máxima: 50 niveles
- Validación de tipos: comportamiento, comparacion, tipo deben ser válidos
- Acciones deben existir en el catálogo

### voxelquest-server.js — Integración

```
POST /bt  →  loadBehaviorTree(json)  →  startBtTick()
                                          ↓
                                    setInterval 100ms
                                          ↓
                                    updateBtBlackboard()
                                          ↓
                                    btEngine.tick()
                                          ↓
                                    btRelay() → sendToGame() → browser
```

**Blackboard** se actualiza desde:
- `state_update.players` (posición, vida — cada 1s)
- `state_update.entities` (enemigos cercanos — desde syncState del browser)

**Fallback:** Si el árbol completo retorna FAILURE, se resetea runningAction y se envía input idle (detener movimiento).

### Endpoints MCP

| Método | Descripción |
|--------|-------------|
| `bt_load` | Cargar árbol JSON. Inicia tick loop |
| `bt_status` | Estado del motor + blackboard actual |
| `bt_stop` | Detener tick loop y limpiar árbol |

## Casos de Uso Verificados

1. Vida ≥ 5, sin enemigos → idle (SUCCESS, sin acciones)
2. Vida < 5 → moverse_a(-10, -10) (RUNNING con dedup)
3. Vida ≥ 5, enemigos cerca → golpear (SUCCESS cada tick)
4. RUNNING dedup: misma acción+params → no re-ejecuta
5. Cambio de condiciones → runningAction se limpia automáticamente

## Pendiente para Fase 4

- Aumentar frecuencia de sync browser→server (actualmente 1Hz, ideal para BT 10Hz)
- Coordinar player_id dinámico (hardcoded a 2 en acciones)
- Manejar respuesta del navegador para acciones RUNNING (moverse_a completado)
- Probar end-to-end con servidor real

## Cómo Probar

```bash
# Iniciar servidor
node voxelquest-server.js

# Cargar árbol
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"method":"bt_load","params":{"tree":{...árbol JSON...}}}'

# Ver estado
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"method":"bt_status","params":{}}'

# Detener
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"method":"bt_stop","params":{}}'
```
