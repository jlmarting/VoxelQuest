#!/usr/bin/env node
/**
 * VoxelQuest Game Server
 *
 * Sirve el juego (archivos estáticos), WebSocket relay al navegador,
 * API JSON-RPC 2.0 para clientes externos (mcp-server.js, scripts Python),
 * y motor de Árboles de Comportamiento (Behavior Tree).
 *
 * No habla MCP. No tiene transporte stdio. No tiene SSE.
 * Para MCP, usar mcp-server.js (adaptador stdio ↔ WebSocket).
 *
 * Uso:
 *   node game-server.js
 *   PORT=9001 node game-server.js
 */

const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const webbrowser = require('child_process').webbrowser || null;
const { BehaviorTree, NODE_STATUS, createActionCatalog } = require('./bt-engine.js');

// Logger que siempre escribe a stderr (para no contaminar stdout con el protocolo MCP)
function log(...args) {
    process.stderr.write(args.map(a => typeof a === 'string' ? a : JSON.stringify(a)).join(' ') + '\n');
}

// Estado global del juego
let gameState = {
    players: {
        1: { name: 'Jugador 1', isAI: false, position: { x: 24, y: 25, z: 20 }, rotation: { x: 0, y: 0 }, health: 20, onGround: true, isFlying: false, selectedSlot: 0, inventory: [] },
        2: { name: 'Jugador 2', isAI: false, position: { x: 25, y: 25, z: 25 }, rotation: { x: 0, y: 0 }, health: 20, onGround: true, isFlying: false, selectedSlot: 0, inventory: [] }
    },
    world: null,
    scene: null,
    enemyManager: null,
    dayNight: null,
    running: false,
    seed: null,
    mode: null, // 'solo', 'coop' o 'training'
    // Configuración de aprobación
    approvalMode: 'auto', // 'auto' o 'human'
    pendingApprovals: [],
    enemies: []
};

// IDs de jugadores
let nextPlayerId = 3; // 1 y 2 son locales

// Helpers MCP
function withPlayer(fn) {
    return async (params) => {
        if (!params || params.player_id === undefined)
            return { error: 'player_id requerido' };
        const player = gameState.players[params.player_id];
        if (!player) return { error: `Jugador ${params.player_id} no encontrado` };
        return fn(params, player);
    };
}

function buildSchema(inputSchema) {
    const properties = {};
    const required = [];
    for (const [key, def] of Object.entries(inputSchema || {})) {
        const prop = { type: def.type };
        if (def.enum) prop.enum = def.enum;
        if (def.minimum !== undefined) prop.minimum = def.minimum;
        if (def.maximum !== undefined) prop.maximum = def.maximum;
        properties[key] = prop;
        if (def.required) required.push(key);
    }
    return {
        type: 'object',
        properties,
        ...(required.length ? { required } : {})
    };
}

function tool(description, schema, fn) {
    fn._mcp = { description, schema };
    return fn;
}

// WebSocket clients conectados
let gameClients = [];

// ---- Behavior Tree Engine ----
let btEngine = null;
let btInterval = null;
let avatarFollowInterval = null;

let avatarFormation = {};
let avatarBreakTargets = {};
let avatarBreakCooldown = {};

function startAvatarFollow() {
    if (avatarFollowInterval) return;
    log('[Avatares] En formación con P2');

    // Asignar offset de formación a cada avatar
    const assignFormation = () => {
        const avs = Object.entries(gameState.players).filter(([id]) => id >= 3);
        avs.forEach(([id], idx) => {
            if (!avatarFormation[id]) {
                const row = Math.floor(idx / 5);
                const col = idx % 5;
                avatarFormation[id] = { ox: (col - 2) * 2, oz: 3 + row * 2 };
            }
        });
    };
    assignFormation();

    avatarFollowInterval = setInterval(() => {
        const p2 = gameState.players[2];
        if (!p2 || !p2.position) return;
        const speed = 0.2;
        const repulsion = 0.15;
        const minDist = 1.8;

        const aiAvatars = Object.entries(gameState.players).filter(([id]) => id >= 3);
        const enemies = gameState.enemies || [];
        assignFormation();

        // Encontrar enemigo más cercano a P2
        let targetEnemy = null;
        let minEnemyDist = Infinity;
        const attackRange = 8.0;
        enemies.forEach(e => {
            const d = Math.hypot(e.x - p2.position.x, e.z - p2.position.z);
            if (d < minEnemyDist) { minEnemyDist = d; targetEnemy = e; }
        });

        aiAvatars.forEach(([id, p]) => {
            if (!p.position) return;
            const off = avatarFormation[id];
            let moveX = 0, moveZ = 0;

            // Buscar y atacar monstruos (prioritario)
            let enemyTarget = null;
            let enemyDist = Infinity;
            enemies.forEach(e => {
                const d = Math.hypot(e.x - p.position.x, e.z - p.position.z);
                if (d < enemyDist) { enemyDist = d; enemyTarget = e; }
            });

            if (enemyTarget) {
                const dx = enemyTarget.x - p.position.x;
                const dz = enemyTarget.z - p.position.z;
                const d = Math.hypot(dx, dz);
                if (d > 0.8) { moveX = (dx/d) * 0.35; moveZ = (dz/d) * 0.35; }
            } else {
                const targetX = p2.position.x + off.ox;
                const targetZ = p2.position.z + off.oz;
                const dx = targetX - p.position.x;
                const dz = targetZ - p.position.z;
                const dist = Math.hypot(dx, dz);
                if (dist > 0.3) {
                    moveX = (dx / dist) * speed;
                    moveZ = (dz / dist) * speed;
                }
            }

            // Repulsión entre avatares
            aiAvatars.forEach(([oid, other]) => {
                if (oid === id || !other.position) return;
                const rx = p.position.x - other.position.x;
                const rz = p.position.z - other.position.z;
                const rd = Math.hypot(rx, rz);
                if (rd < minDist && rd > 0.01) {
                    moveX += (rx / rd) * repulsion;
                    moveZ += (rz / rd) * repulsion;
                }
            });

            p.position.x += moveX;
            p.position.z += moveZ;
        });

        const p2yaw = p2.rotation ? p2.rotation.y : 0;
        // Romper construcciones (rápido y a distancia)
        const now = Date.now();
        const occupied = new Set();
        aiAvatars.forEach(([id, p]) => {
            if (!p.position || !avatarBreakTargets[id]) return;
            occupied.add(avatarBreakTargets[id].x + ',' + avatarBreakTargets[id].y + ',' + avatarBreakTargets[id].z);
        });
        aiAvatars.forEach(([id, p]) => {
            if (!p.position) return;
            if ((avatarBreakCooldown[id] || 0) > now) return;
            const tgt = avatarBreakTargets[id];
            if (tgt) {
                sendToGame({ method: 'break_block', params: { x: tgt.x, y: tgt.y, z: tgt.z } });
                delete avatarBreakTargets[id];
                avatarBreakCooldown[id] = now + 30;
                return;
            }
            for (let attempt = 0; attempt < 20; attempt++) {
                const bx = Math.floor(p.position.x + (Math.random() - 0.5) * 20);
                const by = 2 + Math.floor(Math.random() * 20);
                const bz = Math.floor(p.position.z + (Math.random() - 0.5) * 20);
                const key = bx + ',' + by + ',' + bz;
                if (!occupied.has(key)) {
                    avatarBreakTargets[id] = { x: bx, y: by, z: bz };
                    occupied.add(key);
                    break;
                }
            }
        });

        const avatars = aiAvatars.map(([id, p]) => ({ id: parseInt(id), x: p.position.x, y: p.position.y, z: p.position.z, ry: p2yaw }));
        if (avatars.length > 0) {
            sendToGame({ id: 'av_' + Date.now(), method: 'avatar_update', params: { avatars } });
        }
    }, 100);
}

