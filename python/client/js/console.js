/**
 * Consola de comandos para VoxelQuest Python Client.
 * Activar con T o ~. Envía comandos via MCP al servidor.
 */

class GameConsole {
    constructor(game) {
        this.game = game;
        this.isOpen = false;
        this.commandHistory = [];
        this.historyIndex = -1;
        this.mcpUrl = `http://${window.location.hostname || 'localhost'}:9000/mcp`;

        this.createUI();
        this.setupKeyBindings();
    }

    createUI() {
        this.container = document.createElement('div');
        this.container.id = 'game-console';
        this.container.style.cssText = `
            position: fixed; bottom: 10px; left: 10px; width: 500px; max-height: 300px;
            background: rgba(0, 0, 0, 0.75); border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px; padding: 10px; font-family: 'Courier New', monospace;
            font-size: 13px; color: #0f0; z-index: 1000; display: none; pointer-events: auto;
        `;

        this.messages = document.createElement('div');
        this.messages.style.cssText = `
            height: 200px; overflow-y: auto; margin-bottom: 8px; padding: 5px;
            background: rgba(0, 0, 0, 0.3); border-radius: 4px;
        `;
        this.container.appendChild(this.messages);

        this.input = document.createElement('input');
        this.input.type = 'text';
        this.input.placeholder = 'Escribe un comando... (usa /help)';
        this.input.style.cssText = `
            width: 100%; padding: 8px; background: rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(0, 255, 0, 0.3); border-radius: 4px;
            color: #0f0; font-family: 'Courier New', monospace; font-size: 13px; outline: none;
        `;
        this.input.addEventListener('keydown', (e) => {
            e.stopPropagation();
            if (e.key === 'Enter') {
                this.executeCommand(this.input.value);
                this.input.value = '';
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.historyUp();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.historyDown();
            } else if (e.key === 'Escape') {
                this.close();
            }
        });
        this.container.appendChild(this.input);
        document.body.appendChild(this.container);

        this.addMessage('Consola de comandos. Escribe /help para ver comandos.', '#888');
    }

    setupKeyBindings() {
        document.addEventListener('keydown', (e) => {
            if (e.code === 'KeyT' || e.code === 'Backquote') {
                if (document.activeElement.tagName === 'INPUT') return;
                e.preventDefault();
                this.toggle();
            }
        });
    }

    toggle() { this.isOpen ? this.close() : this.open(); }

    open() {
        this.isOpen = true;
        this.container.style.display = 'block';
        this.input.focus();
        if (document.pointerLockElement) {
            document.exitPointerLock();
        }
    }

    close() {
        this.isOpen = false;
        this.container.style.display = 'none';
        this.input.blur();
    }

    addMessage(text, color = '#0f0') {
        const msg = document.createElement('div');
        msg.style.color = color;
        msg.style.marginBottom = '4px';
        msg.style.wordWrap = 'break-word';
        msg.textContent = text;
        this.messages.appendChild(msg);
        this.messages.scrollTop = this.messages.scrollHeight;
    }

    historyUp() {
        if (this.historyIndex < this.commandHistory.length - 1) {
            this.historyIndex++;
            this.input.value = this.commandHistory[this.historyIndex];
        }
    }

    historyDown() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            this.input.value = this.commandHistory[this.historyIndex];
        } else {
            this.historyIndex = -1;
            this.input.value = '';
        }
    }

    async executeCommand(input) {
        if (!input.trim()) return;
        this.commandHistory.push(input);
        this.historyIndex = -1;
        this.addMessage(`> ${input}`, '#fff');

        const parts = input.trim().split(' ');
        const cmd = parts[0].toLowerCase();
        const args = parts.slice(1);

        switch (cmd) {
            case '/help': this.showHelp(); break;
            case '/fly': this.toggleFly(); break;
            case '/tp': this.teleport(args); break;
            case '/pos': this.showPosition(); break;
            case '/clear': this.messages.innerHTML = ''; this.addMessage('Consola limpiada', '#888'); break;
            case '/time': this.setTime(args[0]); break;
            default:
                try {
                    const resp = await fetch(this.mcpUrl, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            jsonrpc: '2.0', id: Date.now(),
                            method: 'tools/call',
                            params: { name: cmd.replace('/', ''), arguments: this._buildMcpArgs(cmd, args) }
                        })
                    });
                    const data = await resp.json();
                    if (data.result) {
                        this.addMessage(JSON.stringify(data.result), '#0f0');
                    } else if (data.error) {
                        this.addMessage(`Error: ${data.error.message || JSON.stringify(data.error)}`, '#f44');
                    }
                } catch (err) {
                    this.addMessage(`Error de red: ${err.message}`, '#f44');
                }
        }
    }

    _buildMcpArgs(cmd, args) {
        const map = {
            '/tp': { player_id: 1, x: parseFloat(args[0]) || 0, y: parseFloat(args[1]) || 30, z: parseFloat(args[2]) || 0 },
            '/give': { player_id: 1, block_type: args[0] || 'wood', count: parseInt(args[1]) || 1 },
            '/time': { time: args[0] || 'day' },
        };
        return map[cmd] || { player_id: 1 };
    }

    showHelp() {
        const help = [
            '--- COMANDOS ---',
            '/help    - Muestra esta ayuda',
            '/fly     - Activa/desactiva vuelo',
            '/tp x y z - Teletransporta',
            '/time <day|night> - Cambia hora',
            '/pos     - Muestra posición',
            '/clear   - Limpia consola',
            '/give    - Da items (via MCP)',
            '/killall - Mata enemigos (via MCP)',
        ];
        help.forEach(l => this.addMessage(l, '#88f'));
    }

    toggleFly() {
        const input = this.game.inputs && this.game.inputs[0];
        if (input) {
            input.flying = !input.flying;
            this.addMessage(`Vuelo: ${input.flying ? 'ACTIVADO' : 'DESACTIVADO'}`, '#0f0');
        }
    }

    teleport(args) {
        if (args.length < 3) { this.addMessage('Uso: /tp <x> <y> <z>', '#f44'); return; }
        this.addMessage(`TP -> (${args[0]}, ${args[1]}, ${args[2]}) (via MCP)`, '#0f0');
        this.executeCommand(`/tp ${args.join(' ')}`);
    }

    showPosition() {
        const p = this.game.targetStates && this.game.targetStates[0];
        if (p) this.addMessage(`Posición: (${p.x.toFixed(1)}, ${p.y.toFixed(1)}, ${p.z.toFixed(1)})`, '#ff0');
        else this.addMessage('Sin posición disponible', '#888');
    }

    setTime(time) {
        this.addMessage(`Hora: ${time} (via MCP)`, '#0f0');
    }
}

window.GameConsole = GameConsole;
