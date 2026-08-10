/**
 * objects.js — Render de MobileObject (propuesta 002).
 *
 * Fase 1: render mínimo de box/sphere/vehicle/projectile con THREE.Mesh.
 * Sculpture se renderiza como placeholder (AABB) hasta Fase 6 (InstancedMesh).
 * FX de destrucción llegan en Fase 5.
 *
 * Consumo: lee state.objects[] aplicado por server-bridge.js (a continuación
 * se añade el pegamento). Esta clase no se sincroniza sola; el GameLoop del
 * cliente la llama via game.objectRenderer.syncFromServer(objects, scene).
 */
class ObjectRenderer {
    constructor() {
        this.objects = new Map(); // id -> { mesh, obj, kind }
        this.scene = null;
        // Interpolación de movimiento (el servidor manda a 20Hz, el cliente
        // renderiza a ~60FPS; sin esto los objetos "saltan"/parpadean).
        this.INTERP_DELAY = 0.05;          // 50ms de retardo = 1 tick
        this.INTERP_WINDOW = 0.05;         // ventana de suavizado (1 tick)
        this.TELEPORT_THRESHOLD = 5.0;     // >5 bloques de salto = teleport real
    }

    /**
     * Sincroniza la lista de objetos desde el servidor.
     * Crea/actualiza/elimina meshes según diff.
     */
    syncFromServer(serverObjects, scene, mcpUrl) {
        this.scene = scene;
        const seen = new Set();
        for (const so of serverObjects) {
            seen.add(so.id);
            let entry = this.objects.get(so.id);
            // Para sculptures: si ya existe pero llega un snapshot con voxels
            // completos (shape.voxels !== null), reemplazar la mesh.
            if (entry && entry.kind === 'sculpture' && so.shape && so.shape.voxels) {
                scene.remove(entry.mesh);
                this._disposeMesh(entry.mesh);
                this.objects.delete(so.id);
                entry = null;
            }
            // Para sculptures sin voxels en el snapshot: pedir los voxels
            // completos vía MCP una sola vez (el snapshot incremental no los
            // incluye para no saturar el WS). Si ya hay un fetch en curso o la
            // escultura ya está en escena, no re-crear el placeholder.
            if (!entry && so.kind === 'sculpture' && so.shape && so.shape.voxels === null) {
                if (this._fetchedSculptures && this._fetchedSculptures.has(so.id)) {
                    continue;
                }
                this._fetchSculptureVoxels(so, scene, mcpUrl);
                // Crear placeholder mientras llega la respuesta
                const mesh = this._createMesh(so);
                if (mesh) {
                    scene.add(mesh);
                    entry = this._makeEntry(so, mesh);
                    this.objects.set(so.id, entry);
                }
            }
            if (!entry) {
                const mesh = this._createMesh(so);
                if (!mesh) continue;
                scene.add(mesh);
                entry = this._makeEntry(so, mesh);
                this.objects.set(so.id, entry);
            }
            entry.obj = so;
            this._updateInterpolationTarget(entry, so);
            this._updateMesh(entry, so);
        }
        // Eliminar los que ya no están
        for (const [id, entry] of this.objects) {
            if (!seen.has(id)) {
                scene.remove(entry.mesh);
                this._disposeMesh(entry.mesh);
                this.objects.delete(id);
            }
        }
    }

    /** Crea una entrada de objeto con estado de interpolación inicializado. */
    _makeEntry(so, mesh) {
        const pos = new THREE.Vector3(so.position[0], so.position[1], so.position[2]);
        return {
            mesh,
            obj: so,
            kind: so.kind,
            prevPos: pos.clone(),
            targetPos: pos.clone(),
            snapTime: performance.now() / 1000,
        };
    }

    /** Actualiza el target de interpolación desde un snapshot del servidor. */
    _updateInterpolationTarget(entry, so) {
        const newPos = new THREE.Vector3(so.position[0], so.position[1], so.position[2]);
        if (!entry.targetPos) {
            // Primer snapshot: sin interpolación, posicionar directo
            entry.prevPos = newPos.clone();
            entry.targetPos = newPos.clone();
            entry.snapTime = performance.now() / 1000;
            return;
        }
        // Teleport real (distancia grande): saltar sin interpolar
        if (entry.targetPos.distanceTo(newPos) > this.TELEPORT_THRESHOLD) {
            entry.prevPos = newPos.clone();
        } else {
            entry.prevPos = entry.targetPos.clone();
        }
        entry.targetPos = newPos.clone();
        entry.snapTime = performance.now() / 1000;
    }