function stopAvatarFollow() {
    if (avatarFollowInterval) {
        clearInterval(avatarFollowInterval);
        avatarFollowInterval = null;
        log('[Avatares] Dejaron de seguir');
    }
}

const btBlackboard = {
    self_vida: 20,
    self_x: 0,
    self_z: 0,
    p1_x: 0,
    p1_z: 0,
    p1_y: 0,
    target_enemigo_id: null,
    target_enemigo_x: 0,
    target_enemigo_z: 0,
    hay_enemigos_cerca: false,
    // Sensores entrenamiento
    onGround: true,
    stuck: false,
    bloque_bajo: -1,
    bloque_frente_altura: 0,
    self_rot_y: 0
};

function btRelay(method, params) {
    sendToGame({ id: 'bt_' + Date.now(), method, params });
}

function updateBtBlackboard() {
    const p2 = gameState.players[2];
    if (p2) {
        btBlackboard.self_vida = p2.health;
        btBlackboard.self_x = p2.position.x;
        btBlackboard.self_z = p2.position.z;
    }
}

function startBtTick() {
    if (btInterval) return;
    log('[BT] Iniciando tick loop (10Hz)');
    btInterval = setInterval(() => {
        if (!btEngine) return;
        updateBtBlackboard();
        const result = btEngine.tick();
        if (result === NODE_STATUS.FAILURE) {
            // All selectors failed -> auto idle
            btEngine.runningAction = null;
        }
        if (result === NODE_STATUS.FAILURE && btEngine.lastResult !== result) {
            log('[BT] Falling back to idle');
            btRelay('gamepad_input', { player_id: 2, input: { move: { x: 0, z: 0 }, look: { x: 0, y: 0 } } });
        }
    }, 100);
}

function stopBtTick() {
    if (btInterval) {
        clearInterval(btInterval);
        btInterval = null;
        log('[BT] Tick loop detenido');
    }
}

function loadBehaviorTree(json) {
    const catalog = createActionCatalog(btRelay);
    const tree = new BehaviorTree(json, catalog, btRelay, btBlackboard);
    if (tree.error) return { error: tree.error };
    btEngine = tree;
    startBtTick();
    return { success: true, message: 'Behavior tree loaded' };
}

// Enviar comando al juego via WebSocket
function sendToGame(data) {
    const message = JSON.stringify(data);
    gameClients.forEach(client => {
        if (client.readyState === 1) { // WebSocket.OPEN
            client.send(message);
        }
    });
}

// Mapa de peticiones relay pendientes (correlación por id)
const pendingMcp = {};

// Reenvía un comando al navegador (fuente de verdad) y espera su respuesta.
function relayToGame(method, params, timeoutMs = 5000) {
    if (!gameClients.length) return Promise.resolve({ error: 'Juego no conectado' });
    const id = Date.now().toString() + '_' + Math.random().toString(36).slice(2);
    return new Promise((resolve) => {
        const timer = setTimeout(() => {
            delete pendingMcp[id];
            resolve({ error: 'Timeout: el juego no respondió', method });
        }, timeoutMs);
        pendingMcp[id] = { resolve, timer };
        sendToGame({ id, method, params });
    });
}

// Colores para nuevos avatros
const AVATAR_COLORS = [
    { name: 'Rojo', shirt: 0xcc4444, pants: 0x882222 },
    { name: 'Azul', shirt: 0x4444cc, pants: 0x222288 },
    { name: 'Verde', shirt: 0x44cc44, pants: 0x228822 },
    { name: 'Amarillo', shirt: 0xcccc44, pants: 0x888822 },
    { name: 'Morado', shirt: 0xcc44cc, pants: 0x882288 },
    { name: 'Naranja', shirt: 0xcc8844, pants: 0x886622 },
    { name: 'Cian', shirt: 0x44cccc, pants: 0x228888 },
    { name: 'Rosa', shirt: 0xff88aa, pants: 0xcc6688 }
];

