// Block types
const BLOCK_TYPES = {
    AIR: 0,
    GRASS: 1,
    DIRT: 2,
    STONE: 3,
    WOOD: 4,
    LEAVES: 5,
    SAND: 6,
    WATER: 7,
    COBBLESTONE: 8,
    PLANKS: 9,
    BEDROCK: 10
};

const BLOCK_NAMES = {
    [BLOCK_TYPES.GRASS]: 'Hierba',
    [BLOCK_TYPES.DIRT]: 'Tierra',
    [BLOCK_TYPES.STONE]: 'Piedra',
    [BLOCK_TYPES.WOOD]: 'Madera',
    [BLOCK_TYPES.LEAVES]: 'Hojas',
    [BLOCK_TYPES.SAND]: 'Arena',
    [BLOCK_TYPES.WATER]: 'Agua',
    [BLOCK_TYPES.COBBLESTONE]: 'Roca',
    [BLOCK_TYPES.PLANKS]: 'Tablones',
    [BLOCK_TYPES.BEDROCK]: 'Bedrock'
};

const BLOCK_COLORS = {
    [BLOCK_TYPES.GRASS]: 0x5d8c3e,
    [BLOCK_TYPES.DIRT]: 0x8b6942,
    [BLOCK_TYPES.STONE]: 0x808080,
    [BLOCK_TYPES.WOOD]: 0x6b4423,
    [BLOCK_TYPES.LEAVES]: 0x2d5a1e,
    [BLOCK_TYPES.SAND]: 0xd4c4a0,
    [BLOCK_TYPES.WATER]: 0x1e64aa,
    [BLOCK_TYPES.COBBLESTONE]: 0x6b6b6b,
    [BLOCK_TYPES.PLANKS]: 0xbc9458,
    [BLOCK_TYPES.BEDROCK]: 0x2a2a2a
};

// Texture indices in atlas: [top, side, bottom]
const BLOCK_TEXTURES = {
    [BLOCK_TYPES.GRASS]: [0, 1, 2],
    [BLOCK_TYPES.DIRT]: [2, 2, 2],
    [BLOCK_TYPES.STONE]: [3, 3, 3],
    [BLOCK_TYPES.WOOD]: [5, 4, 5],
    [BLOCK_TYPES.LEAVES]: [6, 6, 6],
    [BLOCK_TYPES.SAND]: [7, 7, 7],
    [BLOCK_TYPES.WATER]: [8, 8, 8],
    [BLOCK_TYPES.COBBLESTONE]: [9, 9, 9],
    [BLOCK_TYPES.PLANKS]: [10, 10, 10],
    [BLOCK_TYPES.BEDROCK]: [11, 11, 11]
};

const CHUNK_SIZE = 16;
const WORLD_HEIGHT = 64;
const SEA_LEVEL = 20;
const TEX_SIZE = 16;
const ATLAS_COLS = 16;

class TextureAtlas {
    constructor() {
        this.canvas = null;
        this.texture = null;
    }

    generate() {
        this.canvas = document.createElement('canvas');
        this.canvas.width = TEX_SIZE * ATLAS_COLS;
        this.canvas.height = TEX_SIZE;
        const ctx = this.canvas.getContext('2d');

        this.grassTop(ctx, 0);
        this.grassSide(ctx, 1);
        this.dirt(ctx, 2);
        this.stone(ctx, 3);
        this.woodSide(ctx, 4);
        this.woodTop(ctx, 5);
        this.leaves(ctx, 6);
        this.sand(ctx, 7);
        this.water(ctx, 8);
        this.cobblestone(ctx, 9);
        this.planks(ctx, 10);
        this.bedrock(ctx, 11);

        this.texture = new THREE.CanvasTexture(this.canvas);
        this.texture.magFilter = THREE.NearestFilter;
        this.texture.minFilter = THREE.NearestFilter;
        this.texture.wrapS = THREE.ClampToEdgeWrapping;
        this.texture.wrapT = THREE.ClampToEdgeWrapping;
        this.texture.needsUpdate = true;
        return this.texture;
    }

