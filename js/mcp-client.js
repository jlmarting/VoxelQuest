/**
 * VoxelQuest MCP Client
 * 
 * Sincroniza el estado del juego con el servidor MCP.
 * Permite que agentes IA controlen jugadores remotamente.
 */

class MCPClient {
    constructor(game) {
        this.game = game;
        this.connected = false;
        this.ws = null;
        // Conectar al mismo host que sirve el juego
        this.serverUrl = `ws://${window.location.hostname || 'localhost'}:${window.location.port || 9000}`;
        this.syncInterval = null;
        this.playerStates = {};
        this.pathfinder = new Pathfinder(game.world);
        this.follower = new PathFollower();
        this.pendingResponse = null;
    }

    update(deltaTime) {
        this.follower.tick();
        if (this.follower.state === 'COMPLETE' && this.pendingResponse) {
            this.sendAsyncResponse(this.pendingResponse);
            this.pendingResponse = null;
        }
    }

    sendAsyncResponse(response) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(response));
        }
    }

    // Conectar al servidor MCP
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(this.serverUrl);
                
                this.ws.onopen = () => {
                    this.connected = true;
                    console.log('[MCP] Conectado al servidor');
                    this.startSync();
                    resolve();
                };
                
                this.ws.onmessage = (event) => {
                    this.handleMessage(JSON.parse(event.data));
                };
                
                this.ws.onclose = () => {
                    this.connected = false;
                    console.log('[MCP] Desconectado');
                    this.stopSync();
                };
                
                this.ws.onerror = (error) => {
                    console.error('[MCP] Error:', error);
                    reject(error);
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    // Manejar mensajes del servidor (comandos/consultas relay)
    handleMessage(data) {
        console.log('[MCP] Mensaje recibido:', JSON.stringify(data).substring(0, 100));

        let response = { id: data.id };
        const method = data.method;
        const params = data.params || {};

        try {
            const player = this.getPlayer(params.player_id);

            switch (method) {
                case 'move_player':
                case 'teleport':
                    if (!player) { response.error = 'Player not found'; break; }
                    player.position.set(params.x, params.y, params.z);
                    response.success = true;
                    response.position = this.toPos(player.position);
                    break;

                case 'move_relative': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const rot = player.rotation || { x: 0, y: 0 };
                    const dist = params.distance || 1;
                    const fwd = { x: -Math.sin(rot.y), z: -Math.cos(rot.y) };
                    const right = { x: Math.cos(rot.y), z: -Math.sin(rot.y) };
                    let dx = 0, dz = 0;
                    if (params.forward) { dx += fwd.x * dist; dz += fwd.z * dist; }
                    if (params.backward) { dx -= fwd.x * dist; dz -= fwd.z * dist; }
                    if (params.left) { dx -= right.x * dist; dz -= right.z * dist; }
                    if (params.right) { dx += right.x * dist; dz += right.z * dist; }
                    player.position.x += dx;
                    player.position.z += dz;
                    response.success = true;
                    response.position = this.toPos(player.position);
                    break;
                }

                case 'jump': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const h = params.height || 3;
                    player.position.y += h;
                    setTimeout(() => { if (player) player.position.y -= h; }, 500);
                    response.success = true;
                    response.position = this.toPos(player.position);
                    break;
                }

                case 'look':
                    if (!player) { response.error = 'Player not found'; break; }
                    const rot = player.rotation || { x: 0, y: 0 };
                    if (params.yaw !== undefined) rot.y = params.yaw;
                    if (params.pitch !== undefined) rot.x = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, params.pitch));
                    if (params.yaw_delta) rot.y += params.yaw_delta;
                    if (params.pitch_delta) rot.x = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, rot.x + params.pitch_delta));
                    response.success = true;
                    response.rotation = this.toPos(rot);
                    break;

                case 'get_rotation':
                    if (!player) { response.error = 'Player not found'; break; }
                    response.rotation = this.toPos(player.rotation || { x: 0, y: 0 });
                    break;

                case 'toggle_fly':
                    if (!player) { response.error = 'Player not found'; break; }
                    player.isFlying = !player.isFlying;
                    response.success = true;
                    response.isFlying = player.isFlying;
                    break;

                case 'fly_up':
                    if (!player) { response.error = 'Player not found'; break; }
                    if (!player.isFlying) { response.error = 'Jugador no está volando'; break; }
                    player.position.y += (params.distance || 1);
                    response.success = true;
                    response.position = this.toPos(player.position);
                    break;

                case 'fly_down':
                    if (!player) { response.error = 'Player not found'; break; }
                    if (!player.isFlying) { response.error = 'Jugador no está volando'; break; }
                    player.position.y -= (params.distance || 1);
                    response.success = true;
                    response.position = this.toPos(player.position);
                    break;

                case 'toggle_camera':
                    if (!player) { response.error = 'Player not found'; break; }
                    player.cameraMode = ((player.cameraMode || 0) + 1) % 3;
                    response.success = true;
                    response.cameraMode = player.cameraMode;
                    break;

                case 'select_slot':
                    if (!player) { response.error = 'Player not found'; break; }
                    if (params.slot < 0 || params.slot > 8) { response.error = 'Slot inválido (0-8)'; break; }
                    player.selectedSlot = params.slot;
                    response.success = true;
                    response.selectedSlot = player.selectedSlot;
                    break;

                case 'next_slot':
                    if (!player) { response.error = 'Player not found'; break; }
                    player.selectedSlot = ((player.selectedSlot || 0) + 1) % 9;
                    response.success = true;
                    response.selectedSlot = player.selectedSlot;
                    break;

                case 'prev_slot':
                    if (!player) { response.error = 'Player not found'; break; }
                    player.selectedSlot = ((player.selectedSlot || 0) + 8) % 9;
                    response.success = true;
                    response.selectedSlot = player.selectedSlot;
                    break;

                case 'place_block':
                    this.game.world.setBlock(params.x, params.y, params.z, params.type);
                    response.success = true;
                    response.position = { x: params.x, y: params.y, z: params.z };
                    break;

                case 'break_block': {
                    const block = this.game.world.getBlock(params.x, params.y, params.z);
                    this.game.world.setBlock(params.x, params.y, params.z, 0);
                    response.success = true;
                    response.blockType = block;
                    break;
                }

                case 'apply_blocks': {
                    const blocks = params.blocks || [];
                    blocks.forEach(b => this.game.world.setBlock(b.x, b.y, b.z, b.type));
                    response.success = true;
                    response.blocksPlaced = blocks.length;
                    break;
                }

                case 'place_block_as_player': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const hit = this.raycastFromPlayer(player);
                    if (!hit || !hit.face) { response.error = 'No hay bloque cerca para colocar'; break; }
                    const f = hit.face;
                    this.game.world.setBlock(f.x, f.y, f.z, params.type || 1);
                    response.success = true;
                    response.position = { x: f.x, y: f.y, z: f.z };
                    break;
                }

                case 'break_block_as_player': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const hit = this.raycastFromPlayer(player);
                    if (!hit) { response.error = 'No hay bloque cerca para romper'; break; }
                    if (hit.block === 10) { response.error = 'No se puede romper bedrock'; break; }
                    this.game.world.setBlock(hit.hit.x, hit.hit.y, hit.hit.z, 0);
                    response.success = true;
                    response.position = hit.hit;
                    response.blockType = hit.block;
                    break;
                }

                case 'get_block':
                    response.x = params.x; response.y = params.y; response.z = params.z;
                    response.type = this.game.world.getBlock(params.x, params.y, params.z);
                    break;

                case 'get_height': {
                    let h = 0;
                    for (let y = 63; y >= 0; y--) {
                        const b = this.game.world.getBlock(params.x, y, params.z);
                        if (b !== 0) { h = y; response.blockType = b; break; }
                    }
                    response.x = params.x; response.z = params.z; response.height = h;
                    break;
                }

                case 'get_blocks_in_area': {
                    const blocks = [];
                    const { x1, y1, z1, x2, y2, z2 } = params;
                    for (let x = x1; x <= x2; x++)
                        for (let y = y1; y <= y2; y++)
                            for (let z = z1; z <= z2; z++) {
                                const b = this.game.world.getBlock(x, y, z);
                                if (b !== 0) blocks.push({ x, y, z, type: b });
                            }
                    response.blocks = blocks; response.count = blocks.length;
                    break;
                }

                case 'flat_terrain': {
                    const { x, z, width, depth, height = 30, baseY = 0 } = params;
                    let removed = 0;
                    for (let dx = 0; dx < width; dx++)
                        for (let dz = 0; dz < depth; dz++)
                            for (let dy = 0; dy < height; dy++) {
                                const b = this.game.world.getBlock(x + dx, baseY + dy, z + dz);
                                if (b !== 0 && b !== 7) { this.game.world.setBlock(x + dx, baseY + dy, z + dz, 0); removed++; }
                            }
                    response.success = true; response.blocksRemoved = removed;
                    break;
                }

                case 'plant_tree': {
                    const { x, z } = params;
                    let baseY = 0;
                    for (let y = 63; y >= 0; y--) { if (this.game.world.getBlock(x, y, z) !== 0) { baseY = y + 1; break; } }
                    for (let dy = 0; dy < 5; dy++) this.game.world.setBlock(x, baseY + dy, z, 4);
                    for (let dx = -2; dx <= 2; dx++)
                        for (let dz = -2; dz <= 2; dz++)
                            for (let dy = 3; dy <= 6; dy++)
                                if (Math.abs(dx) + Math.abs(dz) + Math.abs(dy - 4) < 4)
                                    this.game.world.setBlock(x + dx, baseY + dy, z + dz, 5);
                    response.success = true; response.y = baseY;
                    break;
                }

                case 'get_world_info':
                    response.seed = this.game.world.noise ? this.game.world.noise.seed : null;
                    response.chunkCount = this.game.world.chunks ? this.game.world.chunks.size : 0;
                    response.timeOfDay = this.game.dayNight ? this.game.dayNight.timeOfDay : 0;
                    response.isNight = this.game.dayNight ? this.game.dayNight.isNight() : false;
                    break;

                case 'get_view': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const hit = this.raycastFromPlayer(player, params.distance || 8, true);
                    if (!hit) { response.position = null; response.blockType = 0; response.message = 'No hay bloques visibles'; break; }
                    response.position = hit.hit; response.blockType = hit.block; response.distance = hit.distance;
                    break;
                }

                case 'get_nearby_blocks': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const radius = params.radius || 5;
                    const blocks = [];
                    for (let dx = -radius; dx <= radius; dx++)
                        for (let dy = -2; dy <= 3; dy++)
                            for (let dz = -radius; dz <= radius; dz++) {
                                const b = this.game.world.getBlock(Math.floor(player.position.x) + dx, Math.floor(player.position.y) + dy, Math.floor(player.position.z) + dz);
                                if (b !== 0) blocks.push({ x: Math.floor(player.position.x) + dx, y: Math.floor(player.position.y) + dy, z: Math.floor(player.position.z) + dz, type: b });
                            }
                    response.blocks = blocks; response.count = blocks.length;
                    break;
                }

                case 'get_nearby_entities': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const radius = params.radius || 20;
                    const entities = [];
                    [1, 2].forEach(id => {
                        const p = this.getPlayer(id);
                        if (p && id !== params.player_id) {
                            const d = Math.hypot(p.position.x - player.position.x, p.position.y - player.position.y, p.position.z - player.position.z);
                            if (d <= radius) entities.push({ type: 'player', id, name: p.name || ('Jugador ' + id), position: this.toPos(p.position), distance: Math.round(d) });
                        }
                    });
                    if (this.game.enemyManager && this.game.enemyManager.enemies) {
                        this.game.enemyManager.enemies.forEach(e => {
                            const d = Math.hypot(e.position.x - player.position.x, e.position.y - player.position.y, e.position.z - player.position.z);
                            if (d <= radius) entities.push({ type: 'enemy', enemyType: e.type, position: this.toPos(e.position), health: e.health, distance: Math.round(d) });
                        });
                    }
                    response.entities = entities; response.count = entities.length;
                    break;
                }

                case 'get_environment': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const bx = Math.floor(player.position.x), by = Math.floor(player.position.y), bz = Math.floor(player.position.z);
                    const below = this.game.world.getBlock(bx, by - 1, bz);
                    response.position = { x: bx, y: by, z: bz };
                    response.blockBelow = below;
                    response.adjacent = {
                        north: this.game.world.getBlock(bx, by, bz - 1),
                        south: this.game.world.getBlock(bx, by, bz + 1),
                        east: this.game.world.getBlock(bx + 1, by, bz),
                        west: this.game.world.getBlock(bx - 1, by, bz),
                        above: this.game.world.getBlock(bx, by + 1, bz),
                        below
                    };
                    response.timeOfDay = this.game.dayNight ? this.game.dayNight.timeOfDay : 0.5;
                    response.isNight = this.game.dayNight ? this.game.dayNight.isNight() : false;
                    break;
                }

                case 'get_top_down_view': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const radius = params.radius || 10;
                    const bx = Math.floor(player.position.x), bz = Math.floor(player.position.z);
                    const symbolMap = { 0: ' ', 1: '.', 2: ',', 3: '#', 4: 'T', 5: '*', 6: '~', 7: '≈', 8: 'O', 9: '=', 10: 'X' };
                    const map = [];
                    for (let dz = -radius; dz <= radius; dz++) {
                        let row = '';
                        for (let dx = -radius; dx <= radius; dx++) {
                            const wx = bx + dx, wz = bz + dz;
                            let top = 0;
                            for (let wy = 63; wy >= 0; wy--) { const b = this.game.world.getBlock(wx, wy, wz); if (b !== 0) { top = b; break; } }
                            row += (dx === 0 && dz === 0) ? '@' : (symbolMap[top] || '?');
                        }
                        map.push(row);
                    }
                    response.map = map;
                    response.playerPosition = { x: bx, y: Math.floor(player.position.y), z: bz };
                    response.size = radius * 2 + 1;
                    break;
                }

                case 'get_camera_matrix': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const width = params.width || 11, height = params.height || 7, depth = params.depth || 8;
                    const matrix = [];
                    for (let row = 0; row < height; row++) {
                        let mrow = '';
                        for (let col = 0; col < width; col++) {
                            const worldX = Math.floor(player.position.x) + col - Math.floor(width / 2);
                            const worldY = Math.floor(player.position.y + 1.6) + row - Math.floor(height / 2);
                            const worldZ = Math.floor(player.position.z) - 1;
                            let found = 0;
                            for (let d = 0; d < depth; d++) {
                                const b = this.game.world.getBlock(worldX, worldY, worldZ - d);
                                if (b !== 0) { found = b; break; }
                            }
                            mrow += found === 0 ? ' ' : '#';
                        }
                        matrix.push(mrow);
                    }
                    response.matrix = matrix;
                    response.playerPosition = { x: Math.floor(player.position.x), y: Math.floor(player.position.y + 1.6), z: Math.floor(player.position.z) };
                    response.fieldOfView = { width, height, depth };
                    break;
                }

                case 'get_screenshot': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const w = params.width || 640, h = params.height || 360;
                    const renderer = new THREE.WebGLRenderer({ preserveDrawingBuffer: true, antialias: false });
                    renderer.setSize(w, h);
                    renderer.render(this.game.scene, this.game.camera1);
                    response.image = renderer.domElement.toDataURL('image/jpeg', 0.8);
                    response.width = w; response.height = h; response.format = 'jpeg';
                    renderer.dispose();
                    break;
                }

                case 'navigate_to': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const goalX = params.x;
                    const goalZ = params.z;
                    if (goalX === undefined || goalZ === undefined) {
                        response.error = 'x and z required'; break;
                    }
                    const path = this.pathfinder.findPath(
                        player.position.x, player.position.z,
                        goalX, goalZ,
                        player.position.y
                    );
                    if (!path || path.length < 2) {
                        response.error = 'No path found'; break;
                    }
                    this.follower.start(path, params.player_id, player, this.game.gamepadHandler, response);
                    response.__async = true;
                    this.pendingResponse = response;
                    break;
                }

                case 'attack': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const mgr = this.game.enemyManager;
                    if (!mgr) { response.error = 'No enemy manager'; break; }
                    let enemy = null;
                    if (params.target_id) {
                        enemy = mgr.findEnemyById(params.target_id);
                        if (!enemy) { response.error = 'Enemy not found'; break; }
                    } else {
                        const dir = player.getForwardDirection();
                        enemy = mgr.findNearestInCone(player.position, dir, 3.0, 0.707);
                        if (!enemy) { response.error = 'No enemy in range'; break; }
                    }
                    const dead = player.hitEntity(enemy);
                    response.success = true;
                    response.damaged = true;
                    response.enemyDead = dead;
                    if (dead) response.enemyId = enemy.id;
                    break;
                }

                case 'execute_command':
                    if (this.game.gameConsole) this.game.gameConsole.executeRemoteCommand(params.command);
                    response.success = true;
                    break;

                case 'list_players':
                    response.players = [1, 2].map(id => {
                        const p = this.getPlayer(id);
                        return { id, name: p ? (p.name || ('Jugador ' + id)) : ('Jugador ' + id), position: p ? this.toPos(p.position) : null };
                    });
                    break;

                case 'move_burst': {
                    if (!player) { response.error = 'Player not found'; break; }
                    this.burstMove(player, params, response).then(() => {
                        if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(response));
                    });
                    response.__async = true;
                    break;
                }

                case 'gamepad_connect': {
                    if (!player) { response.error = 'Player not found'; break; }
                    this.game.gamepadHandler.enableVirtual(player.id - 1);
                    response.success = true;
                    response.connected = this.game.gamepadHandler.isConnected(player.id - 1);
                    break;
                }

                case 'gamepad_input': {
                    if (!player) { response.error = 'Player not found'; break; }
                    const ok = this.game.gamepadHandler.setVirtualInput(player.id - 1, params.input || {});
                    response.success = ok;
                    if (!ok) response.error = 'Gamepad virtual no activado (usa gamepad_connect)';
                    break;
                }

                case 'gamepad_disconnect': {
                    if (!player) { response.error = 'Player not found'; break; }
                    this.game.gamepadHandler.disableVirtual(player.id - 1);
                    response.success = true;
                    break;
                }

                default:
                    response.error = 'Unknown method';
            }
        } catch (e) {
            response.error = e.message;
            console.error('[MCP] Error procesando:', e);
        }

        // Send response back (unless an async handler already sent it)
        if (!response.__async && this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(response));
        }
    }

    // Aplica una ráfaga de pasos relativos dentro del navegador (fluidoo y rápido).
    // Si target_id está presente, reorienta al objetivo en cada paso.
    async burstMove(player, params, response) {
        const steps = params.steps || 1;
        const dist = params.distance || 1;
        const delay = params.stepDelay || 0;
        const target = params.target_id ? this.getPlayer(params.target_id) : null;
        for (let s = 0; s < steps; s++) {
            if (target && target.position) {
                const t = target.position, p = player.position;
                player.rotation.y = Math.atan2(-(t.x - p.x), -(t.z - p.z));
            }
            const r = player.rotation.y;
            const fwd = { x: -Math.sin(r), z: -Math.cos(r) };
            const right = { x: Math.cos(r), z: -Math.sin(r) };
            let dx = 0, dz = 0;
            if (params.forward) { dx += fwd.x * dist; dz += fwd.z * dist; }
            if (params.backward) { dx -= fwd.x * dist; dz -= fwd.z * dist; }
            if (params.left) { dx -= right.x * dist; dz -= right.z * dist; }
            if (params.right) { dx += right.x * dist; dz += right.z * dist; }
            player.position.x += dx;
            player.position.z += dz;
            if (delay) await new Promise(res => setTimeout(res, delay));
        }
        response.success = true;
        response.position = this.toPos(player.position);
        response.steps = steps;
    }

    // Obtener objeto jugador (1/2; avatares no soportados aún)
    getPlayer(id) {
        return this.game[`player${id}`] || null;
    }

    // Vector3 -> {x,y,z}
    toPos(v) {
        if (v && typeof v.x === 'number') return { x: v.x, y: v.y, z: v.z };
        return v;
    }

    // Raycast simple desde los ojos del jugador en la dirección de mira
    raycastFromPlayer(player, maxDist = 5, withDistance = false) {
        const rotation = player.rotation || { x: 0, y: 0 };
        const eyeY = player.position.y + 1.6;
        const dir = {
            x: -Math.sin(rotation.y) * Math.cos(rotation.x),
            y: -Math.sin(rotation.x),
            z: -Math.cos(rotation.y) * Math.cos(rotation.x)
        };
        let last = null;
        const steps = maxDist * 10;
        for (let i = 1; i <= steps; i++) {
            const px = player.position.x + dir.x * i * 0.1;
            const py = eyeY + dir.y * i * 0.1;
            const pz = player.position.z + dir.z * i * 0.1;
            const bx = Math.floor(px), by = Math.floor(py), bz = Math.floor(pz);
            const block = this.game.world.getBlock(bx, by, bz);
            if (block !== 0) {
                return {
                    hit: { x: bx, y: by, z: bz },
                    block,
                    face: last,
                    distance: withDistance ? i * 0.1 : undefined
                };
            }
            last = { x: bx, y: by, z: bz };
        }
        return null;
    }

    // Iniciar sincronización periódica
    startSync() {
        this.syncInterval = setInterval(() => {
            this.syncState();
        }, 1000); // Cada segundo
    }

    // Detener sincronización
    stopSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
        }
    }

    // Sincronizar estado del juego con el servidor
    syncState() {
        if (!this.connected || !this.game.running) return;

        const state = {
            players: {},
            world: {
                seed: this.game.world.noise.seed,
                chunkCount: this.game.world.chunks.size
            },
            timeOfDay: this.game.dayNight.timeOfDay,
            isNight: this.game.dayNight.isNight()
        };

        // Sincronizar jugadores
        [1, 2].forEach(id => {
            const player = this.game[`player${id}`];
            if (player) {
                state.players[id] = {
                    name: this.game[`playerModel${id}`]?.config?.name || `Jugador ${id}`,
                    position: { x: player.position.x, y: player.position.y, z: player.position.z },
                    rotation: { x: player.rotation.x, y: player.rotation.y },
                    isFlying: player.isFlying,
                    cameraMode: player.cameraMode,
                    selectedSlot: player.selectedSlot,
                    health: player.health,
                    isAI: false,
                    inventory: player.inventory.slots.filter(s => s !== null)
                };
            }
        });

        this.playerStates = state.players;

        // Sincronizar entidades (enemigos) para el blackboard
        if (this.game.enemyManager && this.game.enemyManager.enemies) {
            state.entities = this.game.enemyManager.enemies.map(e => ({
                type: 'enemy',
                enemyType: e.type,
                id: e.id,
                position: { x: e.position.x, y: e.position.y, z: e.position.z },
                distance: Math.hypot(
                    e.position.x - (state.players[2]?.position?.x || 0),
                    e.position.z - (state.players[2]?.position?.z || 0)
                ),
                health: e.health
            }));
        }

        this.playerStates = state.players;
        return state;
    }

    // Obtener estado de un jugador
    getPlayerState(playerId) {
        return this.playerStates[playerId] || null;
    }

    // Enviar estado al servidor
    sendState() {
        if (!this.connected) return;
        
        const state = this.syncState();
        this.ws.send(JSON.stringify({
            type: 'state_update',
            state
        }));
    }

    // Desconectar
    disconnect() {
        this.stopSync();
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Exportar
window.MCPClient = MCPClient;