// Estructuras predefinidas
const STRUCTURES = {
    house: {
        name: 'Casa pequeña',
        blocks: [
            // Foundation
            { dx: 0, dy: 0, dz: 0, type: 3 }, { dx: 1, dy: 0, dz: 0, type: 3 },
            { dx: 2, dy: 0, dz: 0, type: 3 }, { dx: 3, dy: 0, dz: 0, type: 3 },
            { dx: 0, dy: 0, dz: 3, type: 3 }, { dx: 1, dy: 0, dz: 3, type: 3 },
            { dx: 2, dy: 0, dz: 3, type: 3 }, { dx: 3, dy: 0, dz: 3, type: 3 },
            { dx: 0, dy: 0, dz: 1, type: 3 }, { dx: 0, dy: 0, dz: 2, type: 3 },
            { dx: 3, dy: 0, dz: 1, type: 3 }, { dx: 3, dy: 0, dz: 2, type: 3 },
            // Walls
            ...Array.from({length: 4}, (_, i) => ({ dx: i, dy: 1, dz: 0, type: 1 })),
            ...Array.from({length: 4}, (_, i) => ({ dx: i, dy: 2, dz: 0, type: 1 })),
            ...Array.from({length: 4}, (_, i) => ({ dx: i, dy: 1, dz: 3, type: 1 })),
            ...Array.from({length: 4}, (_, i) => ({ dx: i, dy: 2, dz: 3, type: 1 })),
            { dx: 0, dy: 1, dz: 1, type: 1 }, { dx: 0, dy: 2, dz: 1, type: 1 },
            { dx: 3, dy: 1, dz: 1, type: 1 }, { dx: 3, dy: 2, dz: 1, type: 1 },
            { dx: 0, dy: 1, dz: 2, type: 1 }, { dx: 0, dy: 2, dz: 2, type: 1 },
            { dx: 3, dy: 1, dz: 2, type: 1 }, { dx: 3, dy: 2, dz: 2, type: 1 },
            // Roof
            ...Array.from({length: 5}, (_, i) => ({ dx: i, dy: 3, dz: 0, type: 5 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: i, dy: 3, dz: 1, type: 5 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: i, dy: 3, dz: 2, type: 5 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: i, dy: 3, dz: 3, type: 5 })),
        ]
    },
    tower: {
        name: 'Torre',
        blocks: Array.from({length: 20}, (_, i) => {
            const level = Math.floor(i / 4);
            const pos = i % 4;
            const sides = [
                { dx: pos, dy: level, dz: 0, type: 3 },
                { dx: pos, dy: level, dz: 4, type: 3 },
                { dx: 0, dy: level, dz: pos, type: 3 },
                { dx: 4, dy: level, dz: pos, type: 3 }
            ];
            return sides;
        }).flat()
    },
    farm: {
        name: 'Granja',
        blocks: [
            ...Array.from({length: 7}, (_, i) => ({ dx: i, dy: 0, dz: 0, type: 2 })),
            ...Array.from({length: 7}, (_, i) => ({ dx: i, dy: 0, dz: 6, type: 2 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: 0, dy: 0, dz: i+1, type: 2 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: 6, dy: 0, dz: i+1, type: 2 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: i+1, dy: 0, dz: 2, type: 5 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: i+1, dy: 0, dz: 4, type: 5 })),
        ]
    }
};

