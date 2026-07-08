class Game {
    constructor() {
        this.scene = new THREE.Scene();
        this.clock = new THREE.Clock();

        // Single renderer for split screen
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        document.getElementById('viewport-p1').appendChild(this.renderer.domElement);

        // Cameras
        this.camera1 = new THREE.PerspectiveCamera(75, window.innerWidth / (2 * window.innerHeight), 0.1, 1000);
        this.camera2 = new THREE.PerspectiveCamera(75, window.innerWidth / (2 * window.innerHeight), 0.1, 1000);

        // Gamepad handler
        this.gamepadHandler = new GamepadHandler();

        // World
        this.world = new World(this.scene);

        // Physics system for block collapse
        this.physics = new PhysicsSystem(this.world, this.scene);

        // Players
        this.player1 = new Player(1, this.world, this.camera1, this.gamepadHandler, this.physics);
        this.player2 = new Player(2, this.world, this.camera2, this.gamepadHandler, this.physics);

        // Player models (visible characters)
        this.playerModel1 = new PlayerModel(1, this.scene);
        this.playerModel2 = new PlayerModel(2, this.scene);

        // Day/Night cycle
        this.dayNight = new DayNightCycle(this.scene);

        // Enemy manager
        this.enemyManager = new EnemyManager(this.world);

        // UI
        this.ui = new UIManager();

        // Game state
        this.running = false;
        this.menuOpen = true;
        this.activePlayer = 1;
        this.gameMode = 'solo'; // 'solo' or 'coop'

        // Block highlight
        this.blockHighlight = this.createBlockHighlight();
        this.scene.add(this.blockHighlight);

        // Check menu overlay
        const menuOverlay = document.getElementById('menu-overlay');
        console.log('Menu overlay found:', !!menuOverlay);

        this.setupEventListeners();
        this.setupMenu();
    }

    createBlockHighlight() {
        const geometry = new THREE.BoxGeometry(1.01, 1.01, 1.01);
        const edges = new THREE.EdgesGeometry(geometry);
        const material = new THREE.LineBasicMaterial({ color: 0x000000, linewidth: 2 });
        const highlight = new THREE.LineSegments(edges, material);
        highlight.visible = false;
        return highlight;
    }

    setupMenu() {
        const menuOverlay = document.getElementById('menu-overlay');
        const soloBtn = document.getElementById('btn-solo');
        const coopBtn = document.getElementById('btn-coop');
        const controlsBtn = document.getElementById('btn-controls');

        soloBtn.addEventListener('click', () => {
            this.gameMode = 'solo';
            menuOverlay.style.display = 'none';
            this.start();
        });

        coopBtn.addEventListener('click', () => {
            this.gameMode = 'coop';
            menuOverlay.style.display = 'none';
            this.start();
        });

        controlsBtn.addEventListener('click', () => {
            alert(`
CONTROLES TECLADO:

Jugador 1 (Izquierda):
- WASD: Mover
- Ratón: Mirar
- Click Izq: Romper bloque
- Click Der: Colocar bloque
- ESPACIO: Saltar
- ESPACIO+SHIFT: Modo vuelo
- 1-9: Seleccionar slot
- E: Inventario

Jugador 2 (Derecha):
- Flechas: Mover
- Click Izq: Romper bloque
- Click Der: Colocar bloque
- ENTER: Saltar
- ENTER+RSHIFT: Modo vuelo
- 0-9: Seleccionar slot

GAMEPAD (Xbox 360):
- Stick Izq: Mover
- Stick Der: Mirar
- RT: Romper bloque
- LT: Colocar bloque
- A: Saltar
- LS (press): Modo vuelo
- D-Pad: Seleccionar slot
            `);
        });
    }

    setupEventListeners() {
        window.addEventListener('resize', () => {
            const width = window.innerWidth;
            const height = window.innerHeight;

            if (this.gameMode === 'coop') {
                this.camera1.aspect = width / (2 * height);
                this.camera2.aspect = width / (2 * height);
            } else {
                this.camera1.aspect = width / height;
            }
            this.camera1.updateProjectionMatrix();
            this.camera2.updateProjectionMatrix();

            this.renderer.setSize(width, height);
        });

        // Mouse click for pointer lock and player switching
        document.addEventListener('click', (e) => {
            if (!this.running) return;

            if (this.gameMode === 'coop') {
                const clickX = e.clientX;
                this.activePlayer = clickX < window.innerWidth / 2 ? 1 : 2;
            } else {
                this.activePlayer = 1;
            }

            this.renderer.domElement.requestPointerLock();
        });

        // Mouse movement for active player
        document.addEventListener('mousemove', (e) => {
            if (!this.running || !document.pointerLockElement) return;

            const player = this.activePlayer === 1 ? this.player1 : this.player2;
            player.mouseDelta.x += e.movementX;
            player.mouseDelta.y += e.movementY;
        });

        // Mouse buttons for block interaction
        document.addEventListener('mousedown', (e) => {
            if (!this.running || !document.pointerLockElement) return;

            const player = this.activePlayer === 1 ? this.player1 : this.player2;

            if (e.button === 0) {
                player.breakBlock();
            } else if (e.button === 2) {
                player.placeBlock();
            }
        });

        document.addEventListener('contextmenu', (e) => e.preventDefault());

        // Keyboard controls
        document.addEventListener('keydown', (e) => {
            // Allow starting game with Enter or Space (defaults to solo)
            if (!this.running && (e.code === 'Enter' || e.code === 'Space')) {
                const menuOverlay = document.getElementById('menu-overlay');
                if (menuOverlay) {
                    menuOverlay.style.display = 'none';
                    this.gameMode = 'solo';
                    this.start();
                }
                return;
            }

            if (!this.running) return;

            if (e.code === 'KeyE') {
                this.ui.toggleInventory(1);
            }

            if (e.code === 'KeyP' && this.gameMode === 'coop') {
                this.ui.toggleInventory(2);
            }
        });
    }

    start() {
        this.running = true;
        this.menuOpen = false;

        // Spawn players
        this.player1.spawn(8, 8);

        if (this.gameMode === 'coop') {
            this.player2.spawn(10, 8);
            document.getElementById('viewport-p2').style.display = 'block';
        } else {
            // Solo mode - hide player 2 viewport
            document.getElementById('viewport-p2').style.display = 'none';
        }

        // Initialize UI
        this.ui.initialize(this.player1, this.player2);

        // Generate initial chunks
        this.world.update(this.player1.position.x, this.player1.position.z);

        // Start game loop
        this.animate();
    }

    updateBlockHighlight() {
        const player = this.activePlayer === 1 ? this.player1 : this.player2;
        const eyePos = player.getEyePosition();
        const dir = player.getForwardDirection();
        const hit = this.world.raycast(eyePos, dir);

        if (hit) {
            this.blockHighlight.position.set(
                hit.position.x + 0.5,
                hit.position.y + 0.5,
                hit.position.z + 0.5
            );
            this.blockHighlight.visible = true;
        } else {
            this.blockHighlight.visible = false;
        }
    }

    animate() {
        if (!this.running) return;

        requestAnimationFrame(() => this.animate());

        const deltaTime = Math.min(this.clock.getDelta(), 0.1);

        // Update gamepad
        this.gamepadHandler.update();

        // Update players
        this.player1.update(deltaTime);
        if (this.gameMode === 'coop') {
            this.player2.update(deltaTime);
        }

        // Update player models
        this.playerModel1.update(
            this.player1.position,
            this.player1.rotation,
            deltaTime,
            this.player1.isMoving
        );
        if (this.gameMode === 'coop') {
            this.playerModel2.update(
                this.player2.position,
                this.player2.rotation,
                deltaTime,
                this.player2.isMoving
            );
        }

        // Hide own player model (can't see yourself)
        this.playerModel1.setVisible(false);
        if (this.gameMode === 'coop') {
            this.playerModel2.setVisible(false);
        }

        // Update world
        this.world.update(this.player1.position.x, this.player1.position.z);

        // Update day/night cycle
        this.dayNight.update(deltaTime);

        // Update enemies
        this.enemyManager.update(deltaTime, [this.player1, this.player2], this.scene, this.dayNight.isNight());

        // Update physics (falling blocks)
        this.physics.update(deltaTime);

        // Update block highlight
        this.updateBlockHighlight();

        // Update UI
        this.ui.updateHealth(1, this.player1.health);
        this.ui.updateHealth(2, this.player2.health);
        this.ui.updateHotbar('hotbar-p1', this.player1);
        this.ui.updateHotbar('hotbar-p2', this.player2);

        // Debug info
        const gamepad1Status = this.gamepadHandler.isConnected(0) ? '🎮 Conectado' : '⌨️ Teclado';
        const gamepad2Status = this.gamepadHandler.isConnected(1) ? '🎮 Conectado' : '⌨️ Teclado';

        const debugInfo1 = `
            FPS: ${Math.round(1 / deltaTime)}
            Pos: ${this.player1.position.x.toFixed(1)}, ${this.player1.position.y.toFixed(1)}, ${this.player1.position.z.toFixed(1)}
            Bloque: ${BLOCK_NAMES[this.player1.inventory.getSelectedBlock()] || 'Ninguno'}
            Hora: ${this.dayNight.getTimeString()}
            ${gamepad1Status}
        `;

        const debugInfo2 = `
            FPS: ${Math.round(1 / deltaTime)}
            Pos: ${this.player2.position.x.toFixed(1)}, ${this.player2.position.y.toFixed(1)}, ${this.player2.position.z.toFixed(1)}
            Bloque: ${BLOCK_NAMES[this.player2.inventory.getSelectedBlock()] || 'Ninguno'}
            Hora: ${this.dayNight.getTimeString()}
            ${gamepad2Status}
        `;

        this.ui.updateDebugInfo(1, debugInfo1);
        if (this.gameMode === 'coop') {
            this.ui.updateDebugInfo(2, debugInfo2);
        }

        // Render based on game mode
        const width = window.innerWidth;
        const height = window.innerHeight;

        if (this.gameMode === 'coop') {
            // Split screen
            const halfWidth = width / 2;
            this.renderer.setScissorTest(true);

            this.renderer.setViewport(0, 0, halfWidth, height);
            this.renderer.setScissor(0, 0, halfWidth, height);
            this.renderer.render(this.scene, this.camera1);

            this.renderer.setViewport(halfWidth, 0, halfWidth, height);
            this.renderer.setScissor(halfWidth, 0, halfWidth, height);
            this.renderer.render(this.scene, this.camera2);

            this.renderer.setScissorTest(false);
        } else {
            // Solo - full screen
            this.renderer.setViewport(0, 0, width, height);
            this.renderer.setScissor(0, 0, width, height);
            this.renderer.render(this.scene, this.camera1);
        }
    }
}

window.addEventListener('load', () => {
    console.log('Page loaded, creating Game...');
    try {
        const game = new Game();
        console.log('Game created successfully');
    } catch(e) {
        console.error('Error creating Game:', e);
        document.body.innerHTML = '<pre style="color:red;padding:20px;">ERROR: ' + e.message + '\n' + e.stack + '</pre>';
    }
});
