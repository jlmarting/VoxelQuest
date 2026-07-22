#!/usr/bin/env node
/**
 * VoxelQuest MCP Server
 *
 * Servidor MCP puro con transporte stdio nativo.
 * Se conecta al game server vía WebSocket y traduce:
 *   stdio (MCP/JSON-RPC) ←→ WebSocket (API del game server)
 *
 * No contiene lógica de tools ni estado de juego.
 * Es un adaptador de protocolo delgado.
 *
 * Uso:
 *   node mcp-server.js                              # game server en ws://localhost:9000
 *   GAME_SERVER_URL=ws://localhost:9001 node mcp-server.js
 */

const WebSocket = require('ws');
const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { CallToolRequestSchema, ListToolsRequestSchema } = require('@modelcontextprotocol/sdk/types.js');

const GAME_URL = process.env.GAME_SERVER_URL || 'ws://localhost:9000';

// ---- Conexión WebSocket al game server ----
let ws;
const pending = {};

function connect() {
    ws = new WebSocket(GAME_URL);

    ws.on('open', () => {
        process.stderr.write(`[MCP] Conectado a ${GAME_URL}\n`);
    });

    ws.on('message', (msg) => {
        try {
            const data = JSON.parse(msg.toString());
            if (data.jsonrpc && pending[data.id]) {
                pending[data.id](data);
                delete pending[data.id];
            }
        } catch (e) {}
    });

    ws.on('close', () => {
        process.stderr.write('[MCP] Game server desconectado, reintentando en 1s...\n');
        setTimeout(connect, 1000);
    });

    ws.on('error', () => {});
}

function rpc(method, params = {}, timeoutMs = 30000) {
    return new Promise((resolve) => {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            resolve({ error: { code: -32603, message: 'Game server no conectado' } });
            return;
        }
        const id = Date.now() + '_' + Math.random().toString(36).slice(2);
        pending[id] = resolve;
        ws.send(JSON.stringify({ jsonrpc: '2.0', id, method, params }));
        setTimeout(() => {
            if (pending[id]) {
                delete pending[id];
                resolve({ error: { code: -32603, message: 'Timeout esperando game server' } });
            }
        }, timeoutMs);
    });
}

// ---- Servidor MCP (stdio) ----
const mcpServer = new Server(
    { name: 'VoxelQuest MCP Server', version: '1.0' },
    { capabilities: { tools: {} } }
);

mcpServer.setRequestHandler(ListToolsRequestSchema, async () => {
    const res = await rpc('tools/list');
    return res.result || { tools: [] };
});

mcpServer.setRequestHandler(CallToolRequestSchema, async (request) => {
    const res = await rpc('tools/call', request.params);
    if (res.error) {
        return { content: [{ type: 'text', text: JSON.stringify({ error: res.error }) }] };
    }
    return res.result || { content: [{ type: 'text', text: '{}' }] };
});

// ---- Start ----
connect();

(async () => {
    const transport = new StdioServerTransport();
    await mcpServer.connect(transport);
    process.stderr.write('[MCP] Transporte stdio activo\n');
})();