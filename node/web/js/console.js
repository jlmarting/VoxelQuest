/**
 * VoxelQuest In-Game Console
 * 
 * Consola translúcida para ejecutar comandos.
 * Activar con tecla T o ~
 */

class GameConsole {
    constructor(game) {
        this.game = game;
        this.isOpen = false;
        this.commandHistory = [];
        this.historyIndex = -1;
        this.currentInput = '';

        // Configuración del juego
        this.config = {
            monsters: true,
            fly: false,
            god: false,
            time: null,
            speed: 1
        };

        this.createUI();
        this.setupKeyBindings();
    }

    createUI() {
        // Contenedor principal
        this.container = document.createElement('div');
        this.container.id = 'game-console';
        this.container.style.cssText = `
            position: fixed;
            bottom: 10px;
            left: 10px;
            width: 500px;
            max-height: 300px;
            background: rgba(0, 0, 0, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #0f0;
            z-index: 1000;
            display: none;
            pointer-events: auto;
        `;

        // Área de mensajes
        this.messages = document.createElement('div');
        this.messages.style.cssText = `
            height: 200px;
            overflow-y: auto;
            margin-bottom: 8px;
            padding: 5px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 4px;
        `;
        this.container.appendChild(this.messages);

        // Input
        this.input = document.createElement('input');
        this.input.type = 'text';
        this.input.placeholder = 'Escribe un comando... (usa /help)';
        this.input.style.cssText = `
            width: 100%;
            padding: 8px;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(0, 255, 0, 0.3);
            border-radius: 4px;
            color: #0f0;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            outline: none;
        `;
        this.input.addEventListener('keydown', (e) => {
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
            e.stopPropagation();
        });
        this.container.appendChild(this.input);

        document.body.appendChild(this.container);

        this.addMessage('Consola de comandos. Escribe /help para ver comandos.', '#888');
    }

