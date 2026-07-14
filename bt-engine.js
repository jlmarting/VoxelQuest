// Behavior Tree Engine for VoxelQuest
// Evaluates declarative BT JSON at runtime with Blackboard variable resolution.

const NODE_STATUS = {
  SUCCESS: 'SUCCESS',
  FAILURE: 'FAILURE',
  RUNNING: 'RUNNING'
};

class BehaviorTree {
  constructor(json, catalog, relayFn, blackboard) {
    this.catalog = catalog;
    this.relayFn = relayFn;
    this.blackboard = blackboard || {};
    this.runningAction = null;
    this.lastResult = null;
    this.error = null;

    const validation = this.validate(json);
    if (!validation.valid) {
      this.error = validation.error;
      return;
    }

    this.root = this.build(json);
  }

  validate(node, depth = 0) {
    if (depth > 50) return { valid: false, error: 'Tree depth exceeds 50' };
    if (!node || typeof node !== 'object') return { valid: false, error: 'Node must be an object' };
    if (!node.comportamiento) return { valid: false, error: 'Node missing comportamiento' };

    const validTypes = ['Selector', 'Secuencia', 'Accion', 'Condicion'];
    if (!validTypes.includes(node.comportamiento)) {
      return { valid: false, error: `Invalid comportamiento: ${node.comportamiento}` };
    }

    if (node.comportamiento === 'Condicion') {
      if (!node.variable) return { valid: false, error: 'Condicion missing variable' };
      const validComps = ['menor_que', 'mayor_que', 'igual_a', 'verdadero', 'falso'];
      if (node.comparacion && !validComps.includes(node.comparacion)) {
        return { valid: false, error: `Invalid comparacion: ${node.comparacion}` };
      }
    }

    if (node.comportamiento === 'Accion') {
      if (!node.tipo) return { valid: false, error: 'Accion missing tipo' };
      if (!this.catalog[node.tipo]) {
        return { valid: false, error: `Unknown action tipo: ${node.tipo}` };
      }
    }

    if ((node.comportamiento === 'Selector' || node.comportamiento === 'Secuencia')) {
      if (!node.hijos || !Array.isArray(node.hijos) || node.hijos.length === 0) {
        return { valid: false, error: `${node.comportamiento} must have at least one hijo` };
      }
      for (const child of node.hijos) {
        const result = this.validate(child, depth + 1);
        if (!result.valid) return result;
      }
    }

    return { valid: true };
  }

  build(node) {
    switch (node.comportamiento) {
      case 'Selector': return new BTNode('Selector', node, this);
      case 'Secuencia': return new BTNode('Secuencia', node, this);
      case 'Condicion': return new BTNode('Condicion', node, this);
      case 'Accion': return new BTNode('Accion', node, this);
      default: return null;
    }
  }

  tick() {
    if (this.error) return NODE_STATUS.FAILURE;
    if (!this.root) return NODE_STATUS.FAILURE;
    this.lastResult = this.root.tick();
    return this.lastResult;
  }

  resolveParams(params) {
    if (!params) return {};
    const resolved = {};
    for (const [key, value] of Object.entries(params)) {
      if (typeof value === 'string' && value in this.blackboard) {
        resolved[key] = this.blackboard[value];
      } else {
        resolved[key] = value;
      }
    }
    return resolved;
  }

  resolveValue(variable) {
    if (variable && variable in this.blackboard) return this.blackboard[variable];
    return variable;
  }
}

class BTNode {
  constructor(type, config, tree) {
    this.type = type;
    this.config = config;
    this.tree = tree;
    this.children = null;
    this.lastRunningChild = null;

    if (type === 'Selector' || type === 'Secuencia') {
      this.children = (config.hijos || []).map(c => tree.build(c));
    }
  }

  tick() {
    switch (this.type) {
      case 'Selector': return this.tickSelector();
      case 'Secuencia': return this.tickSequence();
      case 'Condicion': return this.tickCondition();
      case 'Accion': return this.tickAction();
      default: return NODE_STATUS.FAILURE;
    }
  }