    noise(x, y) {
        const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
        return n - Math.floor(n);
    }

    fillTex(ctx, col, baseColor) {
        const x0 = col * TEX_SIZE;
        ctx.fillStyle = baseColor;
        ctx.fillRect(x0, 0, TEX_SIZE, TEX_SIZE);
        return x0;
    }

    grassTop(ctx, col) {
        const x0 = this.fillTex(ctx, col, '#5d8c3e');
        for (let x = 0; x < TEX_SIZE; x++)
            for (let y = 0; y < TEX_SIZE; y++) {
                const n = this.noise(x, y);
                if (n > 0.55) {
                    ctx.fillStyle = `rgb(${60 + n * 40}, ${120 + n * 40}, ${40 + n * 30})`;
                    ctx.fillRect(x0 + x, y, 1, 1);
                }
            }
    }

    grassSide(ctx, col) {
        const x0 = this.fillTex(ctx, col, '#8b6942');
        for (let x = 0; x < TEX_SIZE; x++)
            for (let y = 0; y < TEX_SIZE; y++) {
                const n = this.noise(x + 100, y + 100);
                if (n > 0.6) {
                    ctx.fillStyle = `rgb(${110 + n * 40}, ${85 + n * 30}, ${50 + n * 20})`;
                    ctx.fillRect(x0 + x, y, 1, 1);
                }
            }
        for (let x = 0; x < TEX_SIZE; x++) {
            const h = 3 + Math.floor(this.noise(x, 50) * 2);
            for (let y = 0; y < h; y++) {
                ctx.fillStyle = y < h - 1 ? `rgb(${75 + this.noise(x, y) * 30}, ${135 + this.noise(x, y) * 20}, ${45})` : '#5d8c3e';
                ctx.fillRect(x0 + x, y, 1, 1);
            }
        }
    }

    dirt(ctx, col) {
        const x0 = this.fillTex(ctx, col, '#8b6942');
        for (let x = 0; x < TEX_SIZE; x++)
            for (let y = 0; y < TEX_SIZE; y++) {
                const n = this.noise(x + 200, y + 200);
                if (n > 0.6) {
                    ctx.fillStyle = `rgb(${125 + n * 30}, ${95 + n * 25}, ${55 + n * 20})`;
                    ctx.fillRect(x0 + x, y, 1, 1);
                } else if (n < 0.25) {
                    ctx.fillStyle = `rgb(${100 + n * 20}, ${75 + n * 20}, ${40 + n * 15})`;
                    ctx.fillRect(x0 + x, y, 1, 1);
                }
            }
    }

    stone(ctx, col) {
        const x0 = this.fillTex(ctx, col, '#808080');
        for (let x = 0; x < TEX_SIZE; x++)
            for (let y = 0; y < TEX_SIZE; y++) {
                const n = this.noise(x + 300, y + 300);
                const v = 105 + n * 50;
                ctx.fillStyle = `rgb(${v}, ${v}, ${v})`;
                ctx.fillRect(x0 + x, y, 1, 1);
            }
        ctx.strokeStyle = '#606060';
        ctx.lineWidth = 1;
        for (let i = 0; i < 3; i++) {
            ctx.beginPath();
            ctx.moveTo(x0 + this.noise(i, 400) * 12 + 2, this.noise(400, i) * 12 + 2);
            ctx.lineTo(x0 + this.noise(i, 400) * 12 + 5, this.noise(400, i) * 12 + 3);
            ctx.stroke();
        }
    }

    woodSide(ctx, col) {
        const x0 = this.fillTex(ctx, col, '#6b4423');
        for (let x = 0; x < TEX_SIZE; x++)
            for (let y = 0; y < TEX_SIZE; y++) {
                const grain = Math.sin(y * 2.5 + this.noise(x, y) * 2) * 8;
                ctx.fillStyle = `rgb(${85 + grain}, ${52 + grain * 0.6}, ${28 + grain * 0.3})`;
                ctx.fillRect(x0 + x, y, 1, 1);
            }
        ctx.fillStyle = '#5a3a1a';
        for (let y = 0; y < TEX_SIZE; y += 3) ctx.fillRect(x0, y, TEX_SIZE, 1);
    }

    woodTop(ctx, col) {
        const x0 = this.fillTex(ctx, col, '#6b5a3a');
        const cx = TEX_SIZE / 2, cy = TEX_SIZE / 2;
        for (let x = 0; x < TEX_SIZE; x++)
            for (let y = 0; y < TEX_SIZE; y++) {
                const dist = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2);
                const ring = Math.sin(dist * 1.5) * 10;
                ctx.fillStyle = `rgb(${95 + ring}, ${68 + ring * 0.7}, ${38 + ring * 0.4})`;
                ctx.fillRect(x0 + x, y, 1, 1);
            }
    }

    leaves(ctx, col) {
        const x0 = this.fillTex(ctx, col, '#2d5a1e');
        for (let x = 0; x < TEX_SIZE; x++)
            for (let y = 0; y < TEX_SIZE; y++) {
                const n = this.noise(x + 500, y + 500);
                if (n > 0.35) {
                    ctx.fillStyle = `rgb(${18 + n * 45}, ${75 + n * 65}, ${12 + n * 25})`;
                    ctx.fillRect(x0 + x, y, 1, 1);
                }
            }
    }

    sand(ctx, col) {
        const x0 = this.fillTex(ctx, col, '#d4c4a0');
        for (let x = 0; x < TEX_SIZE; x++)
            for (let y = 0; y < TEX_SIZE; y++) {
                const n = this.noise(x + 600, y + 600);
                ctx.fillStyle = `rgb(${195 + n * 35}, ${175 + n * 35}, ${135 + n * 35})`;
                ctx.fillRect(x0 + x, y, 1, 1);
            }
    }

    water(ctx, col) {
        const x0 = this.fillTex(ctx, col, '#1e64aa');
        for (let x = 0; x < TEX_SIZE; x++)
            for (let y = 0; y < TEX_SIZE; y++) {
                const n = this.noise(x + 700, y + 700);
                if (n > 0.45) {
                    ctx.fillStyle = `rgb(${35 + n * 65}, ${95 + n * 65}, ${175 + n * 45})`;
                    ctx.fillRect(x0 + x, y, 1, 1);
                }
            }
    }

    cobblestone(ctx, col) {
        const x0 = this.fillTex(ctx, col, '#6b6b6b');
        for (let x = 0; x < TEX_SIZE; x++)
            for (let y = 0; y < TEX_SIZE; y++) {
                const n = this.noise(x + 800, y + 800);
                const v = 80 + n * 60;
                ctx.fillStyle = `rgb(${v}, ${v}, ${v})`;
                ctx.fillRect(x0 + x, y, 1, 1);
            }
        ctx.strokeStyle = '#505050';
        ctx.lineWidth = 1;
        for (let i = 0; i < 5; i++) {
            ctx.strokeRect(x0 + this.noise(i, 900) * 12 + 2, this.noise(900, i) * 12 + 2, 4, 3);
        }
    }

    planks(ctx, col) {
        const x0 = this.fillTex(ctx, col, '#bc9458');
        ctx.fillStyle = '#a07840';
        for (let y = 0; y < TEX_SIZE; y += 4) ctx.fillRect(x0, y, TEX_SIZE, 1);
        for (let x = 0; x < TEX_SIZE; x++)
            for (let y = 0; y < TEX_SIZE; y++) {
                const n = this.noise(x + 1000, y + 1000);
                if (n > 0.65) {
                    ctx.fillStyle = `rgb(${165 + n * 35}, ${125 + n * 25}, ${65 + n * 25})`;
                    ctx.fillRect(x0 + x, y, 1, 1);
                }
            }
    }

    bedrock(ctx, col) {
        const x0 = this.fillTex(ctx, col, '#2a2a2a');
        for (let x = 0; x < TEX_SIZE; x++)
            for (let y = 0; y < TEX_SIZE; y++) {
                const n = this.noise(x + 1100, y + 1100);
                const v = 28 + n * 44;
                ctx.fillStyle = `rgb(${v}, ${v}, ${v})`;
                ctx.fillRect(x0 + x, y, 1, 1);
            }
    }

    getUV(index) {
        const u0 = index / ATLAS_COLS;
        const u1 = (index + 1) / ATLAS_COLS;
        return { u0, v0: 0, u1, v1: 1 };
    }
}

