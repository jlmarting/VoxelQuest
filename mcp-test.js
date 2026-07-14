#!/usr/bin/env node
/**
 * VoxelQuest MCP Server - Test Version
 */

const http = require('http');

// Mock game state
const gameState = {
    players: {
        1: { name: 'Jugador 1', isAI: false, position: { x: 8, y: 25, z: 8 }, health: 20, inventory: [] },
        2: { name: 'Jugador 2', isAI: false, position: { x: 10, y: 25, z: 10 }, health: 20, inventory: [] }
    },
    world: null,
    running: true
};

// Simple MCP handlers
const handlers = {
    get_config: () => ({
        approvalMode: 'auto',
        playerCount: Object.keys(gameState.players).length,
        players: Object.entries(gameState.players).map(([id, p]) => ({
            id: parseInt(id), name: p.name, position: p.position
        }))
    }),

    get_player_state: (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Player not found' };
        return { id: params.player_id, name: player.name, position: player.position, health: player.health };
    },

    move_player: (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Player not found' };
        player.position = { x: params.x, y: params.y, z: params.z };
        return { success: true, position: player.position };
    },

    list_players: () => ({
        players: Object.entries(gameState.players).map(([id, p]) => ({
            id: parseInt(id), name: p.name, position: p.position
        }))
    }),

    get_nearby_blocks: (params) => ({
        message: 'Mock: 25 blocks nearby',
        radius: params.radius || 5
    }),

    flat_terrain: (params) => ({
        success: true,
        message: `Would flatten ${params.width || 10}x${params.depth || 10} area`
    })
};

// Create server
const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS, GET');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    if (req.method === 'GET' && req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', players: Object.keys(gameState.players).length }));
        return;
    }

    if (req.method === 'GET' && req.url === '/tools') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ tools: Object.keys(handlers) }));
        return;
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
                    res.end(JSON.stringify({ error: `Unknown method: ${request.method}` }));
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

const PORT = 3001;
server.listen(PORT, () => {
    console.log(`VoxelQuest MCP Test Server running on port ${PORT}`);
});