  tickSelector() {
    for (const child of this.children) {
      const result = child.tick();
      if (result === NODE_STATUS.RUNNING) return NODE_STATUS.RUNNING;
      if (result === NODE_STATUS.SUCCESS) return NODE_STATUS.SUCCESS;
    }
    return NODE_STATUS.FAILURE;
  }

  tickSequence() {
    for (const child of this.children) {
      const result = child.tick();
      if (result === NODE_STATUS.RUNNING) return NODE_STATUS.RUNNING;
      if (result === NODE_STATUS.FAILURE) return NODE_STATUS.FAILURE;
    }
    return NODE_STATUS.SUCCESS;
  }

  tickCondition() {
    const value = this.tree.resolveValue(this.config.variable);
    const compareVal = this.config.valor_comparar;
    const resolvedCompare = this.tree.resolveValue(compareVal);

    switch (this.config.comparacion) {
      case 'menor_que': return value < resolvedCompare ? NODE_STATUS.SUCCESS : NODE_STATUS.FAILURE;
      case 'mayor_que': return value > resolvedCompare ? NODE_STATUS.SUCCESS : NODE_STATUS.FAILURE;
      case 'igual_a': return value === resolvedCompare ? NODE_STATUS.SUCCESS : NODE_STATUS.FAILURE;
      case 'verdadero': return value === true ? NODE_STATUS.SUCCESS : NODE_STATUS.FAILURE;
      case 'falso': return value === false ? NODE_STATUS.SUCCESS : NODE_STATUS.FAILURE;
      default: return NODE_STATUS.FAILURE;
    }
  }

  tickAction() {
    const actionFn = this.tree.catalog[this.config.tipo];
    if (!actionFn) return NODE_STATUS.FAILURE;

    const params = this.tree.resolveParams(this.config.parametros);

    // Deduplicate RUNNING: same action + same params = still running
    const runningKey = this.config.tipo + '/' + JSON.stringify(params);
    if (this.tree.runningAction === runningKey) {
      return NODE_STATUS.RUNNING;
    }

    const result = actionFn(params, this.tree.relayFn, this.tree.blackboard);
    if (result === NODE_STATUS.RUNNING) {
      this.tree.runningAction = runningKey;
    }
    return result;
  }
}

// Schema validation for JSON trees
function validateTreeSchema(json) {
  return new BehaviorTree(json, {}, () => {}).error;
}

// Action catalog builder
function createActionCatalog() {
  let lastTarget = null;

  return {
    seguir_a_p1: (params, relay, bb) => {
      const p1x = bb.p1_x;
      const p1z = bb.p1_z;
      const selfX = bb.self_x;
      const selfZ = bb.self_z;
      if (p1x === undefined || p1z === undefined) return NODE_STATUS.FAILURE;

      const dx = selfX - p1x;
      const dz = selfZ - p1z;
      const dist = Math.hypot(dx, dz);
      const desiredDist = params.distancia || 2;

      if (dist <= desiredDist + 0.5) {
        lastTarget = null;
        return NODE_STATUS.SUCCESS;
      }

      const dirX = dx / dist;
      const dirZ = dz / dist;
      const targetX = Math.round(p1x + dirX * desiredDist);
      const targetZ = Math.round(p1z + dirZ * desiredDist);

      const targetKey = targetX + ',' + targetZ;
      if (lastTarget === targetKey) return NODE_STATUS.RUNNING;

      lastTarget = targetKey;
      relay('navigate_to', { player_id: 2, x: targetX, z: targetZ });
      return NODE_STATUS.RUNNING;
    },
    moverse_a: (params, relay) => {
      relay('navigate_to', { player_id: 2, x: params.x, z: params.z });
      return NODE_STATUS.RUNNING;
    },
    golpear: (params, relay) => {
      relay('attack', { player_id: 2, target_id: params.target_id || null });
      return NODE_STATUS.SUCCESS;
    },
    equipar: (params, relay) => {
      const slot = typeof params.item_id === 'number' ? params.item_id : 0;
      relay('select_slot', { player_id: 2, slot });
      return NODE_STATUS.SUCCESS;
    },
    idle: () => NODE_STATUS.SUCCESS
  };
}

module.exports = { BehaviorTree, NODE_STATUS, createActionCatalog, validateTreeSchema };
