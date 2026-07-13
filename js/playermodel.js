// Player model - clean refined character
class PlayerModel {
    constructor(playerId, scene, config = null) {
        this.playerId = playerId;
        this.scene = scene;
        this.group = new THREE.Group();
        this.animTime = 0;
        this.showCollision = false;

        this.config = config || this.getDefaultConfig();
        this.isFemale = this.config.gender === 'female';

        this.createModel();
        this.createCollisionBox();
        this.createLight();
        scene.add(this.group);
    }

    getDefaultConfig() {
        return this.playerId === 1 ? {
            name: 'Steve',
            gender: 'male',
            skinColor: 0xf5c6a0,
            hairColor: 0x3d2314,
            hairStyle: 'short',
            eyeColor: 0x4a90d9,
            shirtColor: 0x2266cc,
            pantsColor: 0x333366,
            shoeColor: 0x222222,
            facialHair: 'none'
        } : {
            name: 'Alex',
            gender: 'female',
            skinColor: 0xfdd9b5,
            hairColor: 0x8b4513,
            hairStyle: 'long',
            eyeColor: 0x50c878,
            shirtColor: 0xcc4466,
            pantsColor: 0x444466,
            shoeColor: 0x333333,
            accessory: 'none'
        };
    }

    createModel() {
        const c = this.config;
        this.createHead(c);
        this.createBody(c);
        this.createArms(c);
        this.createLegs(c);
        if (this.isFemale && c.accessory && c.accessory !== 'none') {
            this.createAccessory(c.accessory);
        }
        this.createNameTag(c.name || `Jugador ${this.playerId}`);
    }

    createHead(c) {
        // Clean head
        const headGeo = new THREE.BoxGeometry(0.5, 0.5, 0.5);
        const headMat = new THREE.MeshStandardMaterial({ color: c.skinColor, roughness: 0.8 });
        this.head = new THREE.Mesh(headGeo, headMat);
        this.head.position.y = 1.65;
        this.head.castShadow = true;
        this.group.add(this.head);

        // Neck
        const neckGeo = new THREE.BoxGeometry(0.15, 0.15, 0.15);
        const neckMat = new THREE.MeshStandardMaterial({ color: c.skinColor, roughness: 0.8 });
        const neck = new THREE.Mesh(neckGeo, neckMat);
        neck.position.set(0, 1.35, 0);
        this.group.add(neck);

        // Ears
        const earGeo = new THREE.BoxGeometry(0.05, 0.1, 0.06);
        const earMat = new THREE.MeshStandardMaterial({ color: this.darken(c.skinColor, 0.05), roughness: 0.8 });
        const leftEar = new THREE.Mesh(earGeo, earMat);
        leftEar.position.set(-0.26, 1.65, 0);
        this.group.add(leftEar);
        const rightEar = new THREE.Mesh(earGeo, earMat);
        rightEar.position.set(0.26, 1.65, 0);
        this.group.add(rightEar);

        // Eyes
        this.createEyes(c.eyeColor);

        // Facial hair for males
        if (!this.isFemale && c.facialHair && c.facialHair !== 'none') {
            this.createFacialHair(c.hairColor, c.facialHair);
        }

        // Hair
        this.createHair(c.hairColor, c.hairStyle);
    }

    createFacialHair(color, style) {
        const hairMat = new THREE.MeshStandardMaterial({ color, roughness: 0.9 });

        if (style === 'mustache') {
            const mustacheGeo = new THREE.BoxGeometry(0.18, 0.035, 0.02);
            const mustache = new THREE.Mesh(mustacheGeo, hairMat);
            mustache.position.set(0, 1.57, 0.26);
            this.group.add(mustache);

        } else if (style === 'beard') {
            // Full beard covering chin and upper lip
            const beardGeo = new THREE.BoxGeometry(0.22, 0.15, 0.03);
            const beard = new THREE.Mesh(beardGeo, hairMat);
            beard.position.set(0, 1.5, 0.25);
            this.group.add(beard);

            // Mustache
            const mustacheGeo = new THREE.BoxGeometry(0.16, 0.03, 0.02);
            const mustache = new THREE.Mesh(mustacheGeo, hairMat);
            mustache.position.set(0, 1.58, 0.26);
            this.group.add(mustache);

            // Sideburns
            const sideGeo = new THREE.BoxGeometry(0.04, 0.12, 0.04);
            const leftSide = new THREE.Mesh(sideGeo, hairMat);
            leftSide.position.set(-0.24, 1.6, 0);
            this.group.add(leftSide);
            const rightSide = new THREE.Mesh(sideGeo, hairMat);
            rightSide.position.set(0.24, 1.6, 0);
            this.group.add(rightSide);

        } else if (style === 'goatee') {
            // Goatee on chin
            const goateeGeo = new THREE.BoxGeometry(0.1, 0.1, 0.03);
            const goatee = new THREE.Mesh(goateeGeo, hairMat);
            goatee.position.set(0, 1.5, 0.26);
            this.group.add(goatee);

            // Small mustache
            const mustacheGeo = new THREE.BoxGeometry(0.12, 0.025, 0.02);
            const mustache = new THREE.Mesh(mustacheGeo, hairMat);
            mustache.position.set(0, 1.57, 0.26);
            this.group.add(mustache);

        } else if (style === 'stubble') {
            // Stubble on chin and upper lip area
            for (let i = 0; i < 12; i++) {
                const dotGeo = new THREE.BoxGeometry(0.015, 0.015, 0.01);
                const dot = new THREE.Mesh(dotGeo, hairMat);
                // Chin area
                dot.position.set(
                    (Math.random() - 0.5) * 0.18,
                    1.5 + Math.random() * 0.08,
                    0.26
                );
                this.group.add(dot);
            }
            // Upper lip dots
            for (let i = 0; i < 6; i++) {
                const dotGeo = new THREE.BoxGeometry(0.015, 0.015, 0.01);
                const dot = new THREE.Mesh(dotGeo, hairMat);
                dot.position.set(
                    (Math.random() - 0.5) * 0.12,
                    1.58,
                    0.26
                );
                this.group.add(dot);
            }
        }
    }

