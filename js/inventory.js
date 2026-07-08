class Inventory {
    constructor(player) {
        this.player = player;
        this.slots = new Array(36).fill(null); // 36 slots (9 hotbar + 27 inventory)
        this.hotbarSize = 9;
        
        // Crafting recipes
        this.recipes = {
            [BLOCK_TYPES.PLANKS]: { 
                input: { [BLOCK_TYPES.WOOD]: 1 }, 
                output: 4 
            },
            [BLOCK_TYPES.COBBLESTONE]: {
                input: { [BLOCK_TYPES.STONE]: 1 },
                output: 2
            }
        };
        
        // Starting items
        this.initializeDefaultItems();
    }

    initializeDefaultItems() {
        this.slots[0] = { type: BLOCK_TYPES.GRASS, count: 64 };
        this.slots[1] = { type: BLOCK_TYPES.DIRT, count: 64 };
        this.slots[2] = { type: BLOCK_TYPES.STONE, count: 64 };
        this.slots[3] = { type: BLOCK_TYPES.WOOD, count: 32 };
        this.slots[4] = { type: BLOCK_TYPES.PLANKS, count: 32 };
        this.slots[5] = { type: BLOCK_TYPES.COBBLESTONE, count: 32 };
        this.slots[6] = { type: BLOCK_TYPES.SAND, count: 32 };
        this.slots[7] = { type: BLOCK_TYPES.LEAVES, count: 32 };
    }

    getSelectedSlot() {
        return this.player.selectedSlot;
    }

    getSelectedBlock() {
        const slot = this.slots[this.getSelectedSlot()];
        return slot ? slot.type : null;
    }

    hasBlock(type) {
        for (const slot of this.slots) {
            if (slot && slot.type === type && slot.count > 0) {
                return true;
            }
        }
        return false;
    }

    addBlock(type, count) {
        // Try to stack with existing
        for (const slot of this.slots) {
            if (slot && slot.type === type && slot.count < 64) {
                const canAdd = Math.min(count, 64 - slot.count);
                slot.count += canAdd;
                count -= canAdd;
                if (count <= 0) return true;
            }
        }
        
        // Find empty slot
        for (let i = 0; i < this.slots.length; i++) {
            if (!this.slots[i]) {
                this.slots[i] = { type, count: Math.min(count, 64) };
                count -= 64;
                if (count <= 0) return true;
            }
        }
        
        return count <= 0;
    }

    removeBlock(type, count) {
        for (let i = 0; i < this.slots.length; i++) {
            if (this.slots[i] && this.slots[i].type === type) {
                const canRemove = Math.min(count, this.slots[i].count);
                this.slots[i].count -= canRemove;
                count -= canRemove;
                
                if (this.slots[i].count <= 0) {
                    this.slots[i] = null;
                }
                
                if (count <= 0) return true;
            }
        }
        return count <= 0;
    }

    craft(recipe) {
        const { input, output } = this.recipes[recipe];
        
        // Check if we have all inputs
        for (const [type, count] of Object.entries(input)) {
            if (!this.hasBlock(parseInt(type), count)) {
                return false;
            }
        }
        
        // Remove inputs
        for (const [type, count] of Object.entries(input)) {
            this.removeBlock(parseInt(type), count);
        }
        
        // Add output
        return this.addBlock(parseInt(recipe), output);
    }

    getAvailableRecipes() {
        const available = [];
        for (const [output, recipe] of Object.entries(this.recipes)) {
            let canCraft = true;
            for (const [type, count] of Object.entries(recipe.input)) {
                if (!this.hasBlock(parseInt(type), count)) {
                    canCraft = false;
                    break;
                }
            }
            if (canCraft) {
                available.push({
                    output: parseInt(output),
                    input: recipe.input,
                    outputCount: recipe.output
                });
            }
        }
        return available;
    }

    swapSlots(index1, index2) {
        const temp = this.slots[index1];
        this.slots[index1] = this.slots[index2];
        this.slots[index2] = temp;
    }
}

window.Inventory = Inventory;
