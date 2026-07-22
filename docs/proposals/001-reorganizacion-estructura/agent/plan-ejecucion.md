# Plan de Ejecución

**Fecha:** 2026-07-22  
**Estado:** Pendiente aprobación

## Resumen

Reorganizar la estructura del proyecto para separar claramente los dos stacks (Node.js y Python), establecer un contrato compartido de tools MCP, y facilitar el mantenimiento y evolución del proyecto.

## Fases

### Fase 1: Crear estructura de carpetas (30 min)

**Objetivo:** Crear la nueva estructura sin mover código aún.

```bash
# Crear carpetas base
mkdir -p core/shared/tools
mkdir -p core/node/web
mkdir -p core/python
mkdir -p core/docs/proposals

# Crear contrato vacío
echo '{"version": "1.0.0", "tools": {}}' > core/shared/tools/definitions.json
```

**Verificación:**
- [ ] Estructura de carpetas creada
- [ ] `definitions.json` inicializado

---

### Fase 2: Mover stack Node.js (45 min)

**Objetivo:** Mover todo el código Node.js a `core/node/`.

**Archivos a mover:**
```bash
# Servidor
mv minecraft-clone/game-server.js core/node/
mv minecraft-clone/mcp-server.js core/node/
mv minecraft-clone/bt-engine.js core/node/
mv minecraft-clone/package.json core/node/
mv minecraft-clone/package-lock.json core/node/
mv minecraft-clone/node_modules core/node/

# Cliente web
mv minecraft-clone/index.html core/node/web/
mv minecraft-clone/css core/node/web/
mv minecraft-clone/js core/node/web/

# Recursos
mv minecraft-clone/textures core/node/web/  # si no está vacío
```

**Ajustes necesarios:**
- [ ] Actualizar rutas en `game-server.js` para servir `web/` en lugar de raíz
- [ ] Actualizar `mcp-server.js` si referencia rutas relativas
- [ ] Verificar que `bt-engine.js` sigue funcionando
- [ ] Probar `node game-server.js` desde `core/node/`

**Verificación:**
- [ ] `cd core/node && node game-server.js` arranca sin errores
- [ ] Cliente web accesible en `http://localhost:9000`
- [ ] MCP funciona vía `mcp-server.js`
- [ ] WebSocket relay funciona

---

### Fase 3: Mover stack Python (45 min)

**Objetivo:** Mover todo el código Python a `core/python/`.

**Archivos a mover:**
```bash
# Servidor
mv minecraft-clone/server core/python/
mv minecraft-clone/pyproject.toml core/python/
mv minecraft-clone/uv.lock core/python/
mv minecraft-clone/.python-version core/python/
mv minecraft-clone/.venv core/python/

# Cliente thin
mv minecraft-clone/client core/python/

# Scripts
mv minecraft-clone/scripts core/python/

# Training
mv minecraft-clone/training core/python/

# Utilidades
mv minecraft-clone/server.py core/python/
mv minecraft-clone/run.sh core/python/
```

**Ajustes necesarios:**
- [ ] Actualizar imports en `server/main.py` si usan rutas relativas
- [ ] Actualizar `run.sh` para usar rutas correctas
- [ ] Verificar que `pyproject.toml` apunta a `server/` correctamente
- [ ] Probar `uv run python -m server.main` desde `core/python/`

**Verificación:**
- [ ] `cd core/python && uv run python -m server.main` arranca sin errores
- [ ] Cliente thin accesible en `http://localhost:8080`
- [ ] MCP funciona vía `POST /mcp`
- [ ] WebSocket funciona
- [ ] Scripts ejecutan correctamente (aunque fallen por tools faltantes)

---

### Fase 4: Mover documentación compartida (15 min)

**Objetivo:** Mover docs a `core/docs/`.

```bash
mv minecraft-clone/docs core/docs
mv minecraft-clone/CHANGELOG.md core/
mv minecraft-clone/README.md core/
```

**Ajustes necesarios:**
- [ ] Actualizar referencias en `AGENTS.md` (raíz del proyecto)
- [ ] Actualizar referencias en `opencode.json` si aplica

**Verificación:**
- [ ] Docs accesibles en `core/docs/`
- [ ] Propuestas en `core/docs/proposals/`

---

### Fase 5: Crear contrato de tools (2-3 horas)

**Objetivo:** Extraer definiciones de tools de ambos servidores a `shared/tools/definitions.json`.

**Pasos:**

1. **Extraer tools de Node.js:**
   ```bash
   # Leer game-server.js y extraer todas las definiciones de tools
   # Hay ~51 tools definidos con tool(description, schema, fn)
   ```

2. **Extraer tools de Python:**
   ```bash
   # Leer server/mcp/server.py y extraer list_tools()
   # Hay ~14 tools definidos
   ```

3. **Unificar en definitions.json:**
   - Para cada tool, crear entrada con:
     - `description`: del servidor original
     - `inputSchema`: del servidor original
     - `servers`: `["node"]`, `["python"]`, o `["node", "python"]`
     - `category`: clasificar (world, player, combat, navigation, bt)

