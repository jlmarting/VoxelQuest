# Contrato de tools MCP — Física de objetos

**Fecha:** 2026-08-09
**Estado:** Propuesta
**Relación con `definitions.json`:** estas tools se añadirán a `core/shared/tools/definitions.json` con `servers: ["python"]` en la fase 1. El stack Node.js queda fuera hasta decisión de paridad.

---

## Convenciones

- Coordenadas en **unidades de voxel** (float). `y` es arriba.
- `position` y `velocity` son `[x, y, z]` arrays.
- `rotation` es `[rx, ry, rz]` en radianes.
- `scale` es `[sx, sy, sz]` en unidades de voxel; admite fracciones (subvoxel).
- `color` es entero RGB (p. ej. `0xff8800`).
- `object_id` entero devuelto por `create_object`.
- Respuestas: `{ "success": true, "object_id": 7, ... }` o error MCP estándar.

---

## 1. create_object

Crea un `MobileObject`.

```json
{
  "kind": "box | sphere | sculpture | projectile | vehicle",
  "position": [10.0, 40.0, 10.0],
  "scale": [1.0, 1.0, 1.0],
  "rotation": [0, 0, 0],
  "color": 16744448,
  "mass": 1.0,
  "restitution": 0.3,
  "friction": 0.5,
  "health": 100,
  "destructible": false,
  "fragile": 0.0,
  "collision_group": 1,
  "collision_mask": 255,
  "anchored": false,
  "owner_id": null,
  "motion": { ... },
  "shape": { ... }
}
```

**Requeridos:** `kind`, `position`.
**Devuelve:** `{ "success": true, "object_id": <int> }`.

`motion` y `shape` son opcionales y se pueden asignar después con `update_object` / `move_object`.

### `shape` por kind

- `box`: `{ "type": "box" }` (se infiere de `scale`).
- `sphere`: `{ "type": "sphere", "radius": 0.5 }` (default `scale.x/2`).
- `sculpture`: ver §7 `create_sculpture`.
- `projectile`: `{ "type": "sphere", "radius": 0.2 }` por defecto.
- `vehicle`: `{ "type": "box" }`.

---

## 2. update_object

Modifica propiedades en caliente.

```json
{
  "object_id": 7,
  "patch": {
    "color": 65280,
    "mass": 2.0,
    "health": 50,
    "destructible": true,
    "visible": true,
    "anchored": false
  }
}
```

**Devuelve:** `{ "success": true, "object": <obj_dict> }`.

Cualquier campo del modelo `MobileObject` es parcheable excepto `id`.

---

## 3. move_object

Asigna un movimiento (cinemático o dinámico). Reemplaza el motion anterior.

```json
{
  "object_id": 7,
  "motion": {
    "type": "waypoints | dynamic | orbit | parametric | rotate | stop",
    "...": "ver presets"
  }
}
```

**Devuelve:** `{ "success": true, "motion": <motion_dict> }`.

Es el entry point genérico. Los presets siguientes son atajos que llaman a este.

---

## 4. move_linear

Línea recta con velocidad constante.

```json
{
  "object_id": 7,
  "velocity": [3.0, 0.0, 0.0],
  "loop": false,
  "expire_at": null
}
```

Internamente: `motion = { "type": "dynamic", "velocity": [...], "gravity": false, "expire_at": ... }`.

---

## 5. move_orbit

Órbita circular alrededor de un centro.

```json
{
  "object_id": 7,
  "center": [10.0, 40.0, 10.0],
  "radius": 5.0,
  "axis": "y",
  "angular_speed": 0.5,
  "loop": true
}
```

`axis`: `"x" | "y" | "z"` (eje de rotación). `angular_speed` en rad/s.

---

## 6. move_bounce

Rebote entre dos puntos.

```json
{
  "object_id": 7,
  "a": [10.0, 40.0, 10.0],
  "b": [20.0, 40.0, 10.0],
  "speed": 2.0,
  "easing": "linear"
}
```

`easing`: `"linear" | "sine" | "bounce"`.

---

## 7. move_projectile

Parábola con gravedad. Pensado para proyectiles.

```json
{
  "object_id": 7,
  "velocity": [5.0, 10.0, 0.0],
  "gravity": true,
  "expire_at": 5.0,
  "damage_on_impact": 5.0,
  "destroy_on_impact": true
}
```

