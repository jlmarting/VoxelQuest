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

        // Camera layers: 0=world, 1=P1 model, 2=P2 model
        // Camera 1 sees: world + P2 model (+ P1 model in third person)
        // Camera 2 sees: world + P1 model (+ P2 model in third person)
        this.camera1.layers.enable(0); // world
        this.camera1.layers.enable(2); // P2 model
        this.camera2.layers.enable(0); // world
        this.camera2.layers.enable(1); // P1 model

        // Gamepad handler
        this.gamepadHandler = new GamepadHandler();

        // World
        this.world = new World(this.scene);

        // Physics system for block collapse
        this.physics = new PhysicsSystem(this.world, this.scene);

        // Sound manager
        this.sound = new SoundManager();

        // Players
        this.player1 = new Player(1, this.world, this.camera1, this.gamepadHandler, this.physics, this.sound);
        this.player2 = new Player(2, this.world, this.camera2, this.gamepadHandler, this.physics, this.sound);

        // Assign building assets to players
        this.player1.buildingAssets = this.buildingAssets;
        this.player2.buildingAssets = this.buildingAssets;

        // Player models (visible characters)
        this.playerModel1 = new PlayerModel(1, this.scene);
        this.playerModel2 = new PlayerModel(2, this.scene);
        this.avatarModels = new Map(); // id → { group, name }

        // Assign layers: P1 model on layer 1, P2 model on layer 2
        this.playerModel1.group.layers.set(1);
        this.playerModel2.group.layers.set(2);

        // Player customization configs
        this.playerConfigs = null;

        // Day/Night cycle
        this.dayNight = new DayNightCycle(this.scene);

        // Enemy manager
        this.enemyManager = new EnemyManager(this.world);

        // Building assets
        this.buildingAssets = new BuildingAssets(this.scene);

        // MCP Client for AI control
        this.gameClient = new GameClient(this);

        // In-game console
        this.gameConsole = null; // Initialized on start

        // UI
        this.ui = new UIManager();

        // Game state
        this.running = false;
        this.menuOpen = true;
        this.activePlayer = 1;
        this.gameMode = 'solo'; // 'solo', 'coop' or 'training'

        // Block highlight
        this.blockHighlight = this.createBlockHighlight();
        this.scene.add(this.blockHighlight);

        // 3D Crosshair
        this.crosshair = this.createCrosshair();

        // Check menu overlay
        const menuOverlay = document.getElementById('menu-overlay');
        console.log('Menu overlay found:', !!menuOverlay);

        this.setupEventListeners();
        this.setupMenu();
    }

    get isMultiplayer() {
        return this.gameMode !== 'solo';
    }

    createCrosshair() {
        const group = new THREE.Group();
        const mat = new THREE.LineBasicMaterial({ color: 0xffffff });

        // Horizontal line
        const hGeo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(-0.02, 0, 0),
            new THREE.Vector3(0.02, 0, 0)
        ]);
        group.add(new THREE.Line(hGeo, mat));

        // Vertical line
        const vGeo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, -0.02, 0),
            new THREE.Vector3(0, 0.02, 0)
        ]);
        group.add(new THREE.Line(vGeo, mat));

        group.renderOrder = 999;
        this.scene.add(group);
        return group;
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
            this.showCustomizer();
        });

        coopBtn.addEventListener('click', () => {
            this.gameMode = 'coop';
            this.showCustomizer();
        });

        const trainingBtn = document.getElementById('btn-training');
        trainingBtn.addEventListener('click', () => {
            this.gameMode = 'training';
            this.showCustomizer();
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

    showCustomizer() {
        const menuOverlay = document.getElementById('menu-overlay');
        menuOverlay.style.display = 'none';

        const customizer = new CharacterCustomizer((configs) => {
            this.playerConfigs = configs;
            this.start();
        });
        customizer.show();
    }

    setupEventListeners() {
        window.addEventListener('resize', () => {
            const width = window.innerWidth;
            const height = window.innerHeight;

            if (this.isMultiplayer) {
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

            if (this.isMultiplayer) {
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

            // Inventory toggle
            if (e.code === 'KeyE') {
                if (this.inventoryUI) this.inventoryUI.toggle();
            }

            if (e.code === 'KeyP' && this.isMultiplayer) {
                if (this.inventoryUI) this.inventoryUI.toggle();
            }

            // Inventory navigation when open
            if (this.inventoryUI && this.inventoryUI.isOpen) {
                if (e.code === 'ArrowUp' || e.code === 'KeyW') {
                    this.inventoryUI.moveSelection(-9); // Up one row
                } else if (e.code === 'ArrowDown' || e.code === 'KeyS') {
                    this.inventoryUI.moveSelection(9); // Down one row
                } else if (e.code === 'ArrowLeft' || e.code === 'KeyA') {
                    this.inventoryUI.moveSelection(-1); // Left
                } else if (e.code === 'ArrowRight' || e.code === 'KeyD') {
                    this.inventoryUI.moveSelection(1); // Right
                } else if (e.code === 'Enter' || e.code === 'Space') {
                    this.inventoryUI.selectCurrent();
                } else if (e.code === 'Escape') {
                    this.inventoryUI.close();
                }
            }

            // X key toggles collision boxes
            if (e.code === 'KeyX') {
                this.playerModel1.toggleCollision();
                if (this.isMultiplayer) {
                    this.playerModel2.toggleCollision();
                }
            }

            // M key toggles sound
            if (e.code === 'KeyM') {
                const enabled = this.sound.toggle();
                this.ui.showNotification(enabled ? 'Sonido: ON' : 'Sonido: OFF');
            }

            // R key toggles recording (training mode only)
            if (e.code === 'KeyR' && this.gameMode === 'training' && this.gameClient) {
                if (this._recording) {
                    const r = this.gameClient._stopRecording();
                    this._recording = false;
                    this._updateRecIndicator();
                    if (r.success) this.ui.showNotification(`✅ Episodio "${r.scenario}" (${r.frames} frames)`);
                } else {
                    const name = prompt('Nombre del escenario:');
                    if (name && name.trim()) {
                        this.gameClient._startRecording(name.trim());
                        this._recording = true;
                        this._updateRecIndicator();
                        this.ui.showNotification(`🔴 Grabando: ${name.trim()}`);
                    }
                }
            }
        });

        // Recorder indicator helper
        this._recIndicator = document.getElementById('rec-indicator');
        this._recording = false;
    }

    _updateRecIndicator() {
        const el = this._recIndicator;
        if (!el) return;
        if (this._recording && this.gameMode === 'training') {
            el.textContent = '🔴 GRABANDO';
            el.style.display = 'block';
        } else {
            el.style.display = 'none';
        }
    }

    start() {
        console.log('[Main] start() called');
        this.running = true;
        this.menuOpen = false;

        // Hide all menus
        document.getElementById('menu-overlay').style.display = 'none';

        // Initialize sound (requires user interaction)
        this.sound.init();

        // Apply customization configs if available
        if (this.playerConfigs) {
            console.log('[Main] Applying customization');
            this.playerModel1.updateConfig(this.playerConfigs[0]);
            this.playerModel2.updateConfig(this.playerConfigs[1]);
        }

        // Spawn players
        if (this.gameMode === 'training') {
            this.world.enableFlatMode(80);
            this.player1.spawn(40, 38);
            this.player2.spawn(40, 42);
            document.getElementById('viewport-p2').style.display = 'block';
        } else {
            this.player1.spawn(8, 8);
            if (this.isMultiplayer) {
                this.player2.spawn(10, 8);
                document.getElementById('viewport-p2').style.display = 'block';
            } else {
                document.getElementById('viewport-p2').style.display = 'none';
            }
        }
        console.log('[Main] Players spawned');

        // Initialize UI
        console.log('[Main] Initializing UI');
        this.ui.initialize(this.player1, this.player2);
        console.log('[Main] UI initialized');

        // Initialize Inventory UI
        this.inventoryUI = new InventoryUI(this.player1.inventory);
        window.gameUI = this;

        // Connect to game server (optional - won't block game if not running)
        this.gameClient.connect().then(() => {
            console.log('[Game] Conectado al servidor');
            this.gameClient.sendState();
        }).catch(err => {
            console.log('[Game] Servidor no disponible (opcional)');
        });

        // Initialize in-game console
        this.gameConsole = new GameConsole(this);
        window.gameConsole = this.gameConsole;

        // Generate initial chunks
        console.log('[Main] Generating chunks');
        this.world.update(this.player1.position.x, this.player1.position.z);
        console.log('[Main] Chunks generated');

        // Start game loop
        console.log('[Main] Starting animate loop');
        this.animate();
        console.log('[Main] animate() called');
    }

    closeInventory() {
        if (this.inventoryUI) this.inventoryUI.close();
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

        if (!this._animateLogged) { console.log('[Main] animate() running'); this._animateLogged = true; }
        requestAnimationFrame(() => this.animate());

        const deltaTime = Math.min(this.clock.getDelta(), 0.1);

        // Update gamepad
        this.gamepadHandler.update();

        // Update game client pathfinding
        if (this.gameClient) {
            this.gameClient.update(deltaTime);
        }

        // Update players
        this.player1.update(deltaTime);
        if (this.isMultiplayer) {
            this.player2.update(deltaTime);
        }

        // Update player models
        this.playerModel1.update(
            this.player1.position,
            this.player1.rotation,
            deltaTime,
            this.player1.isMoving
        );
        if (this.isMultiplayer) {
            this.playerModel2.update(
                this.player2.position,
                this.player2.rotation,
                deltaTime,
                this.player2.isMoving
            );
        }

        // Manage model visibility using layers
        // P1 camera sees P2 model (layer 2) always
        // P2 camera sees P1 model (layer 1) always
        // In third person, also see own model
        if (this.player1.cameraMode > 0) {
            this.camera1.layers.enable(1); // see own model
        } else {
            this.camera1.layers.disable(1); // don't see own model
        }
        if (this.isMultiplayer && this.player2.cameraMode > 0) {
            this.camera2.layers.enable(2); // see own model
        } else if (this.isMultiplayer) {
            this.camera2.layers.disable(2); // don't see own model
        }

        // Update world
        this.world.update(this.player1.position.x, this.player1.position.z);

        // Update day/night cycle
        this.dayNight.update(deltaTime);

        // Update enemies
        this.enemyManager.update(deltaTime, [this.player1, this.player2], this.scene, this.dayNight.isNight());

        // Update physics (falling blocks)
        this.physics.update(deltaTime);

        // Update building asset animations (torch flames, etc.)
        this.buildingAssets.updateAnimations(this.clock.elapsedTime);

        // Sync state with server (every frame, but throttled internally)
        if (this.gameClient && this.gameClient.connected) {
            this.gameClient.syncState();
        }

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

        const cameraModes = ['1ra Persona', '3ra Cerca', '3ra Lejos'];

        const debugInfo1 = `
            FPS: ${Math.round(1 / deltaTime)}
            Pos: ${this.player1.position.x.toFixed(1)}, ${this.player1.position.y.toFixed(1)}, ${this.player1.position.z.toFixed(1)}
            Bloque: ${this.inventoryUI?.inventory.getItemInfo(this.player1.inventory.getSelectedItem()?.type)?.name || 'Ninguno'}
            Cámara: ${cameraModes[this.player1.cameraMode]} (V)
            Hora: ${this.dayNight.getTimeString()}
        `;

        const debugInfo2 = `
            FPS: ${Math.round(1 / deltaTime)}
            Pos: ${this.player2.position.x.toFixed(1)}, ${this.player2.position.y.toFixed(1)}, ${this.player2.position.z.toFixed(1)}
            Bloque: ${this.inventoryUI?.inventory.getItemInfo(this.player2.inventory.getSelectedItem()?.type)?.name || 'Ninguno'}
            Cámara: ${cameraModes[this.player2.cameraMode]} (V)
            Hora: ${this.dayNight.getTimeString()}
        `;

        this.ui.updateDebugInfo(1, debugInfo1);
        if (this.isMultiplayer) {
            this.ui.updateDebugInfo(2, debugInfo2);
        }

        // Update crosshair position (always in front of active camera)
        const activeCamera = this.activePlayer === 1 ? this.camera1 : this.camera2;
        this.crosshair.position.copy(activeCamera.position);
        this.crosshair.quaternion.copy(activeCamera.quaternion);
        this.crosshair.translateZ(-0.5); // 0.5 units in front of camera

        // Render based on game mode
        const width = window.innerWidth;
        const height = window.innerHeight;

        if (this.isMultiplayer) {
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

        // Update avatar models
        for (const [, av] of this.avatarModels) {
            if (av.group) {
                av.group.position.set(av.x, av.y, av.z);
                av.group.rotation.y = av.ry || 0;
            }
        }
    }

    updateAvatars(avatarList) {
        const seen = new Set();
        for (const a of avatarList) {
            seen.add(a.id);
                if (!this.avatarModels.has(a.id)) {
                const cfg = {
                    gender: 'male', skinColor: 0x4488cc, hairColor: 0x224466, hairStyle: 'short',
                    eyeColor: 0x88ddff, shirtColor: 0x2266aa, pantsColor: 0x1a3355, shoeColor: 0x111122
                };
                const model = new PlayerModel(a.id, this.scene);
                model.updateConfig(cfg);
                if (a.id % 2 === 0 && model.light) model.light.intensity = 0;
                this.avatarModels.set(a.id, { group: model.group, x: a.x, y: a.y, z: a.z, ry: a.ry || 0 });
            } else {
                const av = this.avatarModels.get(a.id);
                av.x = a.x; av.y = a.y; av.z = a.z; av.ry = a.ry || 0;
            }
        }
        for (const [id, av] of this.avatarModels) {
            if (!seen.has(id)) {
                this.scene.remove(av.group);
                this.avatarModels.delete(id);
            }
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