class Chunk {
    constructor(x, z, world) {
        this.x = x;
        this.z = z;
        this.world = world;
        this.blocks = new Uint8Array(CHUNK_SIZE * WORLD_HEIGHT * CHUNK_SIZE);
        this.mesh = null;
        this.dirty = true;
    }

    getBlock(x, y, z) {
        if (x < 0 || x >= CHUNK_SIZE || y < 0 || y >= WORLD_HEIGHT || z < 0 || z >= CHUNK_SIZE) return BLOCK_TYPES.AIR;
        return this.blocks[x + z * CHUNK_SIZE + y * CHUNK_SIZE * CHUNK_SIZE];
    }

    setBlock(x, y, z, type) {
        if (x < 0 || x >= CHUNK_SIZE || y < 0 || y >= WORLD_HEIGHT || z < 0 || z >= CHUNK_SIZE) return;
        this.blocks[x + z * CHUNK_SIZE + y * CHUNK_SIZE * CHUNK_SIZE] = type;
        this.dirty = true;
    }

    generateTerrain(noise) {
        for (let x = 0; x < CHUNK_SIZE; x++) {
            for (let z = 0; z < CHUNK_SIZE; z++) {
                const worldX = this.x * CHUNK_SIZE + x;
                const worldZ = this.z * CHUNK_SIZE + z;
                const height = Math.floor(noise.octaveNoise(worldX * 0.02, worldZ * 0.02, 4) * 15 + 25);

                for (let y = 0; y < WORLD_HEIGHT; y++) {
                    let blockType = BLOCK_TYPES.AIR;
                    if (y === 0) blockType = BLOCK_TYPES.BEDROCK;
                    else if (y < height - 4) blockType = BLOCK_TYPES.STONE;
                    else if (y < height - 1) blockType = BLOCK_TYPES.DIRT;
                    else if (y === height - 1) blockType = height > SEA_LEVEL ? BLOCK_TYPES.GRASS : BLOCK_TYPES.SAND;
                    else if (y < SEA_LEVEL) blockType = BLOCK_TYPES.WATER;
                    this.setBlock(x, y, z, blockType);
                }

                if (height > SEA_LEVEL + 2 && Math.random() < 0.02) this.generateTree(x, height - 1, z);
            }
        }
    }

    generateTree(x, y, z) {
        const h = 4 + Math.floor(Math.random() * 3);
        for (let i = 0; i < h; i++) this.setBlock(x, y + i, z, BLOCK_TYPES.WOOD);
        for (let dx = -2; dx <= 2; dx++)
            for (let dz = -2; dz <= 2; dz++)
                for (let dy = -1; dy <= 1; dy++) {
                    if (Math.abs(dx) + Math.abs(dz) + Math.abs(dy) < 4) {
                        const lx = x + dx, ly = y + h + dy, lz = z + dz;
                        if (lx >= 0 && lx < CHUNK_SIZE && lz >= 0 && lz < CHUNK_SIZE) this.setBlock(lx, ly, lz, BLOCK_TYPES.LEAVES);
                    }
                }
    }

