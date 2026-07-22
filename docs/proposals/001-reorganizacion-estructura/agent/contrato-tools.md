# Contrato Compartido de Tools MCP

**Fecha:** 2026-07-22  
**Estado:** Propuesta

## Objetivo

Crear un contrato único de tools MCP que ambos servidores (Node.js y Python) puedan cargar, evitando divergencia de APIs y facilitando la interoperabilidad.

## Estructura del contrato

### Ubicación
```
shared/tools/
└── definitions.json
```

### Formato JSON

```json
{
  "version": "1.0.0",
  "tools": {
    "place_block": {
      "description": "Coloca un bloque en coordenadas absolutas",
      "inputSchema": {
        "type": "object",
        "properties": {
          "x": {
            "type": "integer",
            "description": "Coordenada X absoluta"
          },
          "y": {
            "type": "integer",
            "description": "Coordenada Y absoluta (altura)",
            "minimum": 0,
            "maximum": 63
          },
          "z": {
            "type": "integer",
            "description": "Coordenada Z absoluta"
          },
          "type": {
            "type": "integer",
            "description": "Tipo de bloque (0=aire, 1=hierba, ..., 10=bedrock)",
            "minimum": 0,
            "maximum": 10
          }
        },
        "required": ["x", "y", "z", "type"]
      },
      "servers": ["node", "python"],
      "category": "world"
    },
    "get_player_state": {
      "description": "Obtener estado completo de un jugador",
      "inputSchema": {
        "type": "object",
        "properties": {
          "player_id": {
            "type": "integer",
            "description": "ID del jugador (1=local, 2=coop, 3+=IA)"
          }
        },
        "required": ["player_id"]
      },
      "servers": ["node", "python"],
      "category": "player"
    },
    "gamepad_input": {
      "description": "Inyecta input de gamepad virtual para un jugador",
      "inputSchema": {
        "type": "object",
        "properties": {
          "player_id": {
            "type": "integer",
            "description": "ID del jugador"
          },
          "input": {
            "type": "object",
            "description": "Estado del gamepad",
            "properties": {
              "move": {
                "type": "object",
                "properties": {
                  "x": {"type": "number", "minimum": -1, "maximum": 1},
                  "z": {"type": "number", "minimum": -1, "maximum": 1}
                }
              },
              "look": {
                "type": "object",
                "properties": {
                  "x": {"type": "number"},
                  "y": {"type": "number"}
                }
              },
              "jump": {"type": "boolean"},
              "fly": {"type": "boolean"}
            }
          }
        },
        "required": ["player_id", "input"]
      },
      "servers": ["node", "python"],
      "category": "player"
    },
    "get_top_down_view": {
      "description": "Obtiene vista top-down del mundo alrededor de un jugador",
      "inputSchema": {
        "type": "object",
        "properties": {
          "player_id": {"type": "integer"},
          "radius": {"type": "integer", "minimum": 1, "maximum": 32}
        },
        "required": ["player_id", "radius"]
      },
      "servers": ["node"],
      "category": "world",
      "note": "Solo implementado en Node.js. Pendiente migrar a Python."
    }
  }
}
```

## Campos de cada tool

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `description` | string | Descripción humana del tool |
| `inputSchema` | object | JSON Schema del input (formato MCP estándar) |
| `servers` | array | Lista de servidores que implementan este tool (`["node", "python"]`) |
| `category` | string | Categoría para organización (`world`, `player`, `combat`, `navigation`, `bt`) |
| `note` | string (opcional) | Notas adicionales (ej: "pendiente migrar") |

## Uso en cada servidor

### Node.js (`game-server.js`)

```javascript
const toolDefinitions = require('../shared/tools/definitions.json');

// Filtrar solo tools que este servidor implementa
const myTools = Object.entries(toolDefinitions.tools)
  .filter(([name, def]) => def.servers.includes('node'))
  .map(([name, def]) => ({
    name,
    description: def.description,
    inputSchema: def.inputSchema
  }));

// Registrar handlers
for (const tool of myTools) {
  registerTool(tool.name, tool.inputSchema, handlers[tool.name]);
}
```

### Python (`server/mcp/server.py`)

```python
import json
from pathlib import Path

# Cargar definiciones compartidas
defs_path = Path(__file__).parent.parent.parent / 'shared' / 'tools' / 'definitions.json'
with open(defs_path) as f:
    tool_definitions = json.load(f)

# Filtrar solo tools que este servidor implementa
my_tools = [
    {
        'name': name,
        'description': defn['description'],
        'inputSchema': defn['inputSchema']
    }
    for name, defn in tool_definitions['tools'].items()
    if 'python' in defn['servers']
]

def list_tools():
    return my_tools
```

## Ventajas

1. **Contrato único:** Si cambias la firma de un tool, se actualiza en un sitio
2. **Visibilidad:** El campo `servers` muestra qué tools están implementados en cada backend
3. **Migración gradual:** Tools marcados con `servers: ["node"]` son candidatos a migrar a Python
4. **Documentación viva:** El JSON es la fuente de verdad de la API MCP
5. **Validación:** Ambos servidores pueden validar que implementan el schema correcto

## Proceso de actualización

1. **Añadir nuevo tool:**
   - Añadir entrada en `definitions.json` con `servers: ["node"]` o `["python"]` o ambos
   - Implementar handler en el servidor correspondiente

2. **Modificar tool existente:**
   - Actualizar `inputSchema` en `definitions.json`
   - Actualizar handlers en ambos servidores si `servers` incluye ambos

3. **Deprecar tool:**
   - Marcar con `"deprecated": true` en `definitions.json`
   - Mantener implementación por compatibilidad
   - Eliminar en siguiente versión mayor

4. **Migrar tool de Node.js a Python:**
   - Cambiar `servers: ["node"]` a `servers: ["node", "python"]`
   - Implementar handler en Python
   - Una vez validado, cambiar a `servers: ["python"]`
   - Eliminar implementación en Node.js

## Herramientas de validación (futuro)

Se puede crear un script que valide que ambos servidores implementan correctamente el contrato:

```bash
# Validar que Node.js implementa todos sus tools
node validate-tools.js node

# Validar que Python implementa todos sus tools
python validate_tools.py python

# Validar que no hay tools sin implementar
python validate_tools.py --check-coverage
```