// ============================================================
// HANDLERS MCP
// ============================================================
const mcpHandlers = {
    // ---- CONFIGURACIÓN ----
    get_config: tool('Obtener configuración actual del servidor', {}, async () => ({
        approvalMode: gameState.approvalMode,
        playerCount: Object.keys(gameState.players).length,
        players: Object.entries(gameState.players).map(([id, p]) => ({
            id, name: p.name, isAI: p.isAI, position: p.position
        }))
    })),

    set_approval_mode: tool('Cambiar modo de aprobación (auto/human)', {
        mode: { type: 'string', required: true, enum: ['auto', 'human'] }
    }, async (params) => {
        gameState.approvalMode = params.mode;
        return { success: true, approvalMode: gameState.approvalMode };
    }),

    // ---- GESTIÓN DE JUGADORES ----
    list_players: tool('Listar todos los jugadores', {}, async () => ({
        players: Object.entries(gameState.players).map(([id, p]) => ({
            id: parseInt(id), name: p.name, isAI: p.isAI,
            position: p.position, rotation: p.rotation || { x: 0, y: 0 },
            health: p.health, onGround: p.onGround || false,
            isFlying: p.isFlying || false, selectedSlot: p.selectedSlot || 0
        }))
    })),

    get_player_state: tool('Obtener estado de un jugador', {
        player_id: { type: 'integer', required: true }
    }, withPlayer(async (params, player) => ({
        id: params.player_id, name: player.name, isAI: player.isAI,
        position: player.position, rotation: player.rotation || { x: 0, y: 0 },
        health: player.health, onGround: player.onGround || false,
        isFlying: player.isFlying || false, selectedSlot: player.selectedSlot || 0,
        inventory: player.inventory || []
    }))),

    create_avatar: tool('Crear nuevo avatar IA', {
        name: { type: 'string' }, gender: { type: 'string', enum: ['male', 'female'] },
        hairStyle: { type: 'string' }, hairColor: { type: 'number' }, eyeColor: { type: 'number' },
        shirtColor: { type: 'number' }, pantsColor: { type: 'number' },
        spawnX: { type: 'number' }, spawnZ: { type: 'number' }
    }, async (params) => {
        const { name, gender = 'male', hairStyle = 'short', hairColor = 0x3d2314,
                eyeColor = 0x4a90d9, shirtColor = 0x2266cc, pantsColor = 0x333366,
                spawnX = 0, spawnZ = 0 } = params;
        if (gameState.approvalMode === 'human') {
            const approvalId = Date.now().toString();
            gameState.pendingApprovals.push({ id: approvalId, type: 'create_avatar', params, status: 'pending' });
            if (gameState.onApprovalRequest)
                gameState.onApprovalRequest({ id: approvalId, type: 'create_avatar', message: `Agente IA quiere crear avatar "${name}" (${gender})` });
            return { pending: true, approvalId, message: 'Esperando aprobación del jugador humano' };
        }
        return createAvatar(params);
    }),

    get_pending_requests: tool('Obtener solicitudes pendientes de aprobación', {}, async () => ({
        requests: gameState.pendingApprovals.filter(r => r.status === 'pending')
    })),

    approve_request: tool('Aprobar o rechazar solicitud pendiente', {
        approvalId: { type: 'string', required: true }, approved: { type: 'boolean', required: true }
    }, async (params) => {
        const request = gameState.pendingApprovals.find(r => r.id === params.approvalId);
        if (!request) return { error: 'Solicitud no encontrada' };
        if (params.approved) {
            request.status = 'approved';
            const result = await createAvatar(request.params);
            return { success: true, result };
        }
        request.status = 'rejected';
        return { success: true, message: 'Solicitud rechazada' };
    }),

    // ---- GAMEPAD VIRTUAL ----
    gamepad_connect: tool('Activar gamepad virtual para IA', {
        player_id: { type: 'integer', required: true }
    }, withPlayer(async (params) => relayToGame('gamepad_connect', { player_id: params.player_id }))),

    gamepad_input: tool('Inyectar entrada en gamepad virtual', {
        player_id: { type: 'integer', required: true },
        input: { type: 'object' }
    }, withPlayer(async (params) => relayToGame('gamepad_input', { player_id: params.player_id, input: params.input }))),

    gamepad_disconnect: tool('Desactivar gamepad virtual', {
        player_id: { type: 'integer', required: true }
    }, withPlayer(async (params) => relayToGame('gamepad_disconnect', { player_id: params.player_id }))),

    // ---- CÁMARA ----
    look: tool('Rotar cámara del jugador', {
        player_id: { type: 'integer', required: true },
        yaw: { type: 'number' }, pitch: { type: 'number' },
        yaw_delta: { type: 'number' }, pitch_delta: { type: 'number' }
    }, withPlayer(async (params) => relayToGame('look', {
        player_id: params.player_id, yaw: params.yaw, pitch: params.pitch,
        yaw_delta: params.yaw_delta, pitch_delta: params.pitch_delta
    }))),

    get_rotation: tool('Obtener rotación del jugador', {
        player_id: { type: 'integer', required: true }
    }, withPlayer(async (params) => relayToGame('get_rotation', { player_id: params.player_id }))),

    toggle_camera: tool('Alternar modo de cámara', {
        player_id: { type: 'integer', required: true }
    }, withPlayer(async (params) => relayToGame('toggle_camera', { player_id: params.player_id }))),

    // ---- INVENTARIO ----
    select_slot: tool('Seleccionar slot del inventario (0-8)', {
        player_id: { type: 'integer', required: true },
        slot: { type: 'integer', required: true, minimum: 0, maximum: 8 }
    }, withPlayer(async (params, player) => {
        if (params.slot < 0 || params.slot > 8) return { error: 'Slot inválido (0-8)' };
        player.selectedSlot = params.slot;
        return relayToGame('select_slot', { player_id: params.player_id, slot: params.slot });
    })),

    next_slot: tool('Seleccionar siguiente slot', {
        player_id: { type: 'integer', required: true }
    }, withPlayer(async (params) => relayToGame('next_slot', { player_id: params.player_id }))),

    prev_slot: tool('Seleccionar slot anterior', {
        player_id: { type: 'integer', required: true }
    }, withPlayer(async (params) => relayToGame('prev_slot', { player_id: params.player_id }))),

    get_inventory: tool('Obtener inventario del jugador', {
        player_id: { type: 'integer', required: true }
    }, withPlayer(async (params, player) => ({ inventory: player.inventory || [] }))),

    add_item: tool('Añadir item al inventario', {
        player_id: { type: 'integer', required: true },
        type: { type: 'integer', required: true }, count: { type: 'integer' }
    }, withPlayer(async (params, player) => {
        if (!player.inventory) player.inventory = [];
        player.inventory.push({ type: params.type, count: params.count || 1 });
        return { success: true };
    })),

    // ---- BLOQUES ----
    place_block: tool('Colocar bloque en coordenadas absolutas', {
        x: { type: 'integer', required: true }, y: { type: 'integer', required: true },
        z: { type: 'integer', required: true }, type: { type: 'integer', required: true }
    }, async (params) => relayToGame('place_block', { x: params.x, y: params.y, z: params.z, type: params.type })),

    place_block_as_player: tool('Colocar bloque donde mira el jugador', {
        player_id: { type: 'integer', required: true }, type: { type: 'integer' }
    }, withPlayer(async (params) => relayToGame('place_block_as_player', { player_id: params.player_id, type: params.type }))),

    break_block: tool('Romper bloque en coordenadas absolutas', {
        x: { type: 'integer', required: true }, y: { type: 'integer', required: true },
        z: { type: 'integer', required: true }
    }, async (params) => relayToGame('break_block', { x: params.x, y: params.y, z: params.z })),

    break_block_as_player: tool('Romper bloque donde mira el jugador', {
        player_id: { type: 'integer', required: true }
    }, withPlayer(async (params) => relayToGame('break_block_as_player', { player_id: params.player_id }))),

    get_block: tool('Obtener tipo de bloque en coordenadas', {
        x: { type: 'integer', required: true }, y: { type: 'integer', required: true },
        z: { type: 'integer', required: true }
    }, async (params) => relayToGame('get_block', { x: params.x, y: params.y, z: params.z })),

    get_height: tool('Obtener altura del terreno en (x,z)', {
        x: { type: 'integer', required: true }, z: { type: 'integer', required: true }
    }, async (params) => relayToGame('get_height', { x: params.x, z: params.z })),

    get_blocks_in_area: tool('Obtener todos los bloques en un área', {
        x1: { type: 'integer', required: true }, y1: { type: 'integer', required: true },
        z1: { type: 'integer', required: true }, x2: { type: 'integer', required: true },
        y2: { type: 'integer', required: true }, z2: { type: 'integer', required: true }
    }, async (params) => relayToGame('get_blocks_in_area', {
        x1: params.x1, y1: params.y1, z1: params.z1, x2: params.x2, y2: params.y2, z2: params.z2
    })),

    // ---- CONSTRUCCIÓN ----
    build_structure: tool('Construir una estructura predefinida', {
        structure: { type: 'string', required: true, enum: Object.keys(STRUCTURES) },
        x: { type: 'integer', required: true }, y: { type: 'integer', required: true },
        z: { type: 'integer', required: true }
    }, async (params) => {
        const structure = STRUCTURES[params.structure];
        if (!structure) return { error: `Estructura desconocida: ${params.structure}` };
        return relayToGame('apply_blocks', {
            blocks: structure.blocks.map(b => ({
                x: params.x + b.dx, y: params.y + b.dy, z: params.z + b.dz, type: b.type
            }))
        });
    }),

    list_structures: tool('Listar estructuras disponibles', {}, async () => ({
        structures: Object.entries(STRUCTURES).map(([key, s]) => ({ id: key, name: s.name, blocks: s.blocks.length }))
    })),

    create_wall: tool('Crear una pared', {
        x: { type: 'integer', required: true }, z: { type: 'integer', required: true },
        length: { type: 'integer', required: true }, height: { type: 'integer' },
        direction: { type: 'string', enum: ['x', 'z'] }, type: { type: 'integer' }, baseY: { type: 'integer' }
    }, async (params) => {
        const { x, z, length, height = 3, direction = 'x', type = 1, baseY = 20 } = params;
        const blocks = [];
        for (let i = 0; i < length; i++)
            for (let dy = 0; dy < height; dy++)
                blocks.push({ x: direction === 'x' ? x + i : x, y: baseY + dy, z: direction === 'z' ? z + i : z, type });
        return relayToGame('apply_blocks', { blocks });
    }),

    create_floor: tool('Crear un suelo', {
        x: { type: 'integer', required: true }, z: { type: 'integer', required: true },
        width: { type: 'integer', required: true }, depth: { type: 'integer', required: true },
        type: { type: 'integer' }, baseY: { type: 'integer' }
    }, async (params) => {
        const { x, z, width, depth, type = 4, baseY = 20 } = params;
        const blocks = [];
        for (let dx = 0; dx < width; dx++)
            for (let dz = 0; dz < depth; dz++)
                blocks.push({ x: x + dx, y: baseY, z: z + dz, type });
        return relayToGame('apply_blocks', { blocks });
    }),

    fill_area: tool('Llenar un área con un tipo de bloque', {
        x: { type: 'integer', required: true }, z: { type: 'integer', required: true },
        width: { type: 'integer', required: true }, depth: { type: 'integer', required: true },
        type: { type: 'integer', required: true }, height: { type: 'integer' }, baseY: { type: 'integer' }
    }, async (params) => {
        const { x, z, width, depth, height = 1, type, baseY = 20 } = params;
        const blocks = [];
        for (let dx = 0; dx < width; dx++)
            for (let dz = 0; dz < depth; dz++)
                for (let dy = 0; dy < height; dy++)
                    blocks.push({ x: x + dx, y: baseY + dy, z: z + dz, type });
        return relayToGame('apply_blocks', { blocks });
    }),

    flat_terrain: tool('Aplanar terreno en un área', {
        x: { type: 'integer', required: true }, z: { type: 'integer', required: true },
        width: { type: 'integer', required: true }, depth: { type: 'integer', required: true },
        height: { type: 'integer' }, baseY: { type: 'integer' }
    }, async (params) => relayToGame('flat_terrain', {
        x: params.x, z: params.z, width: params.width, depth: params.depth,
        height: params.height, baseY: params.baseY
    })),

    plant_tree: tool('Plantar un árbol', {
        x: { type: 'integer', required: true }, z: { type: 'integer', required: true }
    }, async (params) => relayToGame('plant_tree', { x: params.x, z: params.z })),

    // ---- MUNDO ----
    get_world_info: tool('Obtener información del mundo', {}, async () => relayToGame('get_world_info', {})),

    // ---- VISIÓN ----
    get_view: tool('Ver qué bloque está mirando el jugador', {
        player_id: { type: 'integer', required: true }, distance: { type: 'integer' }
    }, withPlayer(async (params) => relayToGame('get_view', { player_id: params.player_id, distance: params.distance }))),

    get_nearby_blocks: tool('Obtener mapa de bloques cercanos al jugador', {
        player_id: { type: 'integer', required: true }, radius: { type: 'integer' }
    }, withPlayer(async (params) => relayToGame('get_nearby_blocks', { player_id: params.player_id, radius: params.radius }))),

    get_nearby_entities: tool('Obtener entidades cercanas al jugador', {
        player_id: { type: 'integer', required: true }, radius: { type: 'integer' }
    }, withPlayer(async (params) => relayToGame('get_nearby_entities', { player_id: params.player_id, radius: params.radius }))),

    get_environment: tool('Obtener información del entorno del jugador', {
        player_id: { type: 'integer', required: true }
    }, withPlayer(async (params) => relayToGame('get_environment', { player_id: params.player_id }))),

    get_top_down_view: tool('Vista cenital del terreno alrededor del jugador', {
        player_id: { type: 'integer', required: true }, radius: { type: 'integer' }
    }, withPlayer(async (params) => relayToGame('get_top_down_view', { player_id: params.player_id, radius: params.radius }))),

    get_camera_matrix: tool('Matriz de bloques en visión de cámara', {
        player_id: { type: 'integer', required: true },
        width: { type: 'integer' }, height: { type: 'integer' }, depth: { type: 'integer' }
    }, withPlayer(async (params) => relayToGame('get_camera_matrix', {
        player_id: params.player_id, width: params.width, height: params.height, depth: params.depth
    }))),

    get_screenshot: tool('Capturar screenshot de la cámara del jugador', {
        player_id: { type: 'integer', required: true }, width: { type: 'integer' }, height: { type: 'integer' }
    }, withPlayer(async (params) => relayToGame('get_screenshot', {
        player_id: params.player_id, width: params.width, height: params.height
    }))),

    // ---- CHAT / UTILIDADES ----
    send_message: tool('Enviar mensaje de chat', {
        player_id: { type: 'integer', required: true }, message: { type: 'string', required: true }
    }, async (params) => {
        if (gameState.onChatMessage)
            gameState.onChatMessage({ player_id: params.player_id, message: params.message });
        return { success: true };
    }),

    list_block_types: tool('Listar tipos de bloques disponibles', {}, async () => ({
        blocks: [
            { id: 0, name: 'Aire' }, { id: 1, name: 'Hierba' },
            { id: 2, name: 'Tierra' }, { id: 3, name: 'Piedra' },
            { id: 4, name: 'Madera' }, { id: 5, name: 'Hojas' },
            { id: 6, name: 'Arena' }, { id: 7, name: 'Agua' },
            { id: 8, name: 'Roca' }, { id: 9, name: 'Tablones' }
        ]
    })),

    list_avatar_colors: tool('Listar colores disponibles para avatar', {}, async () => ({
        colors: AVATAR_COLORS
    })),

    // ---- UTILIDAD ----
    teleport: tool('Teletransportar un jugador a coordenadas (x,y,z)', {
        player_id: { type: 'integer', required: true },
        x: { type: 'number', required: true }, y: { type: 'number' }, z: { type: 'number', required: true }
    }, withPlayer(async (params, player) => {
        if (params.player_id >= 3) {
            player.position = { x: params.x, y: params.y || 2, z: params.z };
            return { success: true, position: player.position };
        }
        return relayToGame('teleport', { player_id: params.player_id, x: params.x, y: params.y || 2, z: params.z });
    })),

    // ---- COMBATE ----
    attack: tool('Atacar al enemigo más cercano en cono de 90°', {
        player_id: { type: 'integer', required: true }, target_id: { type: 'integer' }
    }, withPlayer(async (params) => relayToGame('attack', { player_id: params.player_id, target_id: params.target_id }))),

    moverse_a: tool('Navegar con A* hacia coordenadas (x,z)', {
        player_id: { type: 'integer', required: true }, x: { type: 'number' }, z: { type: 'number' }
    }, withPlayer(async (params) => relayToGame('navigate_to', { player_id: params.player_id, x: params.x, z: params.z }, 30000))),

    // ---- ADMIN ----
    kill_all_monsters: tool('Eliminar todos los monstruos del mundo', {}, async () => {
        return relayToGame('console_command', { command: '/killall' });
    }),

    // ---- BEHAVIOR TREE ----
    bt_load: tool('Cargar árbol de comportamiento JSON', {
        tree: { type: 'object', required: true }
    }, async (params) => loadBehaviorTree(params.tree)),

    bt_load_example: tool('Cargar árbol de ejemplo (huir/atacar/idle)', {}, async () => {
        return loadBehaviorTree({
            comportamiento: 'Selector', nombre: 'Raiz',
            hijos: [
                { comportamiento: 'Secuencia', nombre: 'Autopreservacion', hijos: [
                    { comportamiento: 'Condicion', nombre: 'Vida Critica', variable: 'self_vida', comparacion: 'menor_que', valor_comparar: 5 },
                    { comportamiento: 'Accion', nombre: 'Huir', tipo: 'moverse_a', parametros: { x: -10, z: -10 } }
                ]},
                { comportamiento: 'Secuencia', nombre: 'Atacar Enemigo', hijos: [
                    { comportamiento: 'Condicion', nombre: 'Enemigo en Rango', variable: 'hay_enemigos_cerca', comparacion: 'verdadero' },
                    { comportamiento: 'Accion', nombre: 'Atacar', tipo: 'golpear', parametros: {} }
                ]},
                { comportamiento: 'Accion', nombre: 'Esperar', tipo: 'idle' }
            ]
        });
    }),

    bt_load_follow: tool('Cargar árbol de seguimiento al Jugador 1', {
        distancia: { type: 'number' }
    }, async (params) => {
        const dist = params.distancia || 2;
        return loadBehaviorTree({
            comportamiento: 'Selector', nombre: 'SeguirAJugador1',
            hijos: [
                { comportamiento: 'Secuencia', nombre: 'Seguir', hijos: [
                    { comportamiento: 'Accion', nombre: 'Seguir a distancia', tipo: 'seguir_a_p1', parametros: { distancia: dist } }
                ]},
                { comportamiento: 'Accion', nombre: 'Idle', tipo: 'idle' }
            ]
        });
    }),

    bt_status: tool('Estado del motor Behavior Tree', {}, async () => ({
        running: btInterval !== null,
        treeLoaded: btEngine !== null,
        lastResult: btEngine ? btEngine.lastResult : null,
        blackboard: btBlackboard
    })),

    bt_stop: tool('Detener motor Behavior Tree', {}, async () => {
        stopBtTick();
        btEngine = null;
        return { success: true, message: 'Behavior tree engine stopped' };
    }),

    // ---- AVATARES ----
    avatar_walk: tool('Mover un avatar paso a paso (dirección: north/south/east/west)', {
        player_id: { type: 'integer', required: true },
        direction: { type: 'string', required: true, enum: ['north', 'south', 'east', 'west'] },
        steps: { type: 'number' }
    }, withPlayer(async (params, player) => {
        const steps = params.steps || 1;
        const dirs = { north: [0, -1], south: [0, 1], east: [1, 0], west: [-1, 0] };
        const [dx, dz] = dirs[params.direction] || [0, 0];
        player.position.x += dx * steps;
        player.position.z += dz * steps;
        return { success: true, walked: steps, direction: params.direction,
                 position: { x: player.position.x, y: player.position.y, z: player.position.z } };
    })),

    avatars_clear: tool('Eliminar todos los avatares IA', {}, async () => {
        const removed = Object.keys(gameState.players).filter(id => id >= 3).length;
        Object.keys(gameState.players).forEach(id => { if (id >= 3) delete gameState.players[id]; });
        stopAvatarFollow();
        return { success: true, removed };
    }),

    avatars_follow: tool('Avatares IA siguen a P2', {
        activar: { type: 'boolean', description: 'true=activar, false=detener' }
    }, async (params) => {
        if (params.activar !== false) {
            startAvatarFollow();
            return { success: true, message: 'Avatares siguiendo a P2' };
        } else {
            stopAvatarFollow();
            return { success: true, message: 'Avatares detenidos' };
        }
    }),

    get_avatars: tool('Obtener lista de avatares IA con sus posiciones', {}, async () => {
        const avatars = Object.entries(gameState.players)
            .filter(([id]) => id >= 3)
            .map(([id, p]) => ({ id: parseInt(id), x: p.position.x, y: p.position.y, z: p.position.z }));
        return { avatars };
    }),

    // ---- ENTRENAMIENTO ----
    training_start: tool('Iniciar grabación de episodio de entrenamiento (BC)', {
        scenario: { type: 'string', required: true, description: 'Nombre del escenario (ej: subir_escalera)' }
    }, async (params) => relayToGame('training_start', params, 3600000)),

    training_stop: tool('Detener grabación de episodio de entrenamiento', {
        exito: { type: 'boolean', description: 'Si la demostración fue exitosa' }
    }, async (params) => relayToGame('training_stop', params, 60000))
};

// Función auxiliar para crear avatar
function createAvatar(params) {
    const { name, gender, hairStyle, hairColor, eyeColor, shirtColor, pantsColor, spawnX, spawnZ } = params;
    const id = nextPlayerId++;

    gameState.players[id] = {
        name: name || `IA_${id}`,
        isAI: true,
        gender: gender || 'male',
        position: { x: spawnX || 0, y: 2, z: spawnZ || 0 },
        rotation: { x: 0, y: 0 },
        health: 20,
        onGround: false,
        isFlying: false,
        selectedSlot: 0,
        inventory: [],
        config: { gender, hairStyle, hairColor, eyeColor, shirtColor, pantsColor }
    };

    return {
        success: true,
        playerId: id,
        name: gameState.players[id].name,
        message: `Avatar "${gameState.players[id].name}" creado con ID ${id}`
    };
}

// ============================================================
// MCP PROTOCOL (Model Context Protocol - JSON-RPC 2.0)
// ============================================================

// Auto-generadas desde tool() en mcpHandlers
const mcpToolDefinitions = Object.entries(mcpHandlers)
    .filter(([_, h]) => h._mcp)
    .map(([name, handler]) => ({
        name,
        description: handler._mcp.description,
        inputSchema: buildSchema(handler._mcp.schema)
    }));

const mcpToolNames = new Set(mcpToolDefinitions.map(t => t.name));

// Manejador JSON-RPC 2.0 para el protocolo MCP
async function handleJsonRpc(request) {
    if (request.jsonrpc !== '2.0') {
        return { error: { code: -32600, message: 'Invalid Request: jsonrpc must be 2.0' } };
    }

    switch (request.method) {
        case 'initialize': {
            return {
                protocolVersion: '2024-11-05',
                capabilities: {
                    tools: {},
                    resources: {}
                },
                serverInfo: { name: 'VoxelQuest Game Server', version: '3.0' }
            };
        }

        case 'ping':
            return {};

        case 'tools/list':
            return { tools: mcpToolDefinitions };

        case 'tools/call': {
            const { name, arguments: args } = request.params || {};
            if (!name) return { error: { code: -32602, message: 'Invalid params: tool name required' } };
            if (!mcpToolNames.has(name)) return { error: { code: -32602, message: `Unknown tool: ${name}` } };
            const handler = mcpHandlers[name];
            if (!handler) return { error: { code: -32603, message: `No handler for tool: ${name}` } };
            try {
                const result = await handler(args || {});
                return { content: [{ type: 'text', text: JSON.stringify(result) }] };
            } catch (e) {
                return { error: { code: -32603, message: e.message } };
            }
        }

        case 'resources/list':
            return { resources: [] };

        case 'notifications/initialized':
            return null; // no response

        default:
            return { error: { code: -32601, message: `Method not found: ${request.method}` } };
    }
}