    buildMesh(scene, atlas) {
        if (this.mesh) {
            scene.remove(this.mesh);
            this.mesh.geometry.dispose();
            this.mesh.material.dispose();
            this.mesh = null;
        }

        const pos = [], uv = [], idx = [];

        for (let x = 0; x < CHUNK_SIZE; x++) {
            for (let y = 0; y < WORLD_HEIGHT; y++) {
                for (let z = 0; z < CHUNK_SIZE; z++) {
                    const block = this.getBlock(x, y, z);
                    if (block === BLOCK_TYPES.AIR || block === BLOCK_TYPES.WATER) continue;
                    const wx = this.x * CHUNK_SIZE + x;
                    const wz = this.z * CHUNK_SIZE + z;
                    const tex = BLOCK_TEXTURES[block];

                    if (this.shouldDraw(x, y, z, 0, 1, 0)) this.face(pos, uv, idx, wx, y, wz, atlas.getUV(tex[0]), 'top');
                    if (this.shouldDraw(x, y, z, 0, -1, 0)) this.face(pos, uv, idx, wx, y, wz, atlas.getUV(tex[2]), 'bottom');
                    if (this.shouldDraw(x, y, z, 1, 0, 0)) this.face(pos, uv, idx, wx, y, wz, atlas.getUV(tex[1]), 'x+');
                    if (this.shouldDraw(x, y, z, -1, 0, 0)) this.face(pos, uv, idx, wx, y, wz, atlas.getUV(tex[1]), 'x-');
                    if (this.shouldDraw(x, y, z, 0, 0, 1)) this.face(pos, uv, idx, wx, y, wz, atlas.getUV(tex[1]), 'z+');
                    if (this.shouldDraw(x, y, z, 0, 0, -1)) this.face(pos, uv, idx, wx, y, wz, atlas.getUV(tex[1]), 'z-');
                }
            }
        }

        if (pos.length === 0) return;

        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
        geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
        geo.setIndex(idx);
        geo.computeVertexNormals();

        const mat = new THREE.MeshStandardMaterial({ map: atlas.texture, roughness: 0.9, metalness: 0.0, side: THREE.DoubleSide });
        this.mesh = new THREE.Mesh(geo, mat);
        this.mesh.castShadow = true;
        this.mesh.receiveShadow = true;
        scene.add(this.mesh);
        this.dirty = false;
    }

    shouldDraw(x, y, z, dx, dy, dz) {
        const ny = y + dy;
        if (ny < 0 || ny >= WORLD_HEIGHT) return true;
        const nx = x + dx, nz = z + dz;
        if (nx < 0 || nx >= CHUNK_SIZE || nz < 0 || nz >= CHUNK_SIZE) {
            return this.world.getBlock(this.x * CHUNK_SIZE + nx, ny, this.z * CHUNK_SIZE + nz) === BLOCK_TYPES.AIR;
        }
        return this.getBlock(nx, ny, nz) === BLOCK_TYPES.AIR;
    }

    face(pos, uv, idx, x, y, z, t, dir) {
        const i = pos.length / 3;
        const { u0, v0, u1, v1 } = t;

        switch (dir) {
            case 'top': // y+1, normal faces up
                pos.push(x, y+1, z, x+1, y+1, z, x+1, y+1, z+1, x, y+1, z+1);
                uv.push(u0,v0, u1,v0, u1,v1, u0,v1);
                break;
            case 'bottom': // y-1, normal faces down
                pos.push(x, y, z+1, x+1, y, z+1, x+1, y, z, x, y, z);
                uv.push(u0,v0, u1,v0, u1,v1, u0,v1);
                break;
            case 'x+': // x+1, normal faces +x
                pos.push(x+1, y, z, x+1, y+1, z, x+1, y+1, z+1, x+1, y, z+1);
                uv.push(u0,v0, u0,v1, u1,v1, u1,v0);
                break;
            case 'x-': // x-1, normal faces -x
                pos.push(x, y, z+1, x, y+1, z+1, x, y+1, z, x, y, z);
                uv.push(u0,v0, u0,v1, u1,v1, u1,v0);
                break;
            case 'z+': // z+1, normal faces +z
                pos.push(x+1, y, z+1, x+1, y+1, z+1, x, y+1, z+1, x, y, z+1);
                uv.push(u0,v0, u0,v1, u1,v1, u1,v0);
                break;
            case 'z-': // z-1, normal faces -z
                pos.push(x, y, z, x, y+1, z, x+1, y+1, z, x+1, y, z);
                uv.push(u0,v0, u0,v1, u1,v1, u1,v0);
                break;
        }
        idx.push(i, i+1, i+2, i, i+2, i+3);
    }
}

