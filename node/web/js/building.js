// Building assets: windows, doors, torches, furniture
class BuildingAssets {
    constructor(scene) {
        this.scene = scene;
        this.assets = {};
        this.placedAssets = [];
    }

    // Create window mesh
    createWindow(x, y, z, rotation = 0) {
        const group = new THREE.Group();

        // Frame
        const frameMat = new THREE.MeshStandardMaterial({ color: 0x5c3a1e, roughness: 0.9 });
        const frameGeo = new THREE.BoxGeometry(1.0, 1.0, 0.1);

        // Top frame
        const top = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.08, 0.1), frameMat);
        top.position.set(0, 0.46, 0);
        group.add(top);

        // Bottom frame
        const bottom = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.08, 0.1), frameMat);
        bottom.position.set(0, -0.46, 0);
        group.add(bottom);

        // Left frame
        const left = new THREE.Mesh(new THREE.BoxGeometry(0.08, 1.0, 0.1), frameMat);
        left.position.set(-0.46, 0, 0);
        group.add(left);

        // Right frame
        const right = new THREE.Mesh(new THREE.BoxGeometry(0.08, 1.0, 0.1), frameMat);
        right.position.set(0.46, 0, 0);
        group.add(right);

        // Glass
        const glassMat = new THREE.MeshStandardMaterial({
            color: 0x88ccff,
            transparent: true,
            opacity: 0.3,
            roughness: 0.1,
            metalness: 0.1
        });
        const glass = new THREE.Mesh(new THREE.BoxGeometry(0.84, 0.84, 0.02), glassMat);
        glass.position.set(0, 0, 0);
        group.add(glass);

        // Cross bar
        const crossH = new THREE.Mesh(new THREE.BoxGeometry(0.84, 0.04, 0.05), frameMat);
        crossH.position.set(0, 0, 0);
        group.add(crossH);

        const crossV = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.84, 0.05), frameMat);
        crossV.position.set(0, 0, 0);
        group.add(crossV);

        group.position.set(x + 0.5, y + 0.5, z + 0.5);
        group.rotation.y = rotation;
        group.userData.type = 'window';
        this.scene.add(group);
        this.placedAssets.push(group);
        return group;
    }

    // Create door mesh
    createDoor(x, y, z, rotation = 0, open = false) {
        const group = new THREE.Group();

        // Door frame
        const frameMat = new THREE.MeshStandardMaterial({ color: 0x4a3520, roughness: 0.9 });
        const frameLeft = new THREE.Mesh(new THREE.BoxGeometry(0.1, 2.0, 0.15), frameMat);
        frameLeft.position.set(-0.5, 1.0, 0);
        group.add(frameLeft);

        const frameRight = new THREE.Mesh(new THREE.BoxGeometry(0.1, 2.0, 0.15), frameMat);
        frameRight.position.set(0.5, 1.0, 0);
        group.add(frameRight);

        const frameTop = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.1, 0.15), frameMat);
        frameTop.position.set(0, 2.0, 0);
        group.add(frameTop);

        // Door panel
        const doorMat = new THREE.MeshStandardMaterial({ color: 0x8b5a2b, roughness: 0.8 });
        const door = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.9, 0.08), doorMat);
        door.position.set(0, 0.95, 0);
        door.userData.isDoor = true;
        group.add(door);

        // Door handle
        const handleMat = new THREE.MeshStandardMaterial({ color: 0xccaa44, metalness: 0.8, roughness: 0.2 });
        const handle = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.12, 0.04), handleMat);
        handle.position.set(0.35, 0.95, 0.06);
        group.add(handle);

        // Panels
        const panelMat = new THREE.MeshStandardMaterial({ color: 0x7a4a25, roughness: 0.85 });
        const panel1 = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.5, 0.02), panelMat);
        panel1.position.set(0, 1.4, 0.05);
        group.add(panel1);

        const panel2 = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.5, 0.02), panelMat);
        panel2.position.set(0, 0.5, 0.05);
        group.add(panel2);

        group.position.set(x + 0.5, y, z + 0.5);
        group.rotation.y = rotation;
        group.userData.type = 'door';
        group.userData.isOpen = open;
        this.scene.add(group);
        this.placedAssets.push(group);
        return group;
    }

    // Create torch
    createTorch(x, y, z) {
        const group = new THREE.Group();

        // Stick
        const stickMat = new THREE.MeshStandardMaterial({ color: 0x5c3a1e, roughness: 0.9 });
        const stick = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.3, 0.06), stickMat);
        stick.position.set(0, 0.15, 0);
        group.add(stick);

        // Flame (simple box with emissive)
        const flameMat = new THREE.MeshStandardMaterial({
            color: 0xff6600,
            emissive: 0xff4400,
            emissiveIntensity: 0.8,
            roughness: 0.3
        });
        const flame = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.15, 0.1), flameMat);
        flame.position.set(0, 0.38, 0);
        flame.userData.isFlame = true;
        group.add(flame);

        // Light
        const light = new THREE.PointLight(0xff8844, 1.0, 8, 2);
        light.position.set(0, 0.4, 0);
        group.add(light);

        group.position.set(x + 0.5, y + 0.1, z + 0.5);
        group.userData.type = 'torch';
        group.userData.light = light;
        this.scene.add(group);
        this.placedAssets.push(group);
        return group;
    }

    // Create crafting table
    createCraftingTable(x, y, z) {
        const group = new THREE.Group();

        // Table top
        const topMat = new THREE.MeshStandardMaterial({ color: 0xbc9458, roughness: 0.8 });
        const top = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.1, 1.0), topMat);
        top.position.set(0.5, 0.95, 0.5);
        group.add(top);

        // Legs
        const legMat = new THREE.MeshStandardMaterial({ color: 0x6b4423, roughness: 0.9 });
        const legGeo = new THREE.BoxGeometry(0.1, 0.9, 0.1);

        const leg1 = new THREE.Mesh(legGeo, legMat);
        leg1.position.set(0.1, 0.45, 0.1);
        group.add(leg1);

        const leg2 = new THREE.Mesh(legGeo, legMat);
        leg2.position.set(0.9, 0.45, 0.1);
        group.add(leg2);

        const leg3 = new THREE.Mesh(legGeo, legMat);
        leg3.position.set(0.1, 0.45, 0.9);
        group.add(leg3);

        const leg4 = new THREE.Mesh(legGeo, legMat);
        leg4.position.set(0.9, 0.45, 0.9);
        group.add(leg4);

        // Crafting grid pattern on top
        const gridMat = new THREE.MeshStandardMaterial({ color: 0x8b6942, roughness: 0.85 });
        for (let i = 0; i < 3; i++) {
            for (let j = 0; j < 3; j++) {
                const cell = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.01, 0.25), gridMat);
                cell.position.set(0.25 + i * 0.25, 1.01, 0.25 + j * 0.25);
                group.add(cell);
            }
        }

        group.position.set(x, y, z);
        group.userData.type = 'crafting_table';
        this.scene.add(group);
        this.placedAssets.push(group);
        return group;
    }

    // Create chest
    createChest(x, y, z) {
        const group = new THREE.Group();

        // Chest body
        const bodyMat = new THREE.MeshStandardMaterial({ color: 0x8b5a2b, roughness: 0.8 });
        const body = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.6, 0.5), bodyMat);
        body.position.set(0.5, 0.3, 0.5);
        group.add(body);

        // Lid
        const lidMat = new THREE.MeshStandardMaterial({ color: 0x7a4a25, roughness: 0.85 });
        const lid = new THREE.Mesh(new THREE.BoxGeometry(0.82, 0.15, 0.52), lidMat);
        lid.position.set(0.5, 0.65, 0.5);
        group.add(lid);

        // Metal bands
        const bandMat = new THREE.MeshStandardMaterial({ color: 0x888888, metalness: 0.8, roughness: 0.3 });
        const band1 = new THREE.Mesh(new THREE.BoxGeometry(0.82, 0.04, 0.02), bandMat);
        band1.position.set(0.5, 0.2, 0.76);
        group.add(band1);

        const band2 = new THREE.Mesh(new THREE.BoxGeometry(0.82, 0.04, 0.02), bandMat);
        band2.position.set(0.5, 0.5, 0.76);
        group.add(band2);

        // Lock
        const lockMat = new THREE.MeshStandardMaterial({ color: 0xccaa44, metalness: 0.9, roughness: 0.2 });
        const lock = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.1, 0.04), lockMat);
        lock.position.set(0.5, 0.45, 0.77);
        group.add(lock);

        group.position.set(x, y, z);
        group.userData.type = 'chest';
        this.scene.add(group);
        this.placedAssets.push(group);
        return group;
    }

    // Create bed
    createBed(x, y, z, color = 0xcc3333) {
        const group = new THREE.Group();

        // Frame
        const frameMat = new THREE.MeshStandardMaterial({ color: 0x6b4423, roughness: 0.9 });
        const frame = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.2, 2.0), frameMat);
        frame.position.set(0.5, 0.1, 1.0);
        group.add(frame);

        // Mattress
        const mattressMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.9 });
        const mattress = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.15, 1.8), mattressMat);
        mattress.position.set(0.5, 0.27, 1.0);
        group.add(mattress);

        // Blanket
        const blanketMat = new THREE.MeshStandardMaterial({ color, roughness: 0.85 });
        const blanket = new THREE.Mesh(new THREE.BoxGeometry(0.85, 0.05, 1.2), blanketMat);
        blanket.position.set(0.5, 0.37, 1.3);
        group.add(blanket);

        // Pillow
        const pillowMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.9 });
        const pillow = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.12, 0.3), pillowMat);
        pillow.position.set(0.5, 0.35, 0.3);
        group.add(pillow);

        // Headboard
        const headboard = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.6, 0.1), frameMat);
        headboard.position.set(0.5, 0.5, 0.05);
        group.add(headboard);

        group.position.set(x, y, z);
        group.userData.type = 'bed';
        this.scene.add(group);
        this.placedAssets.push(group);
        return group;
    }

    // Create chair
    createChair(x, y, z, color = 0x8b5a2b) {
        const group = new THREE.Group();

        const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.85 });

        // Seat
        const seat = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.05, 0.5), mat);
        seat.position.set(0.25, 0.45, 0.25);
        group.add(seat);

        // Back
        const back = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.5, 0.05), mat);
        back.position.set(0.25, 0.7, 0.02);
        group.add(back);

        // Legs
        const legGeo = new THREE.BoxGeometry(0.05, 0.45, 0.05);
        const leg1 = new THREE.Mesh(legGeo, mat);
        leg1.position.set(0.05, 0.22, 0.05);
        group.add(leg1);

        const leg2 = new THREE.Mesh(legGeo, mat);
        leg2.position.set(0.45, 0.22, 0.05);
        group.add(leg2);

        const leg3 = new THREE.Mesh(legGeo, mat);
        leg3.position.set(0.05, 0.22, 0.45);
        group.add(leg3);

        const leg4 = new THREE.Mesh(legGeo, mat);
        leg4.position.set(0.45, 0.22, 0.45);
        group.add(leg4);

        group.position.set(x, y, z);
        group.userData.type = 'chair';
        this.scene.add(group);
        this.placedAssets.push(group);
        return group;
    }

    // Create table
    createTable(x, y, z, color = 0x8b5a2b) {
        const group = new THREE.Group();

        const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.85 });

        // Table top
        const top = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.06, 0.6), mat);
        top.position.set(0.5, 0.75, 0.3);
        group.add(top);

        // Legs
        const legGeo = new THREE.BoxGeometry(0.06, 0.75, 0.06);
        const leg1 = new THREE.Mesh(legGeo, mat);
        leg1.position.set(0.1, 0.375, 0.1);
        group.add(leg1);

        const leg2 = new THREE.Mesh(legGeo, mat);
        leg2.position.set(0.9, 0.375, 0.1);
        group.add(leg2);

        const leg3 = new THREE.Mesh(legGeo, mat);
        leg3.position.set(0.1, 0.375, 0.5);
        group.add(leg3);

        const leg4 = new THREE.Mesh(legGeo, mat);
        leg4.position.set(0.9, 0.375, 0.5);
        group.add(leg4);

        group.position.set(x, y, z);
        group.userData.type = 'table';
        this.scene.add(group);
        this.placedAssets.push(group);
        return group;
    }

    // Create bookshelf
    createBookshelf(x, y, z) {
        const group = new THREE.Group();

        const woodMat = new THREE.MeshStandardMaterial({ color: 0x6b4423, roughness: 0.9 });

        // Frame
        const back = new THREE.Mesh(new THREE.BoxGeometry(1.0, 1.0, 0.1), woodMat);
        back.position.set(0.5, 0.5, 0.05);
        group.add(back);

        const side1 = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.0, 0.4), woodMat);
        side1.position.set(0.03, 0.5, 0.2);
        group.add(side1);

        const side2 = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.0, 0.4), woodMat);
        side2.position.set(0.97, 0.5, 0.2);
        group.add(side2);

        // Shelves
        const shelf1 = new THREE.Mesh(new THREE.BoxGeometry(0.94, 0.04, 0.38), woodMat);
        shelf1.position.set(0.5, 0.33, 0.2);
        group.add(shelf1);

        const shelf2 = new THREE.Mesh(new THREE.BoxGeometry(0.94, 0.04, 0.38), woodMat);
        shelf2.position.set(0.5, 0.66, 0.2);
        group.add(shelf2);

        // Books
        const bookColors = [0xcc3333, 0x3366cc, 0x33cc33, 0xcccc33, 0xcc33cc];
        for (let row = 0; row < 2; row++) {
            let xPos = 0.12;
            for (let i = 0; i < 5; i++) {
                const bookMat = new THREE.MeshStandardMaterial({ color: bookColors[i], roughness: 0.9 });
                const height = 0.2 + Math.random() * 0.1;
                const book = new THREE.Mesh(new THREE.BoxGeometry(0.08, height, 0.25), bookMat);
                book.position.set(xPos, 0.35 + row * 0.33 + height/2, 0.2);
                group.add(book);
                xPos += 0.16;
            }
        }

        group.position.set(x, y, z);
        group.userData.type = 'bookshelf';
        this.scene.add(group);
        this.placedAssets.push(group);
        return group;
    }

    // Create fence
    createFence(x, y, z, length = 1, rotation = 0) {
        const group = new THREE.Group();
        const mat = new THREE.MeshStandardMaterial({ color: 0x8b7355, roughness: 0.9 });

        for (let i = 0; i < length; i++) {
            // Post
            const post = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.8, 0.08), mat);
            post.position.set(i, 0.4, 0);
            group.add(post);

            // Rails
            if (i < length - 1) {
                const rail1 = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.04, 0.04), mat);
                rail1.position.set(i + 0.5, 0.25, 0);
                group.add(rail1);

                const rail2 = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.04, 0.04), mat);
                rail2.position.set(i + 0.5, 0.55, 0);
                group.add(rail2);
            }
        }

        group.position.set(x, y, z);
        group.rotation.y = rotation;
        group.userData.type = 'fence';
        this.scene.add(group);
        this.placedAssets.push(group);
        return group;
    }

    // Create lamp
    createLamp(x, y, z) {
        const group = new THREE.Group();

        // Pole
        const poleMat = new THREE.MeshStandardMaterial({ color: 0x444444, metalness: 0.8, roughness: 0.3 });
        const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 1.5, 8), poleMat);
        pole.position.set(0, 0.75, 0);
        group.add(pole);

        // Shade
        const shadeMat = new THREE.MeshStandardMaterial({
            color: 0xffeecc,
            emissive: 0xffaa66,
            emissiveIntensity: 0.3,
            roughness: 0.8,
            transparent: true,
            opacity: 0.8
        });
        const shade = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.25, 0.3, 8, 1, true), shadeMat);
        shade.position.set(0, 1.55, 0);
        group.add(shade);

        // Light bulb
        const bulbMat = new THREE.MeshStandardMaterial({
            color: 0xffffcc,
            emissive: 0xffffaa,
            emissiveIntensity: 1.0
        });
        const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.08, 8, 8), bulbMat);
        bulb.position.set(0, 1.5, 0);
        group.add(bulb);

        // Light
        const light = new THREE.PointLight(0xffeedd, 0.8, 10, 2);
        light.position.set(0, 1.5, 0);
        group.add(light);

        group.position.set(x + 0.5, y, z + 0.5);
        group.userData.type = 'lamp';
        group.userData.light = light;
        this.scene.add(group);
        this.placedAssets.push(group);
        return group;
    }

    // Create flower pot
    createFlowerPot(x, y, z, flowerColor = 0xff6688) {
        const group = new THREE.Group();

        // Pot
        const potMat = new THREE.MeshStandardMaterial({ color: 0xaa5533, roughness: 0.9 });
        const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.12, 0.2, 8), potMat);
        pot.position.set(0.5, 0.1, 0.5);
        group.add(pot);

        // Dirt
        const dirtMat = new THREE.MeshStandardMaterial({ color: 0x5c3a1e, roughness: 0.95 });
        const dirt = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.13, 0.05, 8), dirtMat);
        dirt.position.set(0.5, 0.22, 0.5);
        group.add(dirt);

        // Stem
        const stemMat = new THREE.MeshStandardMaterial({ color: 0x228b22, roughness: 0.9 });
        const stem = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.3, 0.02), stemMat);
        stem.position.set(0.5, 0.37, 0.5);
        group.add(stem);

        // Flower
        const flowerMat = new THREE.MeshStandardMaterial({ color: flowerColor, roughness: 0.8 });
        const flower = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.12, 0.12), flowerMat);
        flower.position.set(0.5, 0.55, 0.5);
        group.add(flower);

        group.position.set(x, y, z);
        group.userData.type = 'flower_pot';
        this.scene.add(group);
        this.placedAssets.push(group);
        return group;
    }

    // Animate torch flames
    updateAnimations(time) {
        for (const asset of this.placedAssets) {
            if (asset.userData.type === 'torch') {
                const flame = asset.children.find(c => c.userData.isFlame);
                if (flame) {
                    flame.scale.y = 1 + Math.sin(time * 10) * 0.2;
                    flame.scale.x = 1 + Math.sin(time * 8 + 1) * 0.1;
                }
                // Flicker light
                if (asset.userData.light) {
                    asset.userData.light.intensity = 0.8 + Math.sin(time * 12) * 0.2;
                }
            }
        }
    }

    // Get all placed assets
    getPlacedAssets() {
        return this.placedAssets;
    }

    // Remove asset
    removeAsset(asset) {
        const index = this.placedAssets.indexOf(asset);
        if (index > -1) {
            this.scene.remove(asset);
            this.placedAssets.splice(index, 1);
        }
    }
}

// Asset types for inventory
const ASSET_TYPES = {
    WINDOW: 'window',
    DOOR: 'door',
    TORCH: 'torch',
    CRAFTING_TABLE: 'crafting_table',
    CHEST: 'chest',
    BED: 'bed',
    CHAIR: 'chair',
    TABLE: 'table',
    BOOKSHELF: 'bookshelf',
    FENCE: 'fence',
    LAMP: 'lamp',
    FLOWER_POT: 'flower_pot'
};

window.BuildingAssets = BuildingAssets;
window.ASSET_TYPES = ASSET_TYPES;
