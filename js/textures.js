// Procedural texture generator for blocks
class TextureGenerator {
    constructor() {
        this.textureSize = 16;
        this.textures = {};
    }

    // Create a canvas texture
    createTexture(drawFunc) {
        const canvas = document.createElement('canvas');
        canvas.width = this.textureSize;
        canvas.height = this.textureSize;
        const ctx = canvas.getContext('2d');
        drawFunc(ctx, this.textureSize);
        const texture = new THREE.CanvasTexture(canvas);
        texture.magFilter = THREE.NearestFilter;
        texture.minFilter = THREE.NearestFilter;
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        return texture;
    }

    // Noise function for texture variation
    noise(x, y) {
        const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
        return n - Math.floor(n);
    }

    // Generate all block textures
    generateAll() {
        this.textures = {
            grass_top: this.createGrassTop(),
            grass_side: this.createGrassSide(),
            dirt: this.createDirt(),
            stone: this.createStone(),
            wood: this.createWood(),
            wood_top: this.createWoodTop(),
            leaves: this.createLeaves(),
            sand: this.createSand(),
            water: this.createWater(),
            cobblestone: this.createCobblestone(),
            planks: this.createPlanks(),
            bedrock: this.createBedrock()
        };
        return this.textures;
    }

    createGrassTop() {
        return this.createTexture((ctx, size) => {
            // Base green
            ctx.fillStyle = '#5d8c3e';
            ctx.fillRect(0, 0, size, size);

            // Add noise for grass variation
            for (let x = 0; x < size; x++) {
                for (let y = 0; y < size; y++) {
                    const n = this.noise(x, y);
                    if (n > 0.7) {
                        ctx.fillStyle = `rgb(${70 + n * 30}, ${130 + n * 20}, ${50 + n * 20})`;
                        ctx.fillRect(x, y, 1, 1);
                    } else if (n < 0.3) {
                        ctx.fillStyle = `rgb(${60 + n * 20}, ${110 + n * 30}, ${40 + n * 20})`;
                        ctx.fillRect(x, y, 1, 1);
                    }
                }
            }

            // Grass blade details
            ctx.strokeStyle = '#4a7a2e';
            for (let i = 0; i < 8; i++) {
                const x = Math.floor(this.noise(i, 0) * size);
                const y = Math.floor(this.noise(0, i) * size);
                ctx.beginPath();
                ctx.moveTo(x, y);
                ctx.lineTo(x, y - 2);
                ctx.stroke();
            }
        });
    }

    createGrassSide() {
        return this.createTexture((ctx, size) => {
            // Dirt base
            ctx.fillStyle = '#8b6942';
            ctx.fillRect(0, 0, size, size);

            // Add dirt variation
            for (let x = 0; x < size; x++) {
                for (let y = 0; y < size; y++) {
                    const n = this.noise(x + 100, y + 100);
                    if (n > 0.6) {
                        ctx.fillStyle = `rgb(${120 + n * 40}, ${90 + n * 30}, ${50 + n * 20})`;
                        ctx.fillRect(x, y, 1, 1);
                    }
                }
            }

            // Grass on top (3-4 pixels)
            const grassHeight = 3;
            for (let x = 0; x < size; x++) {
                const h = grassHeight + Math.floor(this.noise(x, 50) * 2);
                for (let y = 0; y < h; y++) {
                    const n = this.noise(x, y);
                    ctx.fillStyle = y < h - 1 ? `rgb(${80 + n * 30}, ${140 + n * 20}, ${50 + n * 20})` : '#5d8c3e';
                    ctx.fillRect(x, y, 1, 1);
                }
            }
        });
    }

    createDirt() {
        return this.createTexture((ctx, size) => {
            ctx.fillStyle = '#8b6942';
            ctx.fillRect(0, 0, size, size);

            for (let x = 0; x < size; x++) {
                for (let y = 0; y < size; y++) {
                    const n = this.noise(x, y);
                    if (n > 0.7) {
                        ctx.fillStyle = `rgb(${130 + n * 30}, ${100 + n * 20}, ${60 + n * 20})`;
                        ctx.fillRect(x, y, 1, 1);
                    } else if (n < 0.2) {
                        ctx.fillStyle = `rgb(${110 + n * 20}, ${80 + n * 30}, ${45 + n * 15})`;
                        ctx.fillRect(x, y, 1, 1);
                    }
                }
            }

            // Small stones
            ctx.fillStyle = '#9a8060';
            for (let i = 0; i < 5; i++) {
                const x = Math.floor(this.noise(i, 200) * (size - 2));
                const y = Math.floor(this.noise(200, i) * (size - 2));
                ctx.fillRect(x, y, 2, 1);
            }
        });
    }

    createStone() {
        return this.createTexture((ctx, size) => {
            ctx.fillStyle = '#808080';
            ctx.fillRect(0, 0, size, size);

            // Stone variation
            for (let x = 0; x < size; x++) {
                for (let y = 0; y < size; y++) {
                    const n = this.noise(x + 50, y + 50);
                    const base = 120 + n * 40 - 20;
                    ctx.fillStyle = `rgb(${base}, ${base}, ${base})`;
                    ctx.fillRect(x, y, 1, 1);
                }
            }

            // Cracks
            ctx.strokeStyle = '#606060';
            ctx.lineWidth = 1;
            for (let i = 0; i < 3; i++) {
                ctx.beginPath();
                const startX = Math.floor(this.noise(i, 300) * size);
                const startY = Math.floor(this.noise(300, i) * size);
                ctx.moveTo(startX, startY);
                ctx.lineTo(startX + 3, startY + 2);
                ctx.stroke();
            }
        });
    }