    /**
     * Interpola las posiciones de todos los objetos hacia su target.
     * Se llama cada frame desde el bucle animate() del cliente.
     */
    tickInterpolation(deltaTime) {
        const now = performance.now() / 1000;
        for (const [, entry] of this.objects) {
            if (!entry.targetPos || !entry.prevPos) continue;
            const mesh = entry.mesh;
            if (!mesh) continue;
            const elapsed = now - entry.snapTime - this.INTERP_DELAY;
            let alpha = elapsed / this.INTERP_WINDOW;
            if (alpha <= 0) {
                // Aún no toca moverse (delay de interpolación)
                mesh.position.set(entry.prevPos.x, entry.prevPos.y, entry.prevPos.z);
                continue;
            }
            if (alpha >= 1) {
                // Llegado al target: posicionar exacto y resetear para evitar drift
                mesh.position.set(entry.targetPos.x, entry.targetPos.y, entry.targetPos.z);
                entry.prevPos = entry.targetPos.clone();
                continue;
            }
            mesh.position.lerpVectors(entry.prevPos, entry.targetPos, alpha);
        }
    }

    /** Pide los voxels completos de una escultura vía MCP y reemplaza la mesh. */
    _fetchSculptureVoxels(so, scene, mcpUrl) {
        if (this._fetchedSculptures && this._fetchedSculptures.has(so.id)) return;
        if (!this._fetchedSculptures) this._fetchedSculptures = new Set();
        this._fetchedSculptures.add(so.id);
        const url = mcpUrl || 'http://localhost:9000/mcp';
        console.log('[Objects] Solicitando voxels de escultura id=' + so.id);
        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/call',
                params: { name: 'get_object', arguments: { object_id: so.id } } })
        }).then(r => r.json()).then(resp => {
            const text = resp.content && resp.content[0] && resp.content[0].text;
            if (!text) return;
            const data = JSON.parse(text);
            const obj = data.object;
            if (!obj || !obj.shape || !obj.shape.voxels) return;
            console.log('[Objects] Voxels recibidos:', obj.shape.voxels.length, 'para id=' + so.id);
            // Reemplazar la mesh placeholder
            const entry = this.objects.get(so.id);
            if (entry) {
                scene.remove(entry.mesh);
                this._disposeMesh(entry.mesh);
                const newMesh = this._createSculptureMesh(obj, obj.shape.voxels);
                scene.add(newMesh);
                entry.mesh = newMesh;
                this._updateMesh(entry, obj);
            }
        }).catch(err => console.error('[Objects] Error al pedir voxels:', err));
    }

    _createMesh(so) {
        const scale = so.scale || [1, 1, 1];
        // NPCs: objetos box con proporciones humanas (alto ~1.8, ancho ~0.6)
        // se renderizan con PlayerModel (aspecto de jugador) en vez de cajas.
        if (so.kind === 'box' && this._isHumanoid(so)) {
            return this._createNpcModel(so);
        }
        let geo;
        const color = so.color != null ? so.color : 0xffffff;
        const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0.1 });
        if (so.kind === 'sphere' || so.kind === 'projectile') {
            const r = (so.shape && so.shape.radius) != null ? so.shape.radius : scale[0] * 0.5;
            geo = new THREE.SphereGeometry(Math.max(0.05, r), 16, 12);
            if (so.emissive) {
                mat.emissive = new THREE.Color(color);
                mat.emissiveIntensity = 1.0;
            }
        } else if (so.kind === 'sculpture') {
            const voxels = (so.shape && so.shape.voxels) || null;
            if (voxels && voxels.length > 0) {
                return this._createSculptureMesh(so, voxels);
            }
            // Sin voxels (snapshot incremental): placeholder envolvente
            geo = new THREE.BoxGeometry(Math.max(0.05, scale[0]), Math.max(0.05, scale[1]), Math.max(0.05, scale[2]));
            mat.transparent = true;
            mat.opacity = 0.35;
            mat.color.setHex(0xff8800);
        } else {
            geo = new THREE.BoxGeometry(Math.max(0.05, scale[0]), Math.max(0.05, scale[1]), Math.max(0.05, scale[2]));
        }
        const mesh = new THREE.Mesh(geo, mat);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        return mesh;
    }

    /** Detecta si un objeto box tiene proporciones humanas (NPC). */
    _isHumanoid(so) {
        const s = so.scale || [1, 1, 1];
        // Alto ~1.8, ancho/profundidad ~0.6 (proporciones de jugador)
        return s[1] >= 1.5 && s[0] <= 0.9 && s[2] <= 0.9;
    }

    /** Crea un PlayerModel con aspecto variado según el color del NPC. */
    _createNpcModel(so) {
        const color = so.color != null ? so.color : 0x808080;
        // Derivar configuración del color de ropa (camisa)
        const config = this._npcConfigFromColor(color, so.id);
        const model = new PlayerModel(so.id, this.scene, config);
        // El constructor de PlayerModel añade el grupo a la escena;
        // syncFromServer lo añadirá de nuevo, así que lo quitamos aquí.
        if (this.scene) this.scene.remove(model.group);
        // Eliminar la etiqueta de nombre (sprite transparente causa parpadeo)
        if (model.nameTag) {
            model.group.remove(model.nameTag);
            if (model.nameTag.material) model.nameTag.material.dispose();
            model.nameTag = null;
        }
        // Eliminar la luz individual (PointLight por NPC causa parpadeo/rendimiento)
        if (model.light) {
            model.group.remove(model.light);
            model.light = null;
        }
        // Guardar referencia al grupo y al modelo para actualizarlo/animarlo
        model.group.userData.isNpc = true;
        model.group.userData.npcId = so.id;
        model.group.userData.npcModel = model;
        return model.group;
    }

    /** Genera una configuración de NPC variada a partir del color de ropa. */
    _npcConfigFromColor(color, id) {
        // Paleta de pieles
        const skins = [0xf5c6a0, 0xfdd9b5, 0xe8b88a, 0xd9a066, 0xc68642];
        // Paleta de colores de pelo
        const hairs = [0x3d2314, 0x8b4513, 0x1a1a1a, 0x6b4226, 0x2c2c2c, 0x9b7a4f];
        // Paleta de colores de pantalón
        const pants = [0x333366, 0x444466, 0x2f4f4f, 0x556b2f, 0x4a3728, 0x3b3b3b];
        // Estilos de pelo
        const maleStyles = ['short', 'mohawk', 'undercut', 'bald', 'punk'];
        const femaleStyles = ['long', 'ponytail', 'bun', 'braids', 'bob'];
        // Vello facial
        const facial = ['none', 'mustache', 'beard', 'goatee', 'stubble'];

        // Semilla determinista por id para que el aspecto sea estable
        const seed = (id * 2654435761) >>> 0;
        const rnd = (n) => {
            const x = Math.sin(seed + n * 12.9898) * 43758.5453;
            return x - Math.floor(x);
        };

        const isFemale = rnd(1) < 0.4;
        const skinColor = skins[Math.floor(rnd(2) * skins.length)];
        const hairColor = hairs[Math.floor(rnd(3) * hairs.length)];
        const eyeColor = [0x4a90d9, 0x50c878, 0x8b6914, 0x5c4033, 0x2c2c2c][Math.floor(rnd(4) * 5)];
        const pantsColor = pants[Math.floor(rnd(5) * pants.length)];
        const shoeColor = 0x222222;

        const config = {
            name: 'NPC',
            gender: isFemale ? 'female' : 'male',
            skinColor,
            hairColor,
            eyeColor,
            shirtColor: color,  // el color del objeto es la camisa
            pantsColor,
            shoeColor,
        };

        if (isFemale) {
            config.hairStyle = femaleStyles[Math.floor(rnd(6) * femaleStyles.length)];
            config.accessory = ['none', 'necklace', 'earrings', 'bow'][Math.floor(rnd(7) * 4)];
            config.pantsType = rnd(8) < 0.5 ? 'skirt' : 'pants';
        } else {
            config.hairStyle = maleStyles[Math.floor(rnd(6) * maleStyles.length)];
            config.facialHair = facial[Math.floor(rnd(7) * facial.length)];
        }
        return config;
    }

    /** Crea una escultura como grupo de InstancedMesh agrupados por color. */
    _createSculptureMesh(so, voxels) {
        const group = new THREE.Group();
        const pos = so.position || [0, 0, 0];
        group.position.set(pos[0], pos[1], pos[2]);
        const rot = so.rotation || [0, 0, 0];
        group.rotation.set(rot[0], rot[1], rot[2]);

        // Agrupar por color
        const byColor = new Map();
        for (const v of voxels) {
            const c = v.color != null ? v.color : (so.color != null ? so.color : 0xff8800);
            if (!byColor.has(c)) byColor.set(c, []);
            byColor.get(c).push(v);
        }

        // Crear un InstancedMesh por color
        group.userData.instancedMeshes = [];
        for (const [color, vs] of byColor) {
            const size = vs[0].size || 0.25;
            const cubeGeo = new THREE.BoxGeometry(size, size, size);
            const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.7, metalness: 0.1 });
            const inst = new THREE.InstancedMesh(cubeGeo, mat, vs.length);
            inst.castShadow = true;
            inst.receiveShadow = true;
            const m = new THREE.Matrix4();
            for (let i = 0; i < vs.length; i++) {
                m.makeTranslation(vs[i].x, vs[i].y, vs[i].z);
                inst.setMatrixAt(i, m);
            }
            inst.instanceMatrix.needsUpdate = true;
            group.add(inst);
            group.userData.instancedMeshes.push(inst);
        }
        group.userData.isSculpture = true;
        return group;
    }

    _updateMesh(entry, so) {
        const mesh = entry.mesh;
        const pos = so.position || [0, 0, 0];
        const rot = so.rotation || [0, 0, 0];
        // La posición se interpola en tickInterpolation(); aquí solo rotación,
        // visibilidad, color y animaciones.
        // NPC (PlayerModel group): rotar y animar (posición la pone la interpolación)
        if (entry.kind === 'box' && mesh.userData && mesh.userData.isNpc) {
            mesh.rotation.y = rot[1] || 0;
            mesh.visible = so.visible !== false;
            // Animar el modelo (movimiento de piernas/brazos) si se mueve
            const model = mesh.userData.npcModel;
            if (model && model.update) {
                const dt = 0.05;
                const moving = !!(so.velocity && (so.velocity[0] || so.velocity[2]));
                model.update(mesh.position, { y: rot[1] || 0 }, dt, moving);
            }
            return;
        }
        // Sculpture: Group con rotation propio; la posición la interpola tickInterpolation.
        if (entry.kind === 'sculpture' && mesh.userData.isSculpture) {
            mesh.rotation.set(rot[0], rot[1], rot[2]);
            mesh.visible = so.visible !== false;
            return;
        }
        mesh.rotation.set(rot[0], rot[1], rot[2]);
        mesh.visible = so.visible !== false;
        if (so.color != null && entry.kind !== 'sculpture') {
            mesh.material.color.setHex(so.color);
        }
        // Luz: si el objeto emite luz, añadir/actualizar PointLight
        if (so.emissive) {
            if (!entry.light) {
                entry.light = new THREE.PointLight(so.color != null ? so.color : 0xffffff, 2.0, 40, 1.5);
                mesh.add(entry.light);
            }
        } else if (entry.light) {
            mesh.remove(entry.light);
            entry.light = null;
        }
        // Salud baja → parpadeo rojo (si es destruible)
        if (so.destructible && typeof so.health === 'number' && typeof so.max_health === 'number' && so.max_health > 0) {
            const ratio = so.health / so.max_health;
            if (ratio < 0.4 && entry.kind !== 'sculpture') {
                const flash = Math.sin(Date.now() * 0.02) * 0.5 + 0.5;
                mesh.material.emissive = mesh.material.emissive || new THREE.Color();
                mesh.material.emissive.setRGB(flash * (1 - ratio), 0, 0);
                mesh.material.needsUpdate = true;
            }
        }
    }

    _disposeMesh(mesh) {
        if (mesh.userData && mesh.userData.isNpc) {
            // PlayerModel group: dispose todos los hijos
            mesh.traverse(child => {
                if (child.geometry) child.geometry.dispose();
                if (child.material) {
                    if (child.material.map) child.material.map.dispose();
                    child.material.dispose();
                }
            });
            return;
        }
        if (mesh.userData && mesh.userData.isSculpture) {
            // Group: dispose todos los InstancedMesh hijos
            for (const child of mesh.children) {
                if (child.geometry) child.geometry.dispose();
                if (child.material) child.material.dispose();
            }
            return;
        }
        if (mesh.geometry) mesh.geometry.dispose();
        if (mesh.material) mesh.material.dispose();
    }

    /** Limpia todo (al desconectar). */
    clear(scene) {
        for (const [, entry] of this.objects) {
            scene.remove(entry.mesh);
            this._disposeMesh(entry.mesh);
        }
        this.objects.clear();
    }

    /** Procesa un evento object_destroyed y lanza FX visual. */
    handleDestroyedEvent(ev, scene) {
        const fx = ev.fx || 'poof';
        const pos = ev.position || [0, 0, 0];
        if (fx === 'explosion_small') {
            this._spawnExplosion(pos, scene, 0x884422, 0.6, 30, 0.8);
        } else if (fx === 'break') {
            this._spawnExplosion(pos, scene, 0x888888, 0.4, 20, 0.6);
        } else { // poof
            this._spawnPoof(pos, scene);
        }
    }

    /** Procesa eventos de colisión (opcional: pequeña chispa). */
    handleCollidedEvent(ev, scene) {
        // Fase 5: chispa sutil al impactar; solo log si impact_speed bajo
        if (!ev.impact_speed || ev.impact_speed < 2) return;
        // Sin posición en el evento; omitir FX por ahora (el evento lleva id)
    }

    _spawnExplosion(pos, scene, colorHex, scale, count, duration) {
        const geo = new THREE.BufferGeometry();
        const positions = new Float32Array(count * 3);
        const velocities = [];
        for (let i = 0; i < count; i++) {
            positions[i*3] = pos[0];
            positions[i*3+1] = pos[1];
            positions[i*3+2] = pos[2];
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);
            const v = scale * (0.5 + Math.random());
            velocities.push([
                v * Math.sin(phi) * Math.cos(theta),
                v * Math.cos(phi),
                v * Math.sin(phi) * Math.sin(theta),
            ]);
        }
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const mat = new THREE.PointsMaterial({ color: colorHex, size: 0.15, transparent: true, opacity: 1.0 });
        const points = new THREE.Points(geo, mat);
        scene.add(points);
        const start = performance.now();
        const update = () => {
            const t = (performance.now() - start) / 1000;
            if (t >= duration) {
                scene.remove(points);
                geo.dispose();
                mat.dispose();
                return;
            }
            const arr = geo.attributes.position.array;
            for (let i = 0; i < count; i++) {
                arr[i*3] += velocities[i][0] * 0.016;
                arr[i*3+1] += velocities[i][1] * 0.016 - 9.8 * 0.016 * t;
                arr[i*3+2] += velocities[i][2] * 0.016;
            }
            geo.attributes.position.needsUpdate = true;
            mat.opacity = 1.0 - t / duration;
            requestAnimationFrame(update);
        };
        update();
    }

    _spawnPoof(pos, scene) {
        const geo = new THREE.SphereGeometry(0.2, 8, 6);
        const mat = new THREE.MeshBasicMaterial({ color: 0xcccccc, transparent: true, opacity: 0.8 });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(pos[0], pos[1], pos[2]);
        scene.add(mesh);
        const start = performance.now();
        const duration = 0.5;
        const update = () => {
            const t = (performance.now() - start) / 1000;
            if (t >= duration) {
                scene.remove(mesh);
                geo.dispose();
                mat.dispose();
                return;
            }
            const s = 1 + t * 3;
            mesh.scale.set(s, s, s);
            mat.opacity = 0.8 * (1 - t / duration);
            requestAnimationFrame(update);
        };
        update();
    }
}

window.ObjectRenderer = ObjectRenderer;