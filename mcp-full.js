#!/usr/bin/env node
/**
 * VoxelQuest MCP Server - Full Version
 * 
 * Servidor MCP completo con WebSocket para comunicación con el juego.
 * Recibe comandos HTTP y los envía al juego via WebSocket.
 */

const http = require('http');
const WebSocket = require('ws');

// Estado del juego
const gameState = {
    players: {
        1: { name: 'Jugador 1', position: { x: 8, y: 25, z: 8 }, health: 20, inventory: [] },
        2: { name: 'Jugador 2', position: { x: 10, y: 25, z: 10 }, health: 20, inventory: [] }
    },
    connected: false,
    gameClients: [] // WebSocket connections from game
};

// Cola de comandos pendientes
let pendingCommands = [];
let commandCallbacks = {};

// MCP Handlers
const handlers = {
    list_players: () => ({
        players: Object.entries(gameState.players).map(([id, p]) => ({
            id: parseInt(id),
            name: p.name,
            position: p.position,
            health: p.health
        }))
    }),

    get_player_state: (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return { id: params.player_id, ...player };
    },

    move_player: (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        // Actualizar estado local
        player.position = { x: params.x, y: params.y, z: params.z };
        
        // Enviar comando al juego
        sendToGame({
            command: 'move_player',
            player_id: params.player_id,
            x: params.x,
            y: params.y,
            z: params.z
        });
        
        return { success: true, position: player.position };
    },

    place_block: (params) => {
        sendToGame({
            command: 'place_block',
            x: params.x,
            y: params.y,
            z: params.z,
            type: params.type
        });
        return { success: true };
    },

    break_block: (params) => {
        sendToGame({
            command: 'break_block',
            x: params.x,
            y: params.y,
            z: params.z
        });
        return { success: true };
    },

    execute_command: (params) => {
        sendToGame({
            command: 'execute_command',
            text: params.command
        });
        return { success: true, command: params.command };
    },

    get_config: () => ({
        connected: gameState.connected,
        playerCount: Object.keys(gameState.players).length
    }),

    health: () => ({
        status: 'ok',
        connected: gameState.connected,
        gameClients: gameState.gameClients.length
    })
};

// Enviar comando al juego via WebSocket
function sendToGame(data) {
    const message = JSON.stringify(data);
    gameState.gameClients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(message);
        }
    });
}

// HTTP Server
const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS, GET');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    if (req.method === 'GET') {
        if (req.url === '/health') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(handlers.health()));
            return;
        }
        if (req.url === '/tools') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ tools: Object.keys(handlers) }));
            return;
        }
    }

    if (req.method === 'POST' && req.url === '/mcp') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            try {
                const request = JSON.parse(body);
                const handler = handlers[request.method];
                if (!handler) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: `Método desconocido: ${request.method}` }));
                    return;
                }
                const result = handler(request.params || {});
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(result));
            } catch (error) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: error.message }));
            }
        });
    } else {
        res.writeHead(404);
        res.end('Not found');
    }
});

// WebSocket Server
const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
    console.log('[WS] Juego conectado');
    gameState.gameClients.push(ws);
    gameState.connected = true;

    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            console.log('[WS] Recibido:', data.type || data.command);
            
            // Actualizar estado desde el juego
            if (data.type === 'state_update' && data.state) {
                if (data.state.players) {
                    Object.entries(data.state.players).forEach(([id, p]) => {
                        if (gameState.players[id]) {
                            gameState.players[id].position = p.position;
                            gameState.players[id].health = p.health;
                        }
                    });
                }
            }
        } catch (e) {
            console.error('[WS] Error:', e.message);
        }
    });

    ws.on('close', () => {
        console.log('[WS] Juego desconectado');
        gameState.gameClients = gameState.gameClients.filter(c => c !== ws);
        if (gameState.gameClients.length === 0) {
            gameState.connected = false;
        }
    });
});

// Start
const PORT = process.env.MCP_PORT || 3001;
server.listen(PORT, () => {
    console.log(`\n🎮 VoxelQuest MCP Server`);
    console.log(`   HTTP: http://localhost:${PORT}/mcp`);
    console.log(`   WebSocket: ws://localhost:${PORT}`);
    console.log(`   Health: http://localhost:${PORT}/health`);
    console.log(`\n   Esperando conexión del juego...\n`);
});