class World {
    constructor(scene, seed = 12345) {
        this.scene = scene;
        this.chunks = new Map();
        this.noise = new PerlinNoise(seed);
        this.renderDistance = 4;
        this.atlas = new TextureAtlas();
        this.atlas.generate();
    }

    getChunkKey(x, z) { return `${x},${z}`; }
    getChunk(x, z) { return this.chunks.get(this.getChunkKey(x, z)); }

    getBlock(wx, wy, wz) {
        const chunk = this.getChunk(Math.floor(wx / CHUNK_SIZE), Math.floor(wz / CHUNK_SIZE));
        if (!chunk) return BLOCK_TYPES.AIR;
        return chunk.getBlock(((wx % CHUNK_SIZE) + CHUNK_SIZE) % CHUNK_SIZE, wy, ((wz % CHUNK_SIZE) + CHUNK_SIZE) % CHUNK_SIZE);
    }

    setBlock(wx, wy, wz, type) {
        const cx = Math.floor(wx / CHUNK_SIZE), cz = Math.floor(wz / CHUNK_SIZE);
        const chunk = this.getChunk(cx, cz);
        if (!chunk) return;
        const lx = ((wx % CHUNK_SIZE) + CHUNK_SIZE) % CHUNK_SIZE;
        const lz = ((wz % CHUNK_SIZE) + CHUNK_SIZE) % CHUNK_SIZE;
        chunk.setBlock(lx, wy, lz, type);
        if (lx === 0) this.dirtyChunk(cx - 1, cz);
        if (lx === CHUNK_SIZE - 1) this.dirtyChunk(cx + 1, cz);
        if (lz === 0) this.dirtyChunk(cx, cz - 1);
        if (lz === CHUNK_SIZE - 1) this.dirtyChunk(cx, cz + 1);
    }

    dirtyChunk(cx, cz) { const c = this.getChunk(cx, cz); if (c) c.dirty = true; }

    update(px, pz) {
        const pcx = Math.floor(px / CHUNK_SIZE), pcz = Math.floor(pz / CHUNK_SIZE);
        for (let dx = -this.renderDistance; dx <= this.renderDistance; dx++)
            for (let dz = -this.renderDistance; dz <= this.renderDistance; dz++) {
                const key = this.getChunkKey(pcx + dx, pcz + dz);
                if (!this.chunks.has(key)) {
                    const c = new Chunk(pcx + dx, pcz + dz, this);
                    c.generateTerrain(this.noise);
                    this.chunks.set(key, c);
                }
            }
        for (const [, c] of this.chunks) if (c.dirty) c.buildMesh(this.scene, this.atlas);
    }

    getSpawnHeight(x, z) {
        for (let y = WORLD_HEIGHT - 1; y >= 0; y--) {
            const b = this.getBlock(x, y, z);
            if (b !== BLOCK_TYPES.AIR && b !== BLOCK_TYPES.WATER) return y + 1;
        }
        return 30;
    }

    raycast(origin, direction, maxDist = 8) {
        const step = 0.1, pos = origin.clone(), dir = direction.clone().normalize().multiplyScalar(step);
        let last = null;
        for (let i = 0; i < maxDist / step; i++) {
            const bx = Math.floor(pos.x), by = Math.floor(pos.y), bz = Math.floor(pos.z);
            const block = this.getBlock(bx, by, bz);
            if (block !== BLOCK_TYPES.AIR && block !== BLOCK_TYPES.WATER) {
                return { position: { x: bx, y: by, z: bz }, normal: last ? { x: last.x - bx, y: last.y - by, z: last.z - bz } : { x: 0, y: 1, z: 0 }, block };
            }
            last = { x: bx, y: by, z: bz };
            pos.add(dir);
        }
        return null;
    }
}

window.BLOCK_TYPES = BLOCK_TYPES;
window.BLOCK_NAMES = BLOCK_NAMES;
window.BLOCK_COLORS = BLOCK_COLORS;
window.CHUNK_SIZE = CHUNK_SIZE;
window.WORLD_HEIGHT = WORLD_HEIGHT;
window.World = World;