Internamente marca `kind` como `projectile` si no lo era, y activa `destructible=true` con `fragile` mínimo.

---

## 8. move_rotate

Rotación continua sin traslación.

```json
{
  "object_id": 7,
  "angular_velocity": [0.0, 1.0, 0.0],
  "loop": true
}
```

`angular_velocity` en rad/s.

---

## 9. stop_motion

Detiene todo movimiento del objeto.

```json
{ "object_id": 7 }
```

Pone `velocity` y `angular_velocity` a 0 y quita el `motion`.

---

## 10. apply_impulse

Aplica un impulso instantáneo a un objeto dinámico (mass > 0).

```json
{
  "object_id": 7,
  "impulse": [0.0, 15.0, 0.0],
  "point": null
}
```

`point` opcional (relativo al centro) genera torque si no es cero.

---

## 11. damage_object

Aplica daño a un objeto destruible.

```json
{
  "object_id": 7,
  "amount": 25.0,
  "source_id": null
}
```

Si `health` llega a 0, el objeto se destruye y emite `object_destroyed`.

---

## 12. destroy_object

Destrucción manual inmediata.

```json
{ "object_id": 7, "cause": "manual" }
```

`cause` se refleja en el evento para logs/training.

---

## 13. list_objects

Lista todos los objetos activos.

```json
{ "filter": { "kind": "projectile", "owner_id": 2 } }
```

`filter` opcional. **Devuelve:** `{ "objects": [<obj_dict>, ...] }`.

---

## 14. get_object

Estado completo de un objeto.

```json
{ "object_id": 7 }
```

**Devuelve:** `{ "object": <obj_dict> }` incluyendo `motion`, `shape`, `health`, `velocity`.

---

## 15. create_sculpture

Wrapper de `create_object` para esculturas subvoxel.

```json
{
  "position": [10.0, 40.0, 10.0],
  "resolution": 4,
  "voxels": [
    { "x": 0.0, "y": 0.0, "z": 0.0, "color": 16711680, "size": 0.25 },
    { "x": 0.25, "y": 0.0, "z": 0.0, "color": 16711680, "size": 0.25 }
  ],
  "generator": null,
  "params": {},
  "anchored": true,
  "destructible": false,
  "color": 16711680
}
```

Dos modos:
- **voxels explícitos:** lista de `{x,y,z,color,size}` (coordenadas locales al `position`).
- **generator:** `"sphere" | "cube" | "pyramid" | "helix" | "cross" | "humanoid_bust"` con `params`.

`resolution`: subdivisiones por voxel (1, 2, 4, 8). Subvoxel size = `1/resolution`.

**Límites:** máx 4096 voxels por escultura (configurable en `constants.py`).

**Devuelve:** `{ "success": true, "object_id": <int>, "voxel_count": <int> }`.

---

## Esquema JSON Schema completo (para `definitions.json`)

Cada tool se añade a `definitions.json` con su `inputSchema` completo. Ejemplo para `create_object`:

```json
"create_object": {
  "description": "Crear un objeto móvil (box, sphere, sculpture, projectile, vehicle) con física de colisiones y opcionalmente destruible",
  "inputSchema": {
    "type": "object",
    "properties": {
      "kind": { "type": "string", "enum": ["box","sphere","sculpture","projectile","vehicle"] },
      "position": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
      "scale": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
      "rotation": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
      "color": { "type": "integer" },
      "mass": { "type": "number" },
      "restitution": { "type": "number" },
      "friction": { "type": "number" },
      "health": { "type": "number" },
      "destructible": { "type": "boolean" },
      "fragile": { "type": "number" },
      "collision_group": { "type": "integer" },
      "collision_mask": { "type": "integer" },
      "anchored": { "type": "boolean" },
      "owner_id": { "type": ["integer","null"] },
      "motion": { "type": "object" },
      "shape": { "type": "object" }
    },
    "required": ["kind", "position"]
  },
  "servers": ["python"],
  "category": "objects"
}
```

El resto de tools siguen el mismo patrón. La implementación final se añade a `definitions.json` en la fase de implementación.

---

## Categorización en `definitions.json`

Todas estas tools llevan `"category": "objects"` (nueva categoría) para distinguirlas de `world`, `player`, `combat`, etc.