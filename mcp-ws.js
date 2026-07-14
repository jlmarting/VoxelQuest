#!/usr/bin/env node
/**
 * VoxelQuest MCP Server - WebSocket Only
 * Simple WebSocket server for game communication
 */

const http = require('http');
const WebSocket = require('ws');

let gameConnection = null;
let pendingResponses = {};

const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Content-Type', 'application/json');

    if (req.url === '/health') {
        res.end(JSON.stringify({ status: 'ok', connected: !!gameConnection }));
        return;
    }

    if (req.url === '/mcp' && req.method === 'POST') {
        let body = '';
        req.on('data', c => body += c);
        req.on('end', () => {
            try {
                const data = JSON.parse(body);
                console.log('[HTTP] Command:', data.method);

                if (!gameConnection) {
                    res.end(JSON.stringify({ error: 'Game not connected' }));
                    return;
                }

                // Forward to game and wait for response
                const id = Date.now().toString();
                pendingResponses[id] = res;

                gameConnection.send(JSON.stringify({ id, ...data }));

                // Timeout after 5 seconds
                setTimeout(() => {
                    if (pendingResponses[id]) {
                        delete pendingResponses[id];
                        res.end(JSON.stringify({ error: 'Timeout' }));
                    }
                }, 5000);
            } catch (e) {
                res.end(JSON.stringify({ error: e.message }));
            }
        });
        return;
    }

    res.end(JSON.stringify({ error: 'Not found' }));
});

const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
    console.log('[WS] Game connected!');
    gameConnection = ws;

    ws.on('message', (msg) => {
        try {
            const data = JSON.parse(msg);
            console.log('[WS] From game:', data.type || data.id || 'response');

            // Handle responses from game
            if (data.id && pendingResponses[data.id]) {
                const res = pendingResponses[data.id];
                delete pendingResponses[data.id];
                res.end(JSON.stringify(data));
            }
        } catch (e) {
            console.error('[WS] Error:', e.message);
        }
    });

    ws.on('close', () => {
        console.log('[WS] Game disconnected');
        gameConnection = null;
    });
});

server.listen(3001, () => {
    console.log('VoxelQuest MCP Server on port 3001');
});