    createAccessory(type) {
        if (type === 'necklace') {
            const chainGeo = new THREE.BoxGeometry(0.2, 0.02, 0.02);
            const chainMat = new THREE.MeshStandardMaterial({ color: 0xddaa44, metalness: 0.8, roughness: 0.2 });
            const chain = new THREE.Mesh(chainGeo, chainMat);
            chain.position.set(0, 1.28, 0.14);
            this.group.add(chain);

            // Pendant
            const pendantGeo = new THREE.BoxGeometry(0.04, 0.06, 0.02);
            const pendantMat = new THREE.MeshStandardMaterial({ color: 0x44aaff, metalness: 0.6, roughness: 0.3 });
            const pendant = new THREE.Mesh(pendantGeo, pendantMat);
            pendant.position.set(0, 1.24, 0.15);
            this.group.add(pendant);

        } else if (type === 'earrings') {
            const earringGeo = new THREE.BoxGeometry(0.03, 0.06, 0.02);
            const earringMat = new THREE.MeshStandardMaterial({ color: 0xffd700, metalness: 0.9, roughness: 0.1 });

            const leftEarring = new THREE.Mesh(earringGeo, earringMat);
            leftEarring.position.set(-0.28, 1.6, 0);
            this.group.add(leftEarring);

            const rightEarring = new THREE.Mesh(earringGeo, earringMat);
            rightEarring.position.set(0.28, 1.6, 0);
            this.group.add(rightEarring);

        } else if (type === 'bow') {
            const bowMat = new THREE.MeshStandardMaterial({ color: 0xff6688, roughness: 0.8 });

            // Left wing
            const wingGeo = new THREE.BoxGeometry(0.06, 0.04, 0.02);
            const leftWing = new THREE.Mesh(wingGeo, bowMat);
            leftWing.position.set(-0.04, 1.35, 0.14);
            leftWing.rotation.z = 0.3;
            this.group.add(leftWing);

            // Right wing
            const rightWing = new THREE.Mesh(wingGeo, bowMat);
            rightWing.position.set(0.04, 1.35, 0.14);
            rightWing.rotation.z = -0.3;
            this.group.add(rightWing);

            // Center knot
            const knotGeo = new THREE.BoxGeometry(0.03, 0.03, 0.03);
            const knot = new THREE.Mesh(knotGeo, bowMat);
            knot.position.set(0, 1.35, 0.15);
            this.group.add(knot);
        }
    }

    createEyes(eyeColor) {
        // Eyes - larger for females
        const scale = this.isFemale ? 1.3 : 1;
        const eyeWhiteGeo = new THREE.BoxGeometry(0.14 * scale, 0.1 * scale, 0.01);
        const eyeWhiteMat = new THREE.MeshBasicMaterial({ color: 0xffffff });

        const irisGeo = new THREE.BoxGeometry(0.09 * scale, 0.09 * scale, 0.01);
        const irisMat = new THREE.MeshBasicMaterial({ color: eyeColor });

        const pupilGeo = new THREE.BoxGeometry(0.05 * scale, 0.05 * scale, 0.01);
        const pupilMat = new THREE.MeshBasicMaterial({ color: 0x111111 });

        const shineGeo = new THREE.BoxGeometry(0.03 * scale, 0.03 * scale, 0.01);
        const shineMat = new THREE.MeshBasicMaterial({ color: 0xffffff });

        // Left eye
        const leftWhite = new THREE.Mesh(eyeWhiteGeo, eyeWhiteMat);
        leftWhite.position.set(-0.1, 1.68, 0.25);
        this.group.add(leftWhite);
        const leftIris = new THREE.Mesh(irisGeo, irisMat);
        leftIris.position.set(-0.1, 1.68, 0.26);
        this.group.add(leftIris);
        const leftPupil = new THREE.Mesh(pupilGeo, pupilMat);
        leftPupil.position.set(-0.1, 1.68, 0.27);
        this.group.add(leftPupil);
        const leftShine = new THREE.Mesh(shineGeo, shineMat);
        leftShine.position.set(-0.08, 1.71, 0.27);
        this.group.add(leftShine);

        // Right eye
        const rightWhite = new THREE.Mesh(eyeWhiteGeo, eyeWhiteMat);
        rightWhite.position.set(0.1, 1.68, 0.25);
        this.group.add(rightWhite);
        const rightIris = new THREE.Mesh(irisGeo, irisMat);
        rightIris.position.set(0.1, 1.68, 0.26);
        this.group.add(rightIris);
        const rightPupil = new THREE.Mesh(pupilGeo, pupilMat);
        rightPupil.position.set(0.1, 1.68, 0.27);
        this.group.add(rightPupil);
        const rightShine = new THREE.Mesh(shineGeo, shineMat);
        rightShine.position.set(0.12, 1.71, 0.27);
        this.group.add(rightShine);

        // Eyebrows
        const browGeo = new THREE.BoxGeometry(0.12, 0.02, 0.01);
        const browMat = new THREE.MeshStandardMaterial({ color: 0x333333 });
        const leftBrow = new THREE.Mesh(browGeo, browMat);
        leftBrow.position.set(-0.1, 1.76, 0.25);
        this.group.add(leftBrow);
        const rightBrow = new THREE.Mesh(browGeo, browMat);
        rightBrow.position.set(0.1, 1.76, 0.25);
        this.group.add(rightBrow);
    }

    createHair(hairColor, style) {
        const hairMat = new THREE.MeshStandardMaterial({ color: hairColor, roughness: 0.9 });

        if (style === 'short') {
            // Top cap - more volume
            const topGeo = new THREE.BoxGeometry(0.56, 0.12, 0.56);
            const top = new THREE.Mesh(topGeo, hairMat);
            top.position.set(0, 1.94, 0);
            this.group.add(top);

            // Sides - wider and fuller
            const sideGeo = new THREE.BoxGeometry(0.1, 0.25, 0.52);
            const leftSide = new THREE.Mesh(sideGeo, hairMat);
            leftSide.position.set(-0.28, 1.78, 0);
            this.group.add(leftSide);
            const rightSide = new THREE.Mesh(sideGeo, hairMat);
            rightSide.position.set(0.28, 1.78, 0);
            this.group.add(rightSide);

            // Back
            const backGeo = new THREE.BoxGeometry(0.56, 0.32, 0.1);
            const back = new THREE.Mesh(backGeo, hairMat);
            back.position.set(0, 1.78, -0.26);
            this.group.add(back);

            // Fringe
            const fringeGeo = new THREE.BoxGeometry(0.4, 0.07, 0.07);
            const fringe = new THREE.Mesh(fringeGeo, hairMat);
            fringe.position.set(0, 1.89, 0.25);
            this.group.add(fringe);

        } else if (style === 'long') {
            // Top - full coverage
            const topGeo = new THREE.BoxGeometry(0.58, 0.14, 0.58);
            const top = new THREE.Mesh(topGeo, hairMat);
            top.position.set(0, 1.95, 0);
            this.group.add(top);

            // Sides - full coverage, no gaps
            const sideGeo = new THREE.BoxGeometry(0.12, 0.75, 0.35);
            const leftSide = new THREE.Mesh(sideGeo, hairMat);
            leftSide.position.set(-0.29, 1.55, -0.02);
            this.group.add(leftSide);
            const rightSide = new THREE.Mesh(sideGeo, hairMat);
            rightSide.position.set(0.28, 1.55, -0.02);
            this.group.add(rightSide);

            // Back - long and full
            const backGeo = new THREE.BoxGeometry(0.54, 0.75, 0.1);
            const back = new THREE.Mesh(backGeo, hairMat);
            back.position.set(0, 1.5, -0.24);
            this.group.add(back);

            // Bangs - softer
            const bangGeo = new THREE.BoxGeometry(0.44, 0.08, 0.06);
            const bang = new THREE.Mesh(bangGeo, hairMat);
            bang.position.set(0, 1.86, 0.25);
            this.group.add(bang);

            // Side bangs
            const sideBangGeo = new THREE.BoxGeometry(0.08, 0.12, 0.06);
            const leftBang = new THREE.Mesh(sideBangGeo, hairMat);
            leftBang.position.set(-0.2, 1.82, 0.24);
            this.group.add(leftBang);
            const rightBang = new THREE.Mesh(sideBangGeo, hairMat);
            rightBang.position.set(0.2, 1.82, 0.24);
            this.group.add(rightBang);

        } else if (style === 'ponytail') {
            // Top
            const topGeo = new THREE.BoxGeometry(0.54, 0.1, 0.54);
            const top = new THREE.Mesh(topGeo, hairMat);
            top.position.set(0, 1.92, 0);
            this.group.add(top);

            // Sides
            const sideGeo = new THREE.BoxGeometry(0.08, 0.2, 0.48);
            const leftSide = new THREE.Mesh(sideGeo, hairMat);
            leftSide.position.set(-0.27, 1.78, 0);
            this.group.add(leftSide);
            const rightSide = new THREE.Mesh(sideGeo, hairMat);
            rightSide.position.set(0.27, 1.78, 0);
            this.group.add(rightSide);

            // Back
            const backGeo = new THREE.BoxGeometry(0.54, 0.25, 0.08);
            const back = new THREE.Mesh(backGeo, hairMat);
            back.position.set(0, 1.78, -0.25);
            this.group.add(back);

            // Ponytail base
            const baseGeo = new THREE.BoxGeometry(0.14, 0.1, 0.14);
            const base = new THREE.Mesh(baseGeo, hairMat);
            base.position.set(0, 1.88, -0.22);
            this.group.add(base);

            // Ponytail
            const tailGeo = new THREE.BoxGeometry(0.1, 0.5, 0.1);
            const tail = new THREE.Mesh(tailGeo, hairMat);
            tail.position.set(0, 1.65, -0.3);
            tail.rotation.x = 0.3;
            this.group.add(tail);

            // Hair tie
            const tieGeo = new THREE.BoxGeometry(0.11, 0.03, 0.11);
            const tieMat = new THREE.MeshStandardMaterial({ color: 0xcc4444 });
            const tie = new THREE.Mesh(tieGeo, tieMat);
            tie.position.set(0, 1.87, -0.26);
            this.group.add(tie);

        } else if (style === 'mohawk') {
            // Sides shaved
            const sideGeo = new THREE.BoxGeometry(0.04, 0.15, 0.48);
            const leftSide = new THREE.Mesh(sideGeo, hairMat);
            leftSide.position.set(-0.26, 1.78, 0);
            this.group.add(leftSide);
            const rightSide = new THREE.Mesh(sideGeo, hairMat);
            rightSide.position.set(0.26, 1.78, 0);
            this.group.add(rightSide);

            // Mohawk ridge
            const ridgeGeo = new THREE.BoxGeometry(0.1, 0.2, 0.3);
            const ridge = new THREE.Mesh(ridgeGeo, hairMat);
            ridge.position.set(0, 1.98, 0);
            this.group.add(ridge);

            // Front spike
            const spikeGeo = new THREE.BoxGeometry(0.08, 0.15, 0.08);
            const spike = new THREE.Mesh(spikeGeo, hairMat);
            spike.position.set(0, 1.95, 0.2);
            spike.rotation.x = -0.3;
            this.group.add(spike);

        } else if (style === 'bun') {
            // Top
            const topGeo = new THREE.BoxGeometry(0.54, 0.1, 0.54);
            const top = new THREE.Mesh(topGeo, hairMat);
            top.position.set(0, 1.92, 0);
            this.group.add(top);

            // Sides
            const sideGeo = new THREE.BoxGeometry(0.08, 0.2, 0.48);
            const leftSide = new THREE.Mesh(sideGeo, hairMat);
            leftSide.position.set(-0.27, 1.78, 0);
            this.group.add(leftSide);
            const rightSide = new THREE.Mesh(sideGeo, hairMat);
            rightSide.position.set(0.27, 1.78, 0);
            this.group.add(rightSide);

            // Back
            const backGeo = new THREE.BoxGeometry(0.54, 0.25, 0.08);
            const back = new THREE.Mesh(backGeo, hairMat);
            back.position.set(0, 1.78, -0.25);
            this.group.add(back);

            // Bun
            const bunGeo = new THREE.BoxGeometry(0.18, 0.18, 0.18);
            const bun = new THREE.Mesh(bunGeo, hairMat);
            bun.position.set(0, 1.92, -0.22);
            this.group.add(bun);

            // Bangs
            const bangGeo = new THREE.BoxGeometry(0.38, 0.06, 0.06);
            const bang = new THREE.Mesh(bangGeo, hairMat);
            bang.position.set(0, 1.88, 0.24);
            this.group.add(bang);

        } else if (style === 'bald') {
            // Male only - bald (no hair)
            // Just leave empty - head shows through

        } else if (style === 'punk') {
            // Punk crest - both genders
            const sideMat = new THREE.MeshStandardMaterial({ color: this.darken(hairColor, 0.4), roughness: 0.9 });

            // Sides shaved
            const sideGeo = new THREE.BoxGeometry(0.04, 0.18, 0.46);
            const leftSide = new THREE.Mesh(sideGeo, sideMat);
            leftSide.position.set(-0.26, 1.78, 0);
            this.group.add(leftSide);
            const rightSide = new THREE.Mesh(sideGeo, sideMat);
            rightSide.position.set(0.26, 1.78, 0);
            this.group.add(rightSide);

            // Back short
            const backGeo = new THREE.BoxGeometry(0.54, 0.15, 0.04);
            const back = new THREE.Mesh(backGeo, sideMat);
            back.position.set(0, 1.78, -0.25);
            this.group.add(back);

            // Large crest
            const crestGeo = new THREE.BoxGeometry(0.12, 0.25, 0.25);
            const crest = new THREE.Mesh(crestGeo, hairMat);
            crest.position.set(0, 2.02, 0);
            this.group.add(crest);

            // Front spike
            const spikeGeo = new THREE.BoxGeometry(0.08, 0.15, 0.08);
            const spike = new THREE.Mesh(spikeGeo, hairMat);
            spike.position.set(0, 2.0, 0.15);
            spike.rotation.x = -0.2;
            this.group.add(spike);

        } else if (style === 'braids') {
            // Female only - voluminous braids
            const topGeo = new THREE.BoxGeometry(0.56, 0.12, 0.56);
            const top = new THREE.Mesh(topGeo, hairMat);
            top.position.set(0, 1.94, 0);
            this.group.add(top);

            // Sides - full coverage
            const sideGeo = new THREE.BoxGeometry(0.1, 0.3, 0.48);
            const leftSide = new THREE.Mesh(sideGeo, hairMat);
            leftSide.position.set(-0.28, 1.75, 0);
            this.group.add(leftSide);
            const rightSide = new THREE.Mesh(sideGeo, hairMat);
            rightSide.position.set(0.28, 1.75, 0);
            this.group.add(rightSide);

            // Back
            const backGeo = new THREE.BoxGeometry(0.56, 0.35, 0.1);
            const back = new THREE.Mesh(backGeo, hairMat);
            back.position.set(0, 1.72, -0.25);
            this.group.add(back);

            // Left braid - thick and long
            const braidGeo = new THREE.BoxGeometry(0.12, 0.65, 0.12);
            const leftBraid = new THREE.Mesh(braidGeo, hairMat);
            leftBraid.position.set(-0.24, 1.45, -0.08);
            leftBraid.rotation.x = 0.1;
            this.group.add(leftBraid);

            // Right braid
            const rightBraid = new THREE.Mesh(braidGeo, hairMat);
            rightBraid.position.set(0.24, 1.45, -0.08);
            rightBraid.rotation.x = 0.1;
            this.group.add(rightBraid);

            // Braid ties
            const tieGeo = new THREE.BoxGeometry(0.13, 0.04, 0.13);
            const tieMat = new THREE.MeshStandardMaterial({ color: 0xffaa44 });
            const leftTie = new THREE.Mesh(tieGeo, tieMat);
            leftTie.position.set(-0.24, 1.14, -0.06);
            this.group.add(leftTie);
            const rightTie = new THREE.Mesh(tieGeo, tieMat);
            rightTie.position.set(0.24, 1.14, -0.06);
            this.group.add(rightTie);

            // Bangs
            const bangGeo = new THREE.BoxGeometry(0.44, 0.08, 0.06);
            const bang = new THREE.Mesh(bangGeo, hairMat);
            bang.position.set(0, 1.88, 0.25);
            this.group.add(bang);

        } else if (style === 'bob') {
            // Female only - bob cut
            const topGeo = new THREE.BoxGeometry(0.54, 0.1, 0.54);
            const top = new THREE.Mesh(topGeo, hairMat);
            top.position.set(0, 1.93, 0);
            this.group.add(top);

            // Full coverage sides
            const sideGeo = new THREE.BoxGeometry(0.1, 0.35, 0.35);
            const leftSide = new THREE.Mesh(sideGeo, hairMat);
            leftSide.position.set(-0.28, 1.7, 0);
            this.group.add(leftSide);
            const rightSide = new THREE.Mesh(sideGeo, hairMat);
            rightSide.position.set(0.28, 1.7, 0);
            this.group.add(rightSide);

            // Back
            const backGeo = new THREE.BoxGeometry(0.54, 0.4, 0.1);
            const back = new THREE.Mesh(backGeo, hairMat);
            back.position.set(0, 1.68, -0.24);
            this.group.add(back);

            // Bangs
            const bangGeo = new THREE.BoxGeometry(0.46, 0.08, 0.06);
            const bang = new THREE.Mesh(bangGeo, hairMat);
            bang.position.set(0, 1.87, 0.24);
            this.group.add(bang);

        } else if (style === 'undercut') {
            // Male only - undercut
            const topGeo = new THREE.BoxGeometry(0.48, 0.12, 0.48);
            const top = new THREE.Mesh(topGeo, hairMat);
            top.position.set(0, 1.94, 0);
            this.group.add(top);

            // Sides very short (different color)
            const sideMat = new THREE.MeshStandardMaterial({ color: this.darken(hairColor, 0.3), roughness: 0.9 });
            const sideGeo = new THREE.BoxGeometry(0.03, 0.2, 0.46);
            const leftSide = new THREE.Mesh(sideGeo, sideMat);
            leftSide.position.set(-0.26, 1.78, 0);
            this.group.add(leftSide);
            const rightSide = new THREE.Mesh(sideGeo, sideMat);
            rightSide.position.set(0.26, 1.78, 0);
            this.group.add(rightSide);

            // Back short
            const backGeo = new THREE.BoxGeometry(0.54, 0.2, 0.03);
            const back = new THREE.Mesh(backGeo, sideMat);
            back.position.set(0, 1.78, -0.25);
            this.group.add(back);
        }
    }

    createBody(c) {
        if (this.isFemale) {
            // Female body - slightly narrower
            const bodyGeo = new THREE.BoxGeometry(0.42, 0.5, 0.24);
            const bodyMat = new THREE.MeshStandardMaterial({ color: c.shirtColor, roughness: 0.8 });
            this.body = new THREE.Mesh(bodyGeo, bodyMat);
            this.body.position.y = 1.0;
            this.body.castShadow = true;
            this.group.add(this.body);

            // V-neck collar
            const collarGeo = new THREE.BoxGeometry(0.25, 0.06, 0.25);
            const collarMat = new THREE.MeshStandardMaterial({ color: this.darken(c.shirtColor, 0.1), roughness: 0.8 });
            const collar = new THREE.Mesh(collarGeo, collarMat);
            collar.position.set(0, 1.23, 0);
            this.group.add(collar);

            // Skirt or pants based on selection
            const pantsMat = new THREE.MeshStandardMaterial({ color: c.pantsColor, roughness: 0.8 });
            if (c.pantsType === 'pants') {
                // Female pants
                const pantsGeo = new THREE.BoxGeometry(0.44, 0.2, 0.26);
                const pants = new THREE.Mesh(pantsGeo, pantsMat);
                pants.position.set(0, 0.68, 0);
                this.group.add(pants);
            } else {
                // Skirt (default)
                const skirtGeo = new THREE.BoxGeometry(0.48, 0.25, 0.28);
                const skirt = new THREE.Mesh(skirtGeo, pantsMat);
                skirt.position.set(0, 0.65, 0);
                this.group.add(skirt);
            }

            // Belt with bow
            const beltGeo = new THREE.BoxGeometry(0.44, 0.04, 0.25);
            const beltMat = new THREE.MeshStandardMaterial({ color: 0x3d2314, roughness: 0.9 });
            const belt = new THREE.Mesh(beltGeo, beltMat);
            belt.position.set(0, 0.76, 0);
            this.group.add(belt);

            // Bow
            const bowGeo = new THREE.BoxGeometry(0.08, 0.06, 0.02);
            const bowMat = new THREE.MeshStandardMaterial({ color: this.darken(c.shirtColor, 0.2) });
            const bow = new THREE.Mesh(bowGeo, bowMat);
            bow.position.set(0, 0.76, 0.13);
            this.group.add(bow);

        } else {
            // Male body - broader shoulders
            const bodyGeo = new THREE.BoxGeometry(0.5, 0.55, 0.26);
            const bodyMat = new THREE.MeshStandardMaterial({ color: c.shirtColor, roughness: 0.8 });
            this.body = new THREE.Mesh(bodyGeo, bodyMat);
            this.body.position.y = 0.98;
            this.body.castShadow = true;
            this.group.add(this.body);

            // Collar
            const collarGeo = new THREE.BoxGeometry(0.34, 0.05, 0.27);
            const collarMat = new THREE.MeshStandardMaterial({ color: this.darken(c.shirtColor, 0.15), roughness: 0.8 });
            const collar = new THREE.Mesh(collarGeo, collarMat);
            collar.position.set(0, 1.23, 0);
            this.group.add(collar);

            // Belt with buckle
            const beltGeo = new THREE.BoxGeometry(0.51, 0.05, 0.27);
            const beltMat = new THREE.MeshStandardMaterial({ color: 0x3d2314, roughness: 0.9 });
            const belt = new THREE.Mesh(beltGeo, beltMat);
            belt.position.set(0, 0.73, 0);
            this.group.add(belt);

            const buckleGeo = new THREE.BoxGeometry(0.06, 0.04, 0.02);
            const buckleMat = new THREE.MeshStandardMaterial({ color: 0xccaa44, metalness: 0.8, roughness: 0.2 });
            const buckle = new THREE.Mesh(buckleGeo, buckleMat);
            buckle.position.set(0, 0.73, 0.14);
            this.group.add(buckle);

            // Pocket
            const pocketGeo = new THREE.BoxGeometry(0.08, 0.08, 0.01);
            const pocketMat = new THREE.MeshStandardMaterial({ color: this.darken(c.pantsColor, 0.1) });
            const pocket = new THREE.Mesh(pocketGeo, pocketMat);
            pocket.position.set(0.15, 0.82, 0.14);
            this.group.add(pocket);
        }
    }

    createArms(c) {
        const armMat = new THREE.MeshStandardMaterial({ color: c.shirtColor, roughness: 0.8 });
        const skinMat = new THREE.MeshStandardMaterial({ color: c.skinColor, roughness: 0.8 });

        // Thinner arms for females
        const armWidth = this.isFemale ? 0.11 : 0.14;
        const lowerArmWidth = this.isFemale ? 0.09 : 0.12;
        const handSize = this.isFemale ? 0.08 : 0.1;

        const upperArmGeo = new THREE.BoxGeometry(armWidth, 0.3, armWidth);
        this.leftArm = new THREE.Mesh(upperArmGeo, armMat);
        this.leftArm.position.set(-0.3, 1.12, 0);
        this.leftArm.castShadow = true;
        this.group.add(this.leftArm);

        this.rightArm = new THREE.Mesh(upperArmGeo, armMat);
        this.rightArm.position.set(0.3, 1.12, 0);
        this.rightArm.castShadow = true;
        this.group.add(this.rightArm);

        const lowerArmGeo = new THREE.BoxGeometry(lowerArmWidth, 0.22, lowerArmWidth);
        this.leftForearm = new THREE.Mesh(lowerArmGeo, skinMat);
        this.leftForearm.position.set(-0.3, 0.84, 0);
        this.leftForearm.castShadow = true;
        this.group.add(this.leftForearm);

        this.rightForearm = new THREE.Mesh(lowerArmGeo, skinMat);
        this.rightForearm.position.set(0.3, 0.84, 0);
        this.rightForearm.castShadow = true;
        this.group.add(this.rightForearm);

        const handGeo = new THREE.BoxGeometry(handSize, handSize, handSize);
        this.leftHand = new THREE.Mesh(handGeo, skinMat);
        this.leftHand.position.set(-0.3, 0.68, 0);
        this.group.add(this.leftHand);

        this.rightHand = new THREE.Mesh(handGeo, skinMat);
        this.rightHand.position.set(0.3, 0.68, 0);
        this.group.add(this.rightHand);
    }

