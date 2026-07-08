// Player model - visible character representation
class PlayerModel {
    constructor(playerId, scene) {
        this.playerId = playerId;
        this.scene = scene;
        this.group = new THREE.Group();
        this.animTime = 0;

        this.createModel();
        scene.add(this.group);
    }

    createModel() {
        const isP1 = this.playerId === 1;
        const skinColor = isP1 ? 0x4488ff : 0xff4444;
        const shirtColor = isP1 ? 0x2266cc : 0xcc2222;
        const pantsColor = isP1 ? 0x333366 : 0x663333;

        // Head
        const headGeo = new THREE.BoxGeometry(0.5, 0.5, 0.5);
        const headMat = new THREE.MeshStandardMaterial({ color: 0xffcc99, roughness: 0.8 });
        this.head = new THREE.Mesh(headGeo, headMat);
        this.head.position.y = 1.6;
        this.head.castShadow = true;
        this.group.add(this.head);

        // Eyes
        const eyeGeo = new THREE.BoxGeometry(0.08, 0.08, 0.05);
        const eyeMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
        const pupilGeo = new THREE.BoxGeometry(0.04, 0.04, 0.05);
        const pupilMat = new THREE.MeshBasicMaterial({ color: 0x000000 });

        // Left eye
        this.leftEye = new THREE.Mesh(eyeGeo, eyeMat);
        this.leftEye.position.set(-0.12, 1.65, 0.25);
        this.group.add(this.leftEye);
        this.leftPupil = new THREE.Mesh(pupilGeo, pupilMat);
        this.leftPupil.position.set(-0.12, 1.65, 0.28);
        this.group.add(this.leftPupil);

        // Right eye
        this.rightEye = new THREE.Mesh(eyeGeo, eyeMat);
        this.rightEye.position.set(0.12, 1.65, 0.25);
        this.group.add(this.rightEye);
        this.rightPupil = new THREE.Mesh(pupilGeo, pupilMat);
        this.rightPupil.position.set(0.12, 1.65, 0.28);
        this.group.add(this.rightPupil);

        // Body
        const bodyGeo = new THREE.BoxGeometry(0.5, 0.6, 0.3);
        const bodyMat = new THREE.MeshStandardMaterial({ color: shirtColor, roughness: 0.8 });
        this.body = new THREE.Mesh(bodyGeo, bodyMat);
        this.body.position.y = 1.05;
        this.body.castShadow = true;
        this.group.add(this.body);

        // Left arm
        const armGeo = new THREE.BoxGeometry(0.2, 0.6, 0.2);
        const armMat = new THREE.MeshStandardMaterial({ color: skinColor, roughness: 0.8 });
        this.leftArm = new THREE.Mesh(armGeo, armMat);
        this.leftArm.position.set(-0.35, 1.05, 0);
        this.leftArm.castShadow = true;
        this.group.add(this.leftArm);

        // Right arm
        this.rightArm = new THREE.Mesh(armGeo, armMat);
        this.rightArm.position.set(0.35, 1.05, 0);
        this.rightArm.castShadow = true;
        this.group.add(this.rightArm);

        // Left leg
        const legGeo = new THREE.BoxGeometry(0.2, 0.6, 0.2);
        const legMat = new THREE.MeshStandardMaterial({ color: pantsColor, roughness: 0.8 });
        this.leftLeg = new THREE.Mesh(legGeo, legMat);
        this.leftLeg.position.set(-0.12, 0.45, 0);
        this.leftLeg.castShadow = true;
        this.group.add(this.leftLeg);

        // Right leg
        this.rightLeg = new THREE.Mesh(legGeo, legMat);
        this.rightLeg.position.set(0.12, 0.45, 0);
        this.rightLeg.castShadow = true;
        this.group.add(this.rightLeg);

        // Name tag
        this.createNameTag(isP1 ? 'Jugador 1' : 'Jugador 2');
    }

    createNameTag(name) {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.fillRect(0, 0, 256, 64);

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 32px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(name, 128, 32);

        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
        this.nameTag = new THREE.Sprite(material);
        this.nameTag.position.y = 2.2;
        this.nameTag.scale.set(1, 0.25, 1);
        this.group.add(this.nameTag);
    }

    update(position, rotation, deltaTime, isMoving) {
        this.group.position.copy(position);
        this.group.position.y -= 0.9; // Offset to align feet

        // Rotate body to face movement direction
        this.group.rotation.y = rotation.y;

        // Walking animation
        this.animTime += deltaTime;
        if (isMoving) {
            const swing = Math.sin(this.animTime * 8) * 0.5;
            this.leftArm.rotation.x = swing;
            this.rightArm.rotation.x = -swing;
            this.leftLeg.rotation.x = -swing;
            this.rightLeg.rotation.x = swing;
        } else {
            // Idle breathing
            const breathe = Math.sin(this.animTime * 2) * 0.02;
            this.body.position.y = 1.05 + breathe;
            this.head.position.y = 1.6 + breathe;

            // Reset limbs
            this.leftArm.rotation.x *= 0.9;
            this.rightArm.rotation.x *= 0.9;
            this.leftLeg.rotation.x *= 0.9;
            this.rightLeg.rotation.x *= 0.9;
        }
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

window.PlayerModel = PlayerModel;
