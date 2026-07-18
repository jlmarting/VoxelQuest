/**
 * Renderizado de chunks, jugadores y enemigos recibidos del servidor.
 */

const BLOCK_COLORS = {
    0: null,
    1: 0x5d8c3e,  // GRASS
    2: 0x8b6942,  // DIRT
    3: 0x808080,  // STONE
    4: 0x6b4423,  // WOOD
    5: 0x2d5a1e,  // LEAVES
    6: 0xd4c4a0,  // SAND
    7: 0x1e64aa,  // WATER
    8: 0x6b6b6b,  // COBBLESTONE
    9: 0xbc9458,  // PLANKS
    10: 0x2a2a2a  // BEDROCK
};

class WorldMesh {
    constructor(scene) {
        this.scene = scene;
        this.chunks = new Map();
        this.geometry = new THREE.BoxGeometry(1, 1, 1);
        this.playerMeshes = new Map();
        this.enemyMeshes = new Map();
    }

    updateFromState(state) {
        const deltas = state.chunk_deltas || {};
        for (const [key, delta] of Object.entries(deltas)) {
            this.updateChunk(key, delta.modified || []);
        }

        const players = state.players || {};
        for (const [pid, p] of Object.entries(players)) {
            this.updatePlayer(pid, p);
        }

        const enemies = state.enemies || [];
        const seenEnemies = new Set();
        for (const e of enemies) {
            this.updateEnemy(e);
            seenEnemies.add(String(e.id));
        }
        for (const [id, mesh] of this.enemyMeshes.entries()) {
            if (!seenEnemies.has(id)) {
                this.scene.remove(mesh);
                this.enemyMeshes.delete(id);
            }
        }
    }

    updateChunk(key, blocks) {
        if (this.chunks.has(key)) {
            this.scene.remove(this.chunks.get(key));
        }
        if (blocks.length === 0) return;

        const [cxStr, czStr] = key.split(',');
        const cx = parseInt(cxStr);
        const cz = parseInt(czStr);

        const instanced = new THREE.InstancedMesh(
            this.geometry,
            new THREE.MeshStandardMaterial({ roughness: 0.9, metalness: 0 }),
            blocks.length
        );

        const dummy = new THREE.Object3D();
        let i = 0;
        for (const [x, y, z, type] of blocks) {
            dummy.position.set(cx * 16 + x + 0.5, y + 0.5, cz * 16 + z + 0.5);
            dummy.updateMatrix();
            instanced.setMatrixAt(i, dummy.matrix);
            instanced.setColorAt(i, new THREE.Color(BLOCK_COLORS[type] || 0xff00ff));
            i++;
        }
        instanced.instanceMatrix.needsUpdate = true;
        instanced.instanceColor.needsUpdate = true;
        instanced.castShadow = true;
        instanced.receiveShadow = true;

        this.scene.add(instanced);
        this.chunks.set(key, instanced);
    }

    updatePlayer(id, p) {
        if (!this.playerMeshes.has(id)) {
            const group = new THREE.Group();
            const body = new THREE.Mesh(
                new THREE.BoxGeometry(0.6, 1.8, 0.6),
                new THREE.MeshStandardMaterial({ color: id === '1' ? 0x2266cc : 0xcc4444 })
            );
            body.position.y = 0.9;
            group.add(body);
            this.scene.add(group);
            this.playerMeshes.set(id, group);
        }
        const mesh = this.playerMeshes.get(id);
        mesh.position.set(p.x, p.y, p.z);
        mesh.rotation.y = p.ry || 0;
    }

    updateEnemy(e) {
        const id = String(e.id);
        if (!this.enemyMeshes.has(id)) {
            const mesh = new THREE.Mesh(
                new THREE.BoxGeometry(0.6, e.type === 'CREEPER' ? 1.5 : 1.8, 0.6),
                new THREE.MeshStandardMaterial({ color: 0x2d5a27 })
            );
            mesh.position.y = (e.type === 'CREEPER' ? 1.5 : 1.8) / 2;
            this.scene.add(mesh);
            this.enemyMeshes.set(id, mesh);
        }
        const mesh = this.enemyMeshes.get(id);
        mesh.position.x = e.x;
        mesh.position.z = e.z;
    }

    clear() {
        for (const mesh of this.chunks.values()) {
            this.scene.remove(mesh);
        }
        this.chunks.clear();
    }
}

window.WorldMesh = WorldMesh;