    createLegs(c) {
        const legMat = new THREE.MeshStandardMaterial({ color: c.pantsColor, roughness: 0.8 });
        const shoeMat = new THREE.MeshStandardMaterial({ color: c.shoeColor, roughness: 0.9 });

        const upperLegGeo = new THREE.BoxGeometry(0.17, 0.35, 0.17);
        this.leftUpperLeg = new THREE.Mesh(upperLegGeo, legMat);
        this.leftUpperLeg.position.set(-0.1, 0.52, 0);
        this.leftUpperLeg.castShadow = true;
        this.group.add(this.leftUpperLeg);

        this.rightUpperLeg = new THREE.Mesh(upperLegGeo, legMat);
        this.rightUpperLeg.position.set(0.1, 0.52, 0);
        this.rightUpperLeg.castShadow = true;
        this.group.add(this.rightUpperLeg);

        const lowerLegGeo = new THREE.BoxGeometry(0.15, 0.25, 0.15);
        this.leftLowerLeg = new THREE.Mesh(lowerLegGeo, legMat);
        this.leftLowerLeg.position.set(-0.1, 0.22, 0);
        this.leftLowerLeg.castShadow = true;
        this.group.add(this.leftLowerLeg);

        this.rightLowerLeg = new THREE.Mesh(lowerLegGeo, legMat);
        this.rightLowerLeg.position.set(0.1, 0.22, 0);
        this.rightLowerLeg.castShadow = true;
        this.group.add(this.rightLowerLeg);

        const shoeGeo = new THREE.BoxGeometry(0.17, 0.08, 0.22);
        this.leftShoe = new THREE.Mesh(shoeGeo, shoeMat);
        this.leftShoe.position.set(-0.1, 0.04, 0.02);
        this.group.add(this.leftShoe);

        this.rightShoe = new THREE.Mesh(shoeGeo, shoeMat);
        this.rightShoe.position.set(0.1, 0.04, 0.02);
        this.group.add(this.rightShoe);
    }

    createNameTag(name) {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.fillRect(0, 0, 256, 64);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 28px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(name, 128, 32);
        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
        this.nameTag = new THREE.Sprite(material);
        this.nameTag.position.y = 2.1;
        this.nameTag.scale.set(1.2, 0.3, 1);
        this.group.add(this.nameTag);
    }

    createCollisionBox() {
        const geo = new THREE.BoxGeometry(0.6, 1.8, 0.6);
        const edges = new THREE.EdgesGeometry(geo);
        const mat = new THREE.LineBasicMaterial({ color: 0xff0000, linewidth: 2 });
        this.collisionBox = new THREE.LineSegments(edges, mat);
        this.collisionBox.position.y = 0.9;
        this.collisionBox.visible = false;
        this.group.add(this.collisionBox);
    }

    createLight() {
        this.light = new THREE.PointLight(0xffeedd, 0.8, 12, 2);
        this.light.position.set(0, 1.5, 0);
        this.group.add(this.light);
    }

    darken(color, amount) {
        const r = ((color >> 16) & 0xff) * (1 - amount);
        const g = ((color >> 8) & 0xff) * (1 - amount);
        const b = (color & 0xff) * (1 - amount);
        return (Math.floor(r) << 16) | (Math.floor(g) << 8) | Math.floor(b);
    }

    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        this.isFemale = this.config.gender === 'female';
        while (this.group.children.length > 0) {
            const child = this.group.children[0];
            this.group.remove(child);
            if (child.geometry) child.geometry.dispose();
            if (child.material) child.material.dispose();
        }
        this.createModel();
        this.createCollisionBox();
        this.createLight();
    }

    update(position, rotation, deltaTime, isMoving) {
        this.group.position.copy(position);
        this.group.rotation.y = rotation.y + Math.PI;

        this.animTime += deltaTime;
        if (isMoving) {
            const speed = 8;
            const swing = Math.sin(this.animTime * speed);
            const swing2 = Math.sin(this.animTime * speed + Math.PI / 2);

            // Upper legs - swing from hip
            const legSwing = swing * 0.6;
            if (this.leftUpperLeg) {
                this.leftUpperLeg.position.z = Math.sin(this.leftUpperLeg.rotation.x) * 0.08;
                this.leftUpperLeg.rotation.x = -legSwing;
            }
            if (this.rightUpperLeg) {
                this.rightUpperLeg.position.z = Math.sin(this.rightUpperLeg.rotation.x) * 0.08;
                this.rightUpperLeg.rotation.x = legSwing;
            }

            // Lower legs - bend at knee
            const kneeAngle = Math.max(0, -legSwing) * 0.8;
            if (this.leftLowerLeg) this.leftLowerLeg.rotation.x = kneeAngle;
            if (this.rightLowerLeg) this.rightLowerLeg.rotation.x = Math.max(0, legSwing) * 0.8;

            // Shoes - follow lower leg
            if (this.leftShoe) this.leftShoe.rotation.x = this.leftLowerLeg ? this.leftLowerLeg.rotation.x * 0.3 : 0;
            if (this.rightShoe) this.rightShoe.rotation.x = this.rightLowerLeg ? this.rightLowerLeg.rotation.x * 0.3 : 0;

            // Arms - swing opposite to legs
            const armSwing = swing * 0.5;
            if (this.leftArm) this.leftArm.rotation.x = armSwing;
            if (this.rightArm) this.rightArm.rotation.x = -armSwing;

            // Forearms - slight bend
            if (this.leftForearm) this.leftForearm.rotation.x = Math.max(0, -armSwing) * 0.4;
            if (this.rightForearm) this.rightForearm.rotation.x = Math.max(0, armSwing) * 0.4;

            // Body bob
            if (this.body) this.body.position.y = 0.98 + Math.abs(swing2) * 0.02;
            if (this.head) this.head.position.y = 1.65 + Math.abs(swing2) * 0.02;

        } else {
            const breathe = Math.sin(this.animTime * 2) * 0.008;
            if (this.body) this.body.position.y = 0.98 + breathe;
            if (this.head) this.head.position.y = 1.65 + breathe;

            // Reset to neutral
            [this.leftUpperLeg, this.rightUpperLeg, this.leftLowerLeg, this.rightLowerLeg,
             this.leftShoe, this.rightShoe, this.leftArm, this.rightArm,
             this.leftForearm, this.rightForearm].forEach(part => {
                if (part) {
                    part.rotation.x *= 0.85;
                    if (part === this.leftUpperLeg || part === this.rightUpperLeg) {
                        part.position.z *= 0.85;
                    }
                }
            });
        }
    }

    toggleCollision() {
        this.showCollision = !this.showCollision;
        this.collisionBox.visible = this.showCollision;
    }

    setVisible(visible) {
        this.group.visible = visible;
    }

    dispose() {
        this.scene.remove(this.group);
        this.group.traverse(child => {
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (child.material.map) child.material.map.dispose();
                child.material.dispose();
            }
        });
    }
}

