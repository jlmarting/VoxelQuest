/**
 * Cliente de VoxelQuest conectado al servidor Python.
 * Soporta modo solo y split-screen coop.
 */

const WS_PORT = window.location.port || 9000;
const WS_URL = `ws://${window.location.hostname || 'localhost'}:${WS_PORT}/ws`;

class ClientGame {
    constructor(mode = 'solo') {
        this.mode = mode;
        this.clients = [];
        this.inputs = [];

        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x87CEEB);
        this.clock = new THREE.Clock();

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.shadowMap.enabled = true;
        document.body.appendChild(this.renderer.domElement);

        // Cámaras: una por jugador local
        this.cameras = [
            new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000),
            new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000)
        ];

        this.worldMesh = new WorldMesh(this.scene);
        this.targetStates = [null, null];

        this.setupLights();
        this.setupEventListeners();

        // Crear clientes según modo
        if (mode === 'coop') {
            this.addLocalPlayer(1, new InputHandler(null));
            this.addLocalPlayer(2, new InputHandler(null));
            this.inputs[1].keys = {}; // placeholder: P2 usaría otro input set
            document.getElementById('mode').textContent = 'Modo: 2 Jugadores Split Screen';
        } else {
            this.addLocalPlayer(1, new InputHandler(null));
            document.getElementById('mode').textContent = 'Modo: Solitario';
        }
    }

    addLocalPlayer(playerId, inputHandler) {
        const client = new GameClient();
        client.onWelcome = (data) => this.onWelcome(data, playerId);
        client.onState = (state) => this.onState(state);
        // input handler real asociado a este jugador
        const input = new InputHandler(client);
        this.clients[playerId - 1] = client;
        this.inputs[playerId - 1] = input;
    }

    setupLights() {
        const ambient = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambient);

        const sun = new THREE.DirectionalLight(0xffffff, 0.8);
        sun.position.set(50, 100, 50);
        sun.castShadow = true;
        this.scene.add(sun);
    }

    setupEventListeners() {
        window.addEventListener('resize', () => {
            const width = window.innerWidth;
            const height = window.innerHeight;
            if (this.mode === 'coop') {
                this.cameras[0].aspect = width / (2 * height);
                this.cameras[1].aspect = width / (2 * height);
            } else {
                this.cameras[0].aspect = width / height;
            }
            this.cameras[0].updateProjectionMatrix();
            this.cameras[1].updateProjectionMatrix();
            this.renderer.setSize(width, height);
        });
    }



    onWelcome(data, playerId) {
        console.log('[Client] Welcome player', playerId, data);
        if (playerId === 1) {
            document.getElementById('loading').style.display = 'none';
        }
    }

    onState(state) {
        this.worldMesh.updateFromState(state);

        const p1 = state.players['1'];
        const p2 = state.players['2'];
        this.targetStates[0] = p1 || null;
        this.targetStates[1] = p2 || null;

        const pid = String(this.clients[0].playerId);
        const p = state.players[pid];
        if (p) {
            document.getElementById('pos').textContent =
                `Pos: ${p.x.toFixed(1)}, ${p.y.toFixed(1)}, ${p.z.toFixed(1)}`;
        }
    }

    updateCameras() {
        for (let i = 0; i < this.cameras.length; i++) {
            const target = this.targetStates[i];
            if (!target) continue;
            const cam = this.cameras[i];

            cam.position.x += (target.x - cam.position.x) * 0.3;
            cam.position.y += ((target.y + 1.6) - cam.position.y) * 0.3;
            cam.position.z += (target.z - cam.position.z) * 0.3;

            const ry = target.ry || 0;
            const rx = target.rx || 0;
            const dir = new THREE.Vector3(
                -Math.sin(ry) * Math.cos(rx),
                -Math.sin(rx),
                -Math.cos(ry) * Math.cos(rx)
            );
            cam.lookAt(cam.position.x + dir.x, cam.position.y + dir.y, cam.position.z + dir.z);
        }
    }

    render() {
        const width = window.innerWidth;
        const height = window.innerHeight;

        if (this.mode === 'coop') {
            const halfWidth = width / 2;
            this.renderer.setScissorTest(true);

            this.renderer.setViewport(0, 0, halfWidth, height);
            this.renderer.setScissor(0, 0, halfWidth, height);
            this.renderer.render(this.scene, this.cameras[0]);

            this.renderer.setViewport(halfWidth, 0, halfWidth, height);
            this.renderer.setScissor(halfWidth, 0, halfWidth, height);
            this.renderer.render(this.scene, this.cameras[1]);

            this.renderer.setScissorTest(false);
        } else {
            this.renderer.setViewport(0, 0, width, height);
            this.renderer.render(this.scene, this.cameras[0]);
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        for (let i = 0; i < this.clients.length; i++) {
            const client = this.clients[i];
            const input = this.inputs[i];
            if (client && client.connected && input) {
                client.sendInput(input.buildInput());
            }
        }

        this.updateCameras();
        this.render();

        const fps = Math.round(1 / this.clock.getDelta());
        document.getElementById('fps').textContent = `FPS: ${fps}`;
    }

    async start() {
        try {
            await Promise.all(this.clients.filter(c => c).map(c => c.connect(WS_URL)));
            this.animate();
        } catch (err) {
            console.error('[Client] No se pudo conectar:', err);
            document.getElementById('loading').textContent = 'Error de conexión al servidor';
        }
    }
}


function startGame(mode) {
    document.getElementById('menu').style.display = 'none';
    document.getElementById('loading').style.display = 'block';
    const game = new ClientGame(mode);
    game.start();
}
