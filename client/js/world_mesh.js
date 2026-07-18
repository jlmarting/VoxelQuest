/**
 * Renderizado de chunks recibidos del servidor.
 * Construye/actualiza meshes de Three.js a partir de estado delta.
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
        this.chunks = new Map(); // key 'cx,cz' -> mesh
        this.geometry = new THREE.BoxGeometry(1, 1, 1);
    }

    updateFromState(state) {
        const deltas = state.chunk_deltas || {};
        for (const [key, delta] of Object.entries(deltas)) {
            this.updateChunk(key, delta.modified || []);
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

    clear() {
        for (const mesh of this.chunks.values()) {
            this.scene.remove(mesh);
        }
        this.chunks.clear();
    }
}

window.WorldMesh = WorldMesh;