    setupKeyBindings() {
        document.addEventListener('keydown', (e) => {
            // T o ~ para abrir/cerrar consola
            if (e.code === 'KeyT' || e.code === 'Backquote') {
                if (!this.game.running) return;
                // No abrir si hay otro input enfocado
                if (document.activeElement.tagName === 'INPUT') return;
                
                e.preventDefault();
                this.toggle();
            }
        });
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        this.isOpen = true;
        this.container.style.display = 'block';
        this.input.focus();
        // Pausar controles del juego
        if (this.game.player1) this.game.player1.keys = {};
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

    executeCommand(input) {
        if (!input.trim()) return;

        this.commandHistory.push(input);
        this.historyIndex = -1;
        this.addMessage(`> ${input}`, '#fff');

        const parts = input.trim().split(' ');
        const cmd = parts[0].toLowerCase();
        const args = parts.slice(1);

        switch (cmd) {
            case '/help':
                this.showHelp();
                break;
            case '/no_monsters':
            case '/nomonsters':
                this.toggleMonsters();
                break;
            case '/monsters':
                this.enableMonsters();
                break;
            case '/time':
                this.setTime(args[0]);
                break;
            case '/tp':
            case '/teleport':
                this.teleport(args);
                break;
            case '/give':
                this.giveItem(args);
                break;
            case '/fly':
                this.toggleFly();
                break;
            case '/god':
                this.toggleGod();
                break;
            case '/speed':
                this.setSpeed(args[0]);
                break;
            case '/day':
                this.setTime('day');
                break;
            case '/night':
                this.setTime('night');
                break;
            case '/spawn':
                this.spawnMonster(args);
                break;
            case '/killall':
                this.killAllMonsters();
                break;
            case '/heal':
                this.heal();
                break;
            case '/clear':
                this.clearConsole();
                break;
            case '/pos':
                this.showPosition();
                break;
            case '/config':
                this.showConfig();
                break;
            default:
                this.addMessage(`Comando desconocido: ${cmd}. Usa /help`, '#f44');
        }
    }

    showHelp() {
        const help = [
            '--- COMANDOS DISPONIBLES ---',
            '/help - Muestra esta ayuda',
            '/no_monsters - Desactiva monstruos',
            '/monsters - Activa monstruos',
            '/time <día|noche|0-1> - Cambia hora',
            '/day - Pone día',
            '/night - Pone noche',
            '/tp <x> <y> <z> - Teletransporta',
            '/give <tipo> [cantidad] - Da items',
            '/fly - Activa/desactiva vuelo',
            '/god - Modo invencible',
            '/speed <velocidad> - Cambia velocidad',
            '/spawn <tipo> - Genera monstruo',
            '/killall - Mata todos los monstruos',
            '/heal - Cura al jugador',
            '/pos - Muestra posición',
            '/config - Muestra configuración',
            '/clear - Limpia consola'
        ];
        help.forEach(line => this.addMessage(line, '#88f'));
    }

    toggleMonsters() {
        this.config.monsters = !this.config.monsters;
        this.game.enemyManager.spawnCooldown = this.config.monsters ? 5000 : 999999;
        
        if (!this.config.monsters) {
            // Eliminar monstruos existentes
            this.game.enemyManager.enemies.forEach(e => {
                this.game.scene.remove(e.mesh);
            });
            this.game.enemyManager.enemies = [];
            this.addMessage('Monstruos desactivados y eliminados', '#ff0');
        } else {
            this.addMessage('Monstruos activados', '#0f0');
        }
    }

    enableMonsters() {
        this.config.monsters = true;
        this.game.enemyManager.spawnCooldown = 5000;
        this.addMessage('Monstruos activados', '#0f0');
    }

    setTime(time) {
        if (!this.game.dayNight) return;
        
        switch (time) {
            case 'day':
                this.game.dayNight.timeOfDay = 0.5;
                this.addMessage('Hora: Día (mediodía)', '#ff0');
                break;
            case 'night':
                this.game.dayNight.timeOfDay = 0.0;
                this.addMessage('Hora: Noche (medianoche)', '#ff0');
                break;
            case 'sunrise':
                this.game.dayNight.timeOfDay = 0.25;
                this.addMessage('Hora: Amanecer', '#ff0');
                break;
            case 'sunset':
                this.game.dayNight.timeOfDay = 0.75;
                this.addMessage('Hora: Atardecer', '#ff0');
                break;
            default:
                const val = parseFloat(time);
                if (!isNaN(val) && val >= 0 && val <= 1) {
                    this.game.dayNight.timeOfDay = val;
                    this.addMessage(`Hora: ${val.toFixed(2)}`, '#ff0');
                } else {
                    this.addMessage('Uso: /time <day|night|sunrise|sunset|0-1>', '#f44');
                }
        }
    }

    teleport(args) {
        if (args.length < 3) {
            this.addMessage('Uso: /tp <x> <y> <z>', '#f44');
            return;
        }

        const x = parseFloat(args[0]);
        const y = parseFloat(args[1]);
        const z = parseFloat(args[2]);

        if (isNaN(x) || isNaN(y) || isNaN(z)) {
            this.addMessage('Coordenadas inválidas', '#f44');
            return;
        }

        const player = this.game[`player${this.game.activePlayer}`];
        player.position.set(x, y, z);
        this.addMessage(`Teletransportado a (${x}, ${y}, ${z})`, '#0f0');
    }

    giveItem(args) {
        if (args.length < 1) {
            this.addMessage('Uso: /give <tipo> [cantidad]', '#f44');
            return;
        }

        const itemName = args[0].toLowerCase();
        const count = parseInt(args[1]) || 1;

        // Mapear nombres a tipos
        const itemMap = {
            'wood': BLOCK_TYPES.WOOD,
            'stone': BLOCK_TYPES.STONE,
            'dirt': BLOCK_TYPES.DIRT,
            'grass': BLOCK_TYPES.GRASS,
            'sand': BLOCK_TYPES.SAND,
            'planks': BLOCK_TYPES.PLANKS,
            'leaves': BLOCK_TYPES.LEAVES,
            'cobble': BLOCK_TYPES.COBBLESTONE
        };

        const itemType = itemMap[itemName];
        if (itemType === undefined) {
            this.addMessage(`Item desconocido: ${itemName}. Usa: wood, stone, dirt, grass, sand, planks, leaves, cobble`, '#f44');
            return;
        }

        const player = this.game[`player${this.game.activePlayer}`];
        player.inventory.addItem(itemType, count);
        this.addMessage(`+${count} ${BLOCK_NAMES[itemType] || itemName}`, '#0f0');
    }

    toggleFly() {
        const player = this.game[`player${this.game.activePlayer}`];
        player.isFlying = !player.isFlying;
        this.addMessage(`Vuelo: ${player.isFlying ? 'ACTIVADO' : 'DESACTIVADO'}`, '#0f0');
    }

    toggleGod() {
        this.config.god = !this.config.god;
        const player = this.game[`player${this.game.activePlayer}`];
        if (this.config.god) {
            player.health = player.maxHealth;
        }
        this.addMessage(`Modo Dios: ${this.config.god ? 'ACTIVADO' : 'DESACTIVADO'}`, '#0f0');
    }

    setSpeed(speed) {
        const val = parseFloat(speed);
        if (isNaN(val) || val < 0.1 || val > 10) {
            this.addMessage('Velocidad inválida (0.1 - 10)', '#f44');
            return;
        }
        const player = this.game[`player${this.game.activePlayer}`];
        player.moveSpeed = val;
        this.addMessage(`Velocidad: ${val}`, '#0f0');
    }

    spawnMonster(args) {
        const type = (args[0] || 'ZOMBIE').toUpperCase();
        if (!ENEMY_TYPES[type]) {
            this.addMessage(`Tipo desconocido: ${type}. Usa: ZOMBIE, SKELETON, CREEPER`, '#f44');
            return;
        }

        const player = this.game[`player${this.game.activePlayer}`];
        const angle = Math.random() * Math.PI * 2;
        const dist = 5 + Math.random() * 5;
        const x = player.position.x + Math.cos(angle) * dist;
        const z = player.position.z + Math.sin(angle) * dist;
        const y = this.game.world.getSpawnHeight(Math.floor(x), Math.floor(z));

        const enemy = new Enemy(type, new THREE.Vector3(x, y, z), this.game.world);
        this.game.enemyManager.enemies.push(enemy);
        this.game.scene.add(enemy.mesh);
        this.addMessage(`${type} generado cerca`, '#f44');
    }

    killAllMonsters() {
        const count = this.game.enemyManager.enemies.length;
        this.game.enemyManager.enemies.forEach(e => {
            this.game.scene.remove(e.mesh);
        });
        this.game.enemyManager.enemies = [];
        this.addMessage(`${count} monstruos eliminados`, '#f44');
    }

    heal() {
        const player = this.game[`player${this.game.activePlayer}`];
        player.health = player.maxHealth;
        this.addMessage(`Salud restaurada: ${player.health}/${player.maxHealth}`, '#0f0');
    }

    clearConsole() {
        this.messages.innerHTML = '';
        this.addMessage('Consola limpiada', '#888');
    }

    showPosition() {
        const player = this.game[`player${this.game.activePlayer}`];
        const p = player.position;
        this.addMessage(`Posición: (${p.x.toFixed(1)}, ${p.y.toFixed(1)}, ${p.z.toFixed(1)})`, '#ff0');
    }

    showConfig() {
        this.addMessage('--- CONFIGURACIÓN ---', '#88f');
        this.addMessage(`Monstruos: ${this.config.monsters ? 'ON' : 'OFF'}`, '#ff0');
        this.addMessage(`Modo Dios: ${this.config.god ? 'ON' : 'OFF'}`, '#ff0');
        this.addMessage(`Jugador activo: ${this.game.activePlayer}`, '#ff0');
    }

    // Método para que el MCP pueda ejecutar comandos
    executeRemoteCommand(command) {
        this.addMessage(`[MCP] ${command}`, '#f0f');
        this.executeCommand(command);
    }
}

window.GameConsole = GameConsole;