// ============================================================
// SERVIDOR HTTP (sirve juego + API JSON-RPC 2.0)
// ============================================================
const MIME_TYPES = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.mp3': 'audio/mpeg',
    '.ogg': 'audio/ogg',
    '.wav': 'audio/wav'
};

const ROOT_DIR = __dirname;

const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS, GET');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    // === API Endpoints ===

    if (req.method === 'GET' && req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', players: Object.keys(gameState.players).length }));
        return;
    }

    if (req.method === 'GET' && req.url === '/tools') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ tools: mcpToolDefinitions.map(t => t.name) }));
        return;
    }

    // JSON-RPC 2.0 API endpoint (para scripts Python y otros clientes HTTP)
    if (req.method === 'POST' && req.url === '/mcp') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const request = JSON.parse(body);

                // Si tiene jsonrpc: "2.0", es MCP protocol
                if (request.jsonrpc === '2.0') {
                    const result = await handleJsonRpc(request);
                    // notifications no llevan respuesta
                    if (request.method && request.method.startsWith('notifications/')) {
                        res.writeHead(202);
                        res.end();
                        return;
                    }
                    const response = { jsonrpc: '2.0', id: request.id || null };
                    if (result.error) {
                        response.error = result.error;
                    } else {
                        response.result = result;
                    }
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify(response));
                    return;
                }

                // Fallback: si no es JSON-RPC 2.0, error
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    jsonrpc: '2.0',
                    id: null,
                    error: { code: -32600, message: 'Invalid Request: expected jsonrpc 2.0' }
                }));
            } catch (error) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    jsonrpc: '2.0',
                    id: null,
                    error: { code: -32700, message: 'Parse error: ' + error.message }
                }));
            }
        });
        return;
    }

    // === Static file serving (juego) ===

    if (req.method === 'GET') {
        let urlPath = req.url.split('?')[0];
        if (urlPath === '/') urlPath = '/index.html';

        const filePath = path.join(ROOT_DIR, urlPath);
        const ext = path.extname(filePath).toLowerCase();

        // Security: prevent directory traversal
        if (!filePath.startsWith(ROOT_DIR)) {
            res.writeHead(403);
            res.end('Forbidden');
            return;
        }

        fs.readFile(filePath, (err, data) => {
            if (err) {
                res.writeHead(404);
                res.end('Not found');
                return;
            }
            const mime = MIME_TYPES[ext] || 'application/octet-stream';
            res.writeHead(200, { 'Content-Type': mime, 'Cache-Control': 'no-store' });
            res.end(data);
        });
        return;
    }

    res.writeHead(404);
    res.end('Not found');
});

