/**
 * Cliente mínimo de VoxelQuest conectado al servidor Python.
 */

const WS_URL = `ws://${window.location.hostname || 'localhost'}:9002/ws`;

class ClientGame {
    constructor() {
        this.client = new GameClient();
        this.input = new InputHandler(this.client);

        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x87CEEB);
        this.clock = new THREE.Clock();

        this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.shadowMap.enabled = true;
        document.body.appendChild(this.renderer.domElement);

        this.worldMesh = new WorldMesh(this.scene);
        this.playerMesh = null;
        this.targetPlayerState = null;

        this.setupLights();
        this.setupEventListeners();

        this.client.onWelcome = (data) => this.onWelcome(data);
        this.client.onState = (state) => this.onState(state);
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
            this.camera.aspect = window.innerWidth / window.innerHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(window.innerWidth, window.innerHeight);
        });
    }

    onWelcome(data) {
        document.getElementById('loading').style.display = 'none';
        console.log('[Client] Welcome:', data);
    }

    onState(state) {
        this.worldMesh.updateFromState(state);

        const pid = String(this.client.playerId);
        const p = state.players[pid];
        if (p) {
            this.targetPlayerState = p;
            document.getElementById('pos').textContent =
                `Pos: ${p.x.toFixed(1)}, ${p.y.toFixed(1)}, ${p.z.toFixed(1)}`;
        }
    }

    updateCamera() {
        if (!this.targetPlayerState) return;

        // Interpolación simple hacia la posición objetivo
        const target = this.targetPlayerState;
        const t = 0.3;
        this.camera.position.x += (target.x - this.camera.position.x) * t;
        this.camera.position.y += ((target.y + 1.6) - this.camera.position.y) * t;
        this.camera.position.z += (target.z - this.camera.position.z) * t;

        const ry = target.ry || 0;
        const rx = target.rx || 0;
        const dir = new THREE.Vector3(
            -Math.sin(ry) * Math.cos(rx),
            -Math.sin(rx),
            -Math.cos(ry) * Math.cos(rx)
        );
        this.camera.lookAt(
            this.camera.position.x + dir.x,
            this.camera.position.y + dir.y,
            this.camera.position.z + dir.z
        );
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        if (this.client.connected) {
            const input = this.input.buildInput();
            this.client.sendInput(input);
        }

        this.updateCamera();
        this.renderer.render(this.scene, this.camera);

        document.getElementById('fps').textContent = `FPS: ${Math.round(1 / this.clock.getDelta())}`;
    }

    async start() {
        try {
            await this.client.connect(WS_URL);
            this.animate();
        } catch (err) {
            console.error('[Client] No se pudo conectar:', err);
            document.getElementById('loading').textContent = 'Error de conexión al servidor';
        }
    }
}

window.addEventListener('load', () => {
    const game = new ClientGame();
    game.start();
});
