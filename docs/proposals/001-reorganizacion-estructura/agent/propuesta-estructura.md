# Propuesta de Estructura

**Fecha:** 2026-07-22  
**Estado:** Propuesta

## Estructura final propuesta

```
VoxelQuest/
├── core/                              # antes minecraft-clone/
│   ├── shared/
│   │   └── tools/
│   │       └── definitions.json       # contrato MCP compartido
│   │
│   ├── node/                          # Stack Node.js completo
│   │   ├── game-server.js             # servidor (sirve web + relay WS + MCP)
│   │   ├── mcp-server.js              # adaptador stdio para opencode
│   │   ├── bt-engine.js               # Behavior Tree engine
│   │   ├── package.json
│   │   └── web/                       # cliente web completo
│   │       ├── index.html
│   │       ├── css/
│   │       │   └── style.css
│   │       └── js/                    # 18 módulos (world, physics, enemies...)
│   │           ├── main.js
│   │           ├── world.js
│   │           ├── physics.js
│   │           ├── player.js
│   │           ├── enemies.js
│   │           ├── game-client.js
│   │           └── ...
│   │
│   ├── python/                        # Stack Python completo
│   │   ├── server/                    # servidor autoritativo
│   │   │   ├── main.py               # FastAPI entrypoint
│   │   │   ├── engine/               # world, physics, entities, navigation
│   │   │   ├── mcp/                  # MCP JSON-RPC 2.0
│   │   │   ├── websocket/            # WebSocket game client
│   │   │   └── bt/                   # Behavior Tree engine
│   │   ├── client/                    # cliente thin
│   │   │   ├── index.html
│   │   │   └── js/                   # 7 módulos (net, input, world_mesh...)
│   │   ├── scripts/                   # scripts cliente (chase, evade, build...)
│   │   │   ├── chase.py
│   │   │   ├── evade.py
│   │   │   ├── evade_chase.py
│   │   │   ├── build_house.py
│   │   │   ├── build_gothic_cathedral.py
│   │   │   └── follow_p1_distance.py
│   │   ├── training/                  # episodios de entrenamiento
│   │   ├── pyproject.toml
│   │   ├── run.sh
│   │   └── server.py                 # static fallback
│   │
│   ├── docs/                          # documentación compartida
│   │   ├── proposals/                # propuestas de desarrollo
│   │   ├── especificacion_mcp.md
│   │   ├── MANUAL_MCP.md
│   │   └── adr/                      # Architecture Decision Records
│   │
│   ├── CHANGELOG.md
│   └── README.md
│
├── AGENTS.md                          # instrucciones para agentes
└── opencode.json                      # configuración opencode
```

## Cambios principales

### 1. Renombrar `minecraft-clone/` → `core/`
Más descriptivo y alineado con el nombre del proyecto (VoxelQuest).

### 2. Separar stacks completos
- **`node/`**: servidor Node.js + cliente web completo (autocontenido)
- **`python/`**: servidor Python + cliente thin + scripts (autocontenido)

Cada stack es independiente: servidor + cliente + herramientas.

### 3. Contrato compartido de tools
`shared/tools/definitions.json` contiene la definición de todos los tools MCP (nombre, descripción, inputSchema). Ambos servidores lo cargan.

### 4. Mover recursos compartidos
- `docs/` a la raíz de `core/` (documentación compartida)
- `scripts/` dentro de `python/` (dependen del API Python/Node)
- `training/` dentro de `python/` (pipeline de IA)

### 5. Eliminar duplicaciones
- `server.py` (static fallback) se mantiene en `python/` para desarrollo
- `run.sh` se mantiene en `python/` para arrancar el stack Python
- `textures/` (vacía) se elimina o se mueve a `shared/` si se usan

## Ventajas

1. **Claridad:** Cada stack está aislado, fácil de entender qué código pertenece a qué versión
2. **Independencia:** Cada stack puede evolucionar sin afectar al otro
3. **Contrato único:** `definitions.json` evita divergencia de APIs
4. **Migración gradual:** Se puede migrar tools de Node.js a Python incrementalmente
5. **Escalabilidad:** Fácil añadir un tercer stack (Go, Rust) si se necesita

## Desventajas

1. **Duplicación de clientes:** `node/web/` y `python/client/` siguen siendo incompatibles
2. **Scripts acoplados:** Los scripts en `python/scripts/` usan tools que solo existen en Node.js
3. **Puerto compartido:** Ambos stacks siguen compitiendo por el puerto 9000

## Mitigaciones

1. **Paridad de tools:** Priorizar implementar en Python los tools que usan los scripts
2. **Puertos distintos:** Documentar que cada stack usa un puerto diferente en desarrollo
3. **Cliente unificado:** A largo plazo, unificar los clientes web en uno solo que funcione con ambos backends
