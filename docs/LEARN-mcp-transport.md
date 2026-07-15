# LEARN: MCP Transport — la tubería entre tu código y la IA

## Concepto

**MCP (Model Context Protocol)** define *cómo* se mandan los mensajes entre un servidor de herramientas y un cliente (como opencode). Esa tubería de comunicación se llama **transporte**. Hay 2 sabores:

| Transporte | Cómo se comunica | Ideal para |
|---|---|---|
| **STDIO** | stdin / stdout (tubería de texto) | Servidores que lanzas y matas con opencode |
| **HTTP + SSE** | POST + eventos vía HTTP | Servidores ya corriendo (remotos o background) |

## Por qué es importante

Si eliges mal el transporte, opencode no podrá hablar con tu servidor MCP. Es como tener un walkie-talkie en modo equivocado: oyes ruido blanco pero no la señal. El error típico que vimos fue:

> `opencode: voxelquest — operation timed out`

La causa: opencode intentaba conectar vía HTTP (tipo `remote`) a un servidor que no había arrancado aún.

## Explicación sencilla

Imagina que opencode es un chef (la IA) y tu servidor MCP es un ayudante de cocina con herramientas (pelar, cortar, batir).

- **STDIO** = el ayudante está *en la misma cocina*. El chef le habla directamente ("pela la zanahoria") y el ayudante responde al instante. Cuando el chef se va, el ayudante también.
- **HTTP + SSE** = el ayudante está *en una cocina remota*, con un teléfono. El chef llama, da la orden, el ayudante cuelga, la hace, y llama de vuelta. El ayudante puede seguir en la cocina aunque el chef no esté hablando.

```
STDIO (local):        opencode ←→ [tu MCP server]    mismo proceso
HTTP (remote):        opencode ←→ 🌐 ←→ [tu server]  proceso separado
```

## Ejemplo práctico

### Tu FastMCP en Python (STDIO)

```python
from fastmcp import FastMCP

mcp = FastMCP(name="Mi Primer Servidor MCP")

@mcp.tool()
def suma(a: int, b: int) -> int:
    """Suma dos números enteros."""
    return a + b

mcp.run()  # ← usa STDIO por defecto
```

Config en `opencode.json`:
```json
{
    "mcp": {
        "mi_server": {
            "type": "local",
            "command": ["python", "mi_server.py"],
            "enabled": true
        }
    }
}
```

**Cómo funciona:** opencode lanza `python mi_server.py` como proceso hijo. Cada vez que necesita usar una herramienta, escribe un JSON en stdin. Tu script lee de stdin, procesa, y escribe la respuesta en stdout. opencode la lee. Simple, limpio.

### VoxelQuest (HTTP + SSE)

Este servidor Node.js monta un HTTP server en el puerto 9000. opencode no lo lanza — ya está corriendo aparte:

```json
{
    "mcp": {
        "voxelquest": {
            "type": "remote",
            "url": "http://localhost:9000/mcp"
        }
    }
}
```

**Problema:** si el server no está corriendo cuando opencode inicia, la conexión falla con timeout.

**Solución que implementamos:** un **bridge STDIO** (`mcp-bridge.js`) que opencode lanza como proceso local, y el bridge se encarga de:
1. Arrancar el VoxelQuest server si no está vivo
2. Leer JSON de stdin (como si fuera STDIO nativo)
3. Reenviar por HTTP al server real
4. Devolver la respuesta a stdout

```
opencode ←stdin/stdout→ mcp-bridge.js ←HTTP→ voxelquest-server.js
         ↑ type: local                  ↑ proceso separado
```

## Consejo pro

**Para desarrollo rápido** (scripts pequeños, tools ligeras): usa `type: local` con STDIO. Tu server MCP se lanza bajo demanda y se mata solo. Es lo que hace FastMCP por defecto.

**Para servidores pesados o persistentes** (juegos, bases de datos, APIs externas): usa `type: remote` con HTTP. Así el server vive independientemente de opencode.

**Si tu server es HTTP pero quieres usar `local` para que opencode lo gestione:** escribe un bridge STDIO como el que creamos (`mcp-bridge.js`). Es ~40 líneas y te ahorras el "operation timed out" de por vida.

### Bonus: la magia de los docstrings

En tu FastMCP, el `"""Suma dos números"""` se convierte automáticamente en el `description` que la IA ve al elegir herramientas. En el VoxelQuest server tuvimos que escribir `description` a mano en cada tool definition (línea 851-909 de `voxelquest-server.js`). El resultado es el mismo, pero FastMCP te ahorra el trabajo pesado.