    createWood() {
        return this.createTexture((ctx, size) => {
            // Wood base
            ctx.fillStyle = '#6b4423';
            ctx.fillRect(0, 0, size, size);

            // Vertical grain
            for (let x = 0; x < size; x++) {
                for (let y = 0; y < size; y++) {
                    const grain = Math.sin(x * 2 + this.noise(x, y) * 3) * 10;
                    const r = 90 + grain;
                    const g = 55 + grain * 0.6;
                    const b = 30 + grain * 0.3;
                    ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
                    ctx.fillRect(x, y, 1, 1);
                }
            }

            // Bark texture
            ctx.fillStyle = '#5a3a1a';
            for (let y = 0; y < size; y += 3) {
                ctx.fillRect(0, y, size, 1);
            }
        });
    }

    createWoodTop() {
        return this.createTexture((ctx, size) => {
            // Wood rings
            const centerX = size / 2;
            const centerY = size / 2;

            for (let x = 0; x < size; x++) {
                for (let y = 0; y < size; y++) {
                    const dist = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2);
                    const ring = Math.sin(dist * 1.5) * 10;
                    const r = 100 + ring;
                    const g = 70 + ring * 0.7;
                    const b = 40 + ring * 0.4;
                    ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
                    ctx.fillRect(x, y, 1, 1);
                }
            }
        });
    }

    createLeaves() {
        return this.createTexture((ctx, size) => {
            ctx.fillStyle = '#2d5a1e';
            ctx.fillRect(0, 0, size, size);

            // Leaf variation
            for (let x = 0; x < size; x++) {
                for (let y = 0; y < size; y++) {
                    const n = this.noise(x + 200, y + 200);
                    if (n > 0.5) {
                        const g = 80 + n * 60;
                        ctx.fillStyle = `rgb(${20 + n * 30}, ${g}, ${15 + n * 20})`;
                        ctx.fillRect(x, y, 1, 1);
                    }
                }
            }

            // Leaf holes (transparent spots rendered darker)
            ctx.fillStyle = '#1a3d12';
            for (let i = 0; i < 8; i++) {
                const x = Math.floor(this.noise(i, 400) * size);
                const y = Math.floor(this.noise(400, i) * size);
                ctx.fillRect(x, y, 2, 2);
            }
        });
    }

    createSand() {
        return this.createTexture((ctx, size) => {
            ctx.fillStyle = '#d4c4a0';
            ctx.fillRect(0, 0, size, size);

            for (let x = 0; x < size; x++) {
                for (let y = 0; y < size; y++) {
                    const n = this.noise(x + 300, y + 300);
                    const r = 200 + n * 30;
                    const g = 180 + n * 30;
                    const b = 140 + n * 30;
                    ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
                    ctx.fillRect(x, y, 1, 1);
                }
            }
        });
    }

    createWater() {
        return this.createTexture((ctx, size) => {
            ctx.fillStyle = 'rgba(30, 100, 180, 0.7)';
            ctx.fillRect(0, 0, size, size);

            // Water ripples
            for (let x = 0; x < size; x++) {
                for (let y = 0; y < size; y++) {
                    const n = this.noise(x + 400, y + 400);
                    if (n > 0.6) {
                        ctx.fillStyle = `rgba(60, 140, 220, ${0.5 + n * 0.3})`;
                        ctx.fillRect(x, y, 1, 1);
                    }
                }
            }
        });
    }

    createCobblestone() {
        return this.createTexture((ctx, size) => {
            ctx.fillStyle = '#6b6b6b';
            ctx.fillRect(0, 0, size, size);

            // Cobble pattern
            for (let x = 0; x < size; x++) {
                for (let y = 0; y < size; y++) {
                    const n = this.noise(x + 500, y + 500);
                    const base = 90 + n * 50;
                    ctx.fillStyle = `rgb(${base}, ${base}, ${base})`;
                    ctx.fillRect(x, y, 1, 1);
                }
            }

            // Stone outlines
            ctx.strokeStyle = '#505050';
            ctx.lineWidth = 1;
            for (let i = 0; i < 6; i++) {
                const x = Math.floor(this.noise(i, 600) * (size - 4)) + 2;
                const y = Math.floor(this.noise(600, i) * (size - 4)) + 2;
                ctx.strokeRect(x, y, 4, 3);
            }
        });
    }

    createPlanks() {
        return this.createTexture((ctx, size) => {
            ctx.fillStyle = '#bc9458';
            ctx.fillRect(0, 0, size, size);

            // Plank lines
            ctx.fillStyle = '#a07840';
            for (let y = 0; y < size; y += 4) {
                ctx.fillRect(0, y, size, 1);
            }

            // Wood grain
            for (let x = 0; x < size; x++) {
                for (let y = 0; y < size; y++) {
                    const n = this.noise(x + 700, y + 700);
                    if (n > 0.7) {
                        ctx.fillStyle = `rgb(${170 + n * 30}, ${130 + n * 20}, ${70 + n * 20})`;
                        ctx.fillRect(x, y, 1, 1);
                    }
                }
            }
        });
    }

    createBedrock() {
        return this.createTexture((ctx, size) => {
            ctx.fillStyle = '#2a2a2a';
            ctx.fillRect(0, 0, size, size);

            for (let x = 0; x < size; x++) {
                for (let y = 0; y < size; y++) {
                    const n = this.noise(x + 800, y + 800);
                    const base = 30 + n * 40;
                    ctx.fillStyle = `rgb(${base}, ${base}, ${base})`;
                    ctx.fillRect(x, y, 1, 1);
                }
            }
        });
    }
}

window.TextureGenerator = TextureGenerator;