// Character customization UI
class CharacterCustomizer {
    constructor(callback) {
        this.callback = callback;
        this.configs = [
            { gender: 'male', skinColor: 0xf5c6a0, hairColor: 0x3d2314, hairStyle: 'short', eyeColor: 0x4a90d9, shirtColor: 0x2266cc, pantsColor: 0x333366, shoeColor: 0x222222 },
            { gender: 'female', skinColor: 0xfdd9b5, hairColor: 0x8b4513, hairStyle: 'long', eyeColor: 0x50c878, shirtColor: 0xcc4466, pantsColor: 0x444466, shoeColor: 0x333333 }
        ];
        this.currentPlayer = 0;

        // Preview 3D
        this.previewScene = null;
        this.previewCamera = null;
        this.previewRenderer = null;
        this.previewModel = null;
        this.previewAnimId = null;
        this.previewRotation = 0;
        this.isDragging = false;
        this.lastMouseX = 0;
    }

    show() {
        const overlay = document.getElementById('menu-overlay');
        overlay.innerHTML = this.getHTML();
        overlay.style.display = 'flex';
        this.bindEvents();
        this.initPreview();
    }

    getHTML() {
        const c = this.configs[this.currentPlayer];
        const isFemale = c.gender === 'female';
        return `
            <h1>PERSONALIZAR JUGADOR ${this.currentPlayer + 1}</h1>
            <div class="customizer-layout">
                <div class="preview-container">
                    <canvas id="preview-canvas" width="300" height="400"></canvas>
                    <p class="preview-hint">Arrastra para rotar</p>
                </div>
                <div class="customizer-grid">
                    <div class="customizer-section">
                        <h3>Género</h3>
                        <label>
                            <select id="gender">
                                <option value="male" ${!isFemale ? 'selected' : ''}>Chico</option>
                                <option value="female" ${isFemale ? 'selected' : ''}>Chica</option>
                            </select>
                        </label>
                    </div>
                    <div class="customizer-section">
                        <h3>Nombre</h3>
                        <label>
                            <input type="text" id="playerName" value="${c.name || ''}" maxlength="12" placeholder="Nombre...">
                        </label>
                    </div>
                    <div class="customizer-section">
                        <h3>Pelo</h3>
                        <label>Estilo:
                            <select id="hairStyle">
                                ${isFemale ?
                                    `<option value="long" ${c.hairStyle === 'long' ? 'selected' : ''}>Largo</option>
                                     <option value="ponytail" ${c.hairStyle === 'ponytail' ? 'selected' : ''}>Coleta</option>
                                     <option value="bun" ${c.hairStyle === 'bun' ? 'selected' : ''}>Moño</option>
                                     <option value="braids" ${c.hairStyle === 'braids' ? 'selected' : ''}>Trenzas</option>
                                     <option value="bob" ${c.hairStyle === 'bob' ? 'selected' : ''}>Bob</option>
                                     <option value="punk" ${c.hairStyle === 'punk' ? 'selected' : ''}>Cresta Punk</option>` :
                                    `<option value="short" ${c.hairStyle === 'short' ? 'selected' : ''}>Corto</option>
                                     <option value="mohawk" ${c.hairStyle === 'mohawk' ? 'selected' : ''}>Mohawk</option>
                                     <option value="punk" ${c.hairStyle === 'punk' ? 'selected' : ''}>Cresta Punk</option>
                                     <option value="undercut" ${c.hairStyle === 'undercut' ? 'selected' : ''}>Undercut</option>
                                     <option value="bald" ${c.hairStyle === 'bald' ? 'selected' : ''}>Calvo</option>`
                                }
                            </select>
                        </label>
                        <label>Color: <input type="color" id="hairColor" value="#${c.hairColor.toString(16).padStart(6, '0')}"></label>
                    </div>
                    <div class="customizer-section">
                        <h3>Ojos</h3>
                        <label>Color: <input type="color" id="eyeColor" value="#${c.eyeColor.toString(16).padStart(6, '0')}"></label>
                    </div>
                    <div class="customizer-section">
                        <h3>Piel</h3>
                        <label>Color: <input type="color" id="skinColor" value="#${c.skinColor.toString(16).padStart(6, '0')}"></label>
                    </div>
                    ${isFemale ? `
                    <div class="customizer-section">
                        <h3>Complementos</h3>
                        <label>Accesorio:
                            <select id="accessory">
                                <option value="none" ${c.accessory === 'none' ? 'selected' : ''}>Ninguno</option>
                                <option value="necklace" ${c.accessory === 'necklace' ? 'selected' : ''}>Collar</option>
                                <option value="earrings" ${c.accessory === 'earrings' ? 'selected' : ''}>Aretes</option>
                                <option value="bow" ${c.accessory === 'bow' ? 'selected' : ''}>Lazo</option>
                            </select>
                        </label>
                    </div>
                    ` : `
                    <div class="customizer-section">
                        <h3>Vello Facial</h3>
                        <label>Estilo:
                            <select id="facialHair">
                                <option value="none" ${c.facialHair === 'none' ? 'selected' : ''}>Ninguno</option>
                                <option value="mustache" ${c.facialHair === 'mustache' ? 'selected' : ''}>Bigote</option>
                                <option value="beard" ${c.facialHair === 'beard' ? 'selected' : ''}>Barba</option>
                                <option value="goatee" ${c.facialHair === 'goatee' ? 'selected' : ''}>Perilla</option>
                                <option value="stubble" ${c.facialHair === 'stubble' ? 'selected' : ''}>Barba de 3 días</option>
                            </select>
                        </label>
                    </div>
                    `}
                    <div class="customizer-section">
                        <h3>Ropa</h3>
                        <label>Camiseta: <input type="color" id="shirtColor" value="#${c.shirtColor.toString(16).padStart(6, '0')}"></label>
                        ${isFemale ?
                            `<label>Tipo:
                                <select id="pantsType">
                                    <option value="skirt" ${c.pantsType === 'skirt' ? 'selected' : ''}>Falda</option>
                                    <option value="pants" ${c.pantsType === 'pants' ? 'selected' : ''}>Pantalones</option>
                                </select>
                            </label>` : ''}
                        <label>${isFemale ? 'Falda/Pantalón' : 'Pantalones'}: <input type="color" id="pantsColor" value="#${c.pantsColor.toString(16).padStart(6, '0')}"></label>
                        <label>Zapatos: <input type="color" id="shoeColor" value="#${c.shoeColor.toString(16).padStart(6, '0')}"></label>
                    </div>
                </div>
            </div>
            <div class="menu-buttons">
                <button id="btn-apply" class="mode-btn">Aplicar</button>
                ${this.currentPlayer === 0 ? '<button id="btn-next" class="mode-btn">Siguiente →</button>' : '<button id="btn-start-game" class="mode-btn">¡Jugar!</button>'}
            </div>
        `;
    }