// ============================================================
// WEBSOCKET SERVER
// ============================================================
const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
    log('[WS] Cliente conectado');
    gameClients.push(ws);

    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message.toString());

            // ---- Cliente API (mcp-server.js, scripts): JSON-RPC 2.0 ----
            if (data.jsonrpc === '2.0') {
                handleJsonRpc(data).then(result => {
                    if (data.method && data.method.startsWith('notifications/')) return;
                    const response = { jsonrpc: '2.0', id: data.id || null };
                    if (result?.error) response.error = result.error;
                    else response.result = result;
                    if (ws.readyState === WebSocket.OPEN)
                        ws.send(JSON.stringify(response));
                });
                return;
            }

            // ---- Navegador: respuesta a un comando relay (correlación por id) ----
            if (data.id && pendingMcp[data.id]) {
                const { resolve, timer } = pendingMcp[data.id];
                clearTimeout(timer);
                delete pendingMcp[data.id];
                const { id, ...rest } = data;
                resolve(rest);
                return;
            }

            // ---- Navegador: actualizaciones de estado ----
            if (data.type === 'state_update' && data.state && data.state.players) {
                Object.entries(data.state.players).forEach(([id, p]) => {
                    if (gameState.players[id]) {
                        if (p.position) gameState.players[id].position = p.position;
                        if (p.health !== undefined) gameState.players[id].health = p.health;
                        if (p.rotation) gameState.players[id].rotation = p.rotation;
                        if (p.onGround !== undefined) gameState.players[id].onGround = p.onGround;
                        if (p.isFlying !== undefined) gameState.players[id].isFlying = p.isFlying;
                    }
                });

                if (data.state.entities) {
                    const enemies = data.state.entities.filter(e => e.type === 'enemy');
                    gameState.enemies = enemies.map(e => ({ x: e.position.x, z: e.position.z, id: e.id }));
                    const nearest = enemies.sort((a, b) => a.distance - b.distance)[0];
                    btBlackboard.hay_enemigos_cerca = enemies.length > 0;
                    if (nearest) {
                        btBlackboard.target_enemigo_id = nearest.id || nearest.enemyType;
                        btBlackboard.target_enemigo_x = nearest.position ? nearest.position.x : nearest.x;
                        btBlackboard.target_enemigo_z = nearest.position ? nearest.position.z : nearest.z;
                    }
                }
            }

            // Heartbeat ligero para BT (10Hz)
            if (data.type === 'bt_heartbeat') {
                if (data.gameMode) gameState.mode = data.gameMode;
                const p2 = gameState.players[2];
                if (p2) {
                    if (data.position) p2.position = data.position;
                    if (data.health !== undefined) p2.health = data.health;
                    if (data.rotation) p2.rotation = data.rotation;
                    if (data.isFlying !== undefined) p2.isFlying = data.isFlying;
                }
                // Actualizar posición de P1 en el blackboard
                if (data.p1_position) {
                    btBlackboard.p1_x = data.p1_position.x;
                    btBlackboard.p1_z = data.p1_position.z;
                    btBlackboard.p1_y = data.p1_position.y;
                }
                // Sensores del jugador
                if (data.onGround !== undefined) btBlackboard.onGround = data.onGround;
                if (data.stuck !== undefined) btBlackboard.stuck = data.stuck;
                if (data.rotation) btBlackboard.self_rot_y = data.rotation.y;
                // Enviar avatares al navegador junto al heartbeat
                const avs = Object.entries(gameState.players)
                    .filter(([id]) => id >= 3)
                    .map(([id, p]) => ({ id: parseInt(id), x: p.position.x, y: p.position.y, z: p.position.z }));
                if (avs.length > 0) {
                    ws.send(JSON.stringify({ method: 'avatar_update', params: { avatars: avs } }));
                }
                if (data.bloque_bajo !== undefined) btBlackboard.bloque_bajo = data.bloque_bajo;
                if (data.bloque_frente_altura !== undefined) btBlackboard.bloque_frente_altura = data.bloque_frente_altura;
                if (data.nearest_enemy) {
                    btBlackboard.hay_enemigos_cerca = true;
                    btBlackboard.target_enemigo_id = data.nearest_enemy.id;
                    btBlackboard.target_enemigo_x = data.nearest_enemy.x;
                    btBlackboard.target_enemigo_z = data.nearest_enemy.z;
                } else {
                    btBlackboard.hay_enemigos_cerca = false;
                }
            }

            // ---- Episodio de entrenamiento ----
            if (data.type === 'episode_save') {
                const scenario = data.scenario || 'unknown';
                const dir = path.join(__dirname, 'training', 'episodes', scenario);
                try { fs.mkdirSync(dir, { recursive: true }); } catch (_) {}
                const filename = Date.now() + '.jsonl';
                fs.writeFileSync(path.join(dir, filename), data.episode || '');
                log(`[Training] Episodio guardado: ${scenario}/${filename} (${data.episode?.split('\n').length || 0} frames)`);
            }
        } catch (e) {
            // Silently ignore parse errors from game
        }
    });

    ws.on('close', () => {
        gameClients = gameClients.filter(c => c !== ws);
        log('[WS] Cliente desconectado');
    });

    ws.on('error', () => {
        gameClients = gameClients.filter(c => c !== ws);
    });
});

// ============================================================
// GLOBAL ERROR HANDLER
// ============================================================
process.on('uncaughtException', (err) => {
    console.error('[FATAL]', err.message);
});

process.on('unhandledRejection', (err) => {
    console.error('[REJECT]', err);
});

// ============================================================
// EXPORTS
module.exports = { gameState, mcpHandlers, mcpToolDefinitions, STRUCTURES, AVATAR_COLORS, server };

if (require.main === module) {
    const PORT = process.env.PORT || 9000;
    server.listen(PORT, () => {
        const url = `http://localhost:${PORT}`;
        log(`\n🎮 VoxelQuest Game Server`);
        log(`   Juego:     ${url}`);
        log(`   API:       ${url}/mcp (JSON-RPC 2.0)`);
        log(`   WebSocket: ws://localhost:${PORT}`);
        log(`   Health:    ${url}/health`);
        log(`   Tools:     ${url}/tools\n`);

        try {
            const { exec } = require('child_process');
            const cmd = process.platform === 'darwin' ? 'open' : process.platform === 'win32' ? 'start' : 'xdg-open';
            exec(`${cmd} ${url}`);
        } catch (e) {}
    });
}
