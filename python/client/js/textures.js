/**
 * TextureAtlas: genera un atlas de texturas procedurales (igual que la
 * versión previa root js/world.js) con ruido en la hierba, tierra, piedra, etc.
 * Se reutiliza el código probado de la versión anterior.
 */

const TEX_SIZE = 16;
const ATLAS_COLS = 16;

// Índices de textura en el atlas: [top, side, bottom] por tipo de bloque.
// Tipos 1..10 (0 = aire).
const BLOCK_TEXTURES = {
    1: [0, 1, 2],   // GRASS  (grass_top, grass_side, dirt)
    2: [2, 2, 2],   // DIRT
    3: [3, 3, 3],   // STONE
    4: [5, 4, 5],   // WOOD   (wood_top, wood_side, wood_top)
    5: [6, 6, 6],   // LEAVES
    6: [7, 7, 7],   // SAND
    7: [8, 8, 8],   // WATER
    8: [9, 9, 9],   // COBBLESTONE
    9: [10, 10, 10],// PLANKS
    10: [11, 11, 11]// BEDROCK
};

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

window.TextureAtlas = TextureAtlas;
window.BLOCK_TEXTURES = BLOCK_TEXTURES;