    initPreview() {
        const canvas = document.getElementById('preview-canvas');
        if (!canvas) return;

        // Scene
        this.previewScene = new THREE.Scene();
        this.previewScene.background = new THREE.Color(0x2a2a3a);

        // Camera
        this.previewCamera = new THREE.PerspectiveCamera(50, 300 / 400, 0.1, 100);
        this.previewCamera.position.set(0, 1, 4);
        this.previewCamera.lookAt(0, 1, 0);

        // Renderer
        this.previewRenderer = new THREE.WebGLRenderer({ canvas, antialias: true });
        this.previewRenderer.setSize(300, 400);
        this.previewRenderer.setPixelRatio(window.devicePixelRatio);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.previewScene.add(ambientLight);

        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(5, 10, 7);
        this.previewScene.add(dirLight);

        const backLight = new THREE.DirectionalLight(0x8888ff, 0.3);
        backLight.position.set(-5, 5, -5);
        this.previewScene.add(backLight);

        // Ground plane
        const groundGeo = new THREE.CircleGeometry(1.5, 32);
        const groundMat = new THREE.MeshStandardMaterial({ color: 0x3a3a4a, roughness: 0.8 });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = 0;
        this.previewScene.add(ground);

        // Create model
        this.createPreviewModel();

        // Mouse rotation
        canvas.addEventListener('mousedown', (e) => {
            this.isDragging = true;
            this.lastMouseX = e.clientX;
        });

        canvas.addEventListener('mousemove', (e) => {
            if (this.isDragging) {
                const deltaX = e.clientX - this.lastMouseX;
                this.previewRotation += deltaX * 0.01;
                this.lastMouseX = e.clientX;
            }
        });

        canvas.addEventListener('mouseup', () => { this.isDragging = false; });
        canvas.addEventListener('mouseleave', () => { this.isDragging = false; });

        // Start animation
        this.animatePreview();
    }

    createPreviewModel() {
        if (this.previewModel) {
            this.previewScene.remove(this.previewModel.group);
            this.previewModel.dispose();
        }
        this.previewModel = new PlayerModel(1, this.previewScene, this.configs[this.currentPlayer]);
        this.previewModel.setVisible(true);
        this.previewModel.group.position.set(0, 0, 0);
    }

    animatePreview() {
        this.previewAnimId = requestAnimationFrame(() => this.animatePreview());

        if (this.previewModel) {
            this.previewModel.group.rotation.y = this.previewRotation;
            this.previewModel.animTime += 0.016;
            // Idle animation
            const breathe = Math.sin(this.previewModel.animTime * 2) * 0.008;
            if (this.previewModel.body) this.previewModel.body.position.y = 0.98 + breathe;
            if (this.previewModel.head) this.previewModel.head.position.y = 1.65 + breathe;
        }

        if (this.previewRenderer && this.previewScene && this.previewCamera) {
            this.previewRenderer.render(this.previewScene, this.previewCamera);
        }
    }

    updatePreview() {
        this.applyConfig();
        this.createPreviewModel();
        this.previewModel.group.rotation.y = this.previewRotation;
    }

    bindEvents() {
        // Apply button
        document.getElementById('btn-apply').onclick = () => {
            this.updatePreview();
        };

        // Next button
        const nextBtn = document.getElementById('btn-next');
        if (nextBtn) {
            nextBtn.onclick = () => {
                this.applyConfig();
                this.currentPlayer = 1;
                this.stopPreview();
                this.show();
            };
        }

        // Start game button
        const startBtn = document.getElementById('btn-start-game');
        if (startBtn) {
            startBtn.onclick = () => {
                this.applyConfig();
                this.stopPreview();
                this.callback(this.configs);
            };
        }

        // Gender change - update hairstyle options
        const genderSelect = document.getElementById('gender');
        if (genderSelect) {
            genderSelect.addEventListener('change', () => {
                this.applyConfig();
                // Reset hairstyle to default for new gender
                const isFemale = genderSelect.value === 'female';
                this.configs[this.currentPlayer].hairStyle = isFemale ? 'long' : 'short';
                this.stopPreview();
                this.show();
            });
        }

        // Live update on input change
        ['hairStyle', 'hairColor', 'eyeColor', 'skinColor', 'shirtColor', 'pantsColor', 'shoeColor', 'facialHair', 'accessory', 'playerName'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('input', () => this.updatePreview());
                el.addEventListener('change', () => this.updatePreview());
            }
        });
    }

    stopPreview() {
        if (this.previewAnimId) {
            cancelAnimationFrame(this.previewAnimId);
            this.previewAnimId = null;
        }
        if (this.previewModel) {
            this.previewModel.dispose();
            this.previewModel = null;
        }
        if (this.previewRenderer) {
            this.previewRenderer.dispose();
            this.previewRenderer = null;
        }
    }

    applyConfig() {
        const genderEl = document.getElementById('gender');
        const isFemale = genderEl ? genderEl.value === 'female' : this.currentPlayer === 1;

        this.configs[this.currentPlayer] = {
            name: document.getElementById('playerName').value || `Jugador ${this.currentPlayer + 1}`,
            gender: genderEl ? genderEl.value : (this.currentPlayer === 0 ? 'male' : 'female'),
            hairStyle: document.getElementById('hairStyle').value,
            hairColor: parseInt(document.getElementById('hairColor').value.slice(1), 16),
            eyeColor: parseInt(document.getElementById('eyeColor').value.slice(1), 16),
            skinColor: parseInt(document.getElementById('skinColor').value.slice(1), 16),
            shirtColor: parseInt(document.getElementById('shirtColor').value.slice(1), 16),
            pantsColor: parseInt(document.getElementById('pantsColor').value.slice(1), 16),
            pantsType: isFemale ? (document.getElementById('pantsType')?.value || 'skirt') : 'pants',
            shoeColor: parseInt(document.getElementById('shoeColor').value.slice(1), 16),
            facialHair: isFemale ? 'none' : (document.getElementById('facialHair')?.value || 'none'),
            accessory: isFemale ? (document.getElementById('accessory')?.value || 'none') : 'none'
        };
    }
}

window.PlayerModel = PlayerModel;
window.CharacterCustomizer = CharacterCustomizer;