4. **Validar:**
   - [ ] Todos los tools de Node.js están en `definitions.json`
   - [ ] Todos los tools de Python están en `definitions.json`
   - [ ] No hay conflictos de nombres
   - [ ] Schemas son compatibles (mismo tool en ambos servidores tiene mismo schema)

**Verificación:**
- [ ] `definitions.json` contiene todos los tools
- [ ] Campo `servers` indica correctamente qué backend implementa cada tool
- [ ] Schemas son válidos JSON Schema

---

### Fase 6: Adaptar servidores al contrato (1-2 horas)

**Objetivo:** Que ambos servidores carguen `definitions.json` en lugar de definir tools inline.

**Node.js (`game-server.js`):**
- [ ] Cargar `../shared/tools/definitions.json`
- [ ] Filtrar tools con `servers.includes('node')`
- [ ] Registrar solo esos tools
- [ ] Mantener handlers existentes

**Python (`server/mcp/server.py`):**
- [ ] Cargar `../../shared/tools/definitions.json`
- [ ] Filtrar tools con `'python' in servers`
- [ ] Retornar esos tools en `list_tools()`
- [ ] Mantener handlers existentes

**Verificación:**
- [ ] Node.js sigue exponiendo los mismos tools que antes
- [ ] Python sigue exponiendo los mismos tools que antes
- [ ] MCP funciona en ambos servidores
- [ ] Scripts ejecutan correctamente

---

### Fase 7: Limpiar y renombrar (15 min)

**Objetivo:** Eliminar `minecraft-clone/` y renombrar a `core/`.

```bash
# Verificar que minecraft-clone/ está vacío
ls minecraft-clone/

# Si quedan archivos, moverlos o eliminarlos
# Luego:
mv minecraft-clone core
```

**Ajustes finales:**
- [ ] Actualizar `AGENTS.md` con nueva estructura
- [ ] Actualizar `opencode.json` si referencia rutas
- [ ] Actualizar `.gitignore` si es necesario
- [ ] Actualizar README si existe

**Verificación:**
- [ ] No existe `minecraft-clone/`
- [ ] `core/` contiene toda la estructura
- [ ] Ambos stacks funcionan desde sus nuevas ubicaciones

---

### Fase 8: Documentar y comunicar (30 min)

**Objetivo:** Documentar la nueva estructura y comunicar cambios.

**Documentación a crear:**
- [ ] `core/README.md` con overview de la estructura
- [ ] `core/node/README.md` con instrucciones del stack Node.js
- [ ] `core/python/README.md` con instrucciones del stack Python
- [ ] `core/shared/tools/README.md` explicando el contrato

**Documentación a actualizar:**
- [ ] `AGENTS.md` con nuevas rutas
- [ ] `CHANGELOG.md` con entrada "Refactor: reorganización de estructura"

**Verificación:**
- [ ] Documentación clara y completa
- [ ] Instrucciones de desarrollo funcionan

---

## Riesgos y mitigaciones

### Riesgo 1: Ruptura de rutas relativas
**Probabilidad:** Alta  
**Impacto:** Medio  
**Mitigación:** Probar cada stack después de mover. Buscar `../` y `./` en el código.

### Riesgo 2: Scripts dejan de funcionar
**Probabilidad:** Alta (ya usan tools solo en Node.js)  
**Impacto:** Bajo (no es crítico ahora)  
**Mitigación:** Documentar que scripts requieren stack Node.js por ahora.

### Riesgo 3: Conflicto de puertos persiste
**Probabilidad:** Media  
**Impacto:** Bajo  
**Mitigación:** Documentar que cada stack usa puerto diferente en desarrollo.

### Riesgo 4: Pérdida de historial git
**Probabilidad:** Baja (si se usa `git mv`)  
**Impacto:** Medio  
**Mitigación:** Usar `git mv` en lugar de `mv` para preservar historial.

---

## Estimación total

| Fase | Tiempo | Dependencias |
|------|--------|--------------|
| 1. Crear estructura | 30 min | Ninguna |
| 2. Mover Node.js | 45 min | Fase 1 |
| 3. Mover Python | 45 min | Fase 1 |
| 4. Mover docs | 15 min | Fases 2, 3 |
| 5. Crear contrato | 2-3 horas | Fases 2, 3 |
| 6. Adaptar servidores | 1-2 horas | Fase 5 |
| 7. Limpiar y renombrar | 15 min | Fases 2, 3, 4 |
| 8. Documentar | 30 min | Fase 7 |

**Total estimado:** 6-8 horas

---

## Criterios de éxito

- [ ] Estructura de carpetas clara y lógica
- [ ] Ambos stacks funcionan independientemente
- [ ] Contrato de tools compartido funciona
- [ ] Documentación actualizada
- [ ] No se pierde funcionalidad existente
- [ ] Scripts siguen ejecutando (aunque con limitaciones conocidas)

---

## Próximos pasos (post-reorganización)

1. **Paridad de tools:** Implementar en Python los tools que usan los scripts
2. **Cliente unificado:** Evaluar si se puede unificar `node/web/` y `python/client/`
3. **Validación automática:** Crear script que valide contrato de tools
4. **Migración gradual:** Decidir si se migra de Node.js a Python o se mantienen ambos
