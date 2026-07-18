"""Tests de Behavior Tree y pathfinding."""

import pytest

from server.bt.engine import BehaviorTree, NodeStatus, create_action_catalog
from server.engine.game_loop import GameLoop
from server.engine.navigation import Pathfinder
from server.engine.world import World


class TestBehaviorTree:
    def test_simple_action(self):
        called = {"count": 0}

        def action(params, tree):
            called["count"] += 1
            return NodeStatus.SUCCESS

        tree = BehaviorTree({"comportamiento": "Accion", "tipo": "test"}, {"test": action})
        result = tree.tick()
        assert result == NodeStatus.SUCCESS
        assert called["count"] == 1

    def test_sequence(self):
        calls = []

        def a1(params, tree):
            calls.append(1)
            return NodeStatus.SUCCESS

        def a2(params, tree):
            calls.append(2)
            return NodeStatus.SUCCESS

        tree = BehaviorTree(
            {"comportamiento": "Secuencia", "hijos": [{"comportamiento": "Accion", "tipo": "a1"}, {"comportamiento": "Accion", "tipo": "a2"}]},
            {"a1": a1, "a2": a2},
        )
        result = tree.tick()
        assert result == NodeStatus.SUCCESS
        assert calls == [1, 2]

    def test_selector(self):
        def fail(params, tree):
            return NodeStatus.FAILURE

        def ok(params, tree):
            return NodeStatus.SUCCESS

        tree = BehaviorTree(
            {"comportamiento": "Selector", "hijos": [{"comportamiento": "Accion", "tipo": "fail"}, {"comportamiento": "Accion", "tipo": "ok"}]},
            {"fail": fail, "ok": ok},
        )
        result = tree.tick()
        assert result == NodeStatus.SUCCESS

    def test_condition(self):
        tree = BehaviorTree(
            {"comportamiento": "Condicion", "variable": "vida", "comparacion": "mayor_que", "valor_comparar": 10},
            {},
            blackboard={"vida": 15},
        )
        assert tree.tick() == NodeStatus.SUCCESS


class TestPathfinder:
    def test_flat_path(self):
        world = World(seed=42, flat_mode=16)
        world.update_around(0, 0)
        pathfinder = Pathfinder(world)
        path = pathfinder.find_path(0.5, 0.5, 5.5, 0.5, 2.0)
        assert path is not None
        assert len(path) > 1
        assert path[-1]["x"] == 5
        assert path[-1]["z"] == 0

    def test_no_path_for_unloaded(self):
        world = World(seed=42)
        pathfinder = Pathfinder(world)
        path = pathfinder.find_path(0.5, 0.5, 100.5, 100.5, 30.0)
        assert path is None


class TestBtActions:
    def test_idle(self):
        world = World(seed=42, flat_mode=16)
        loop = GameLoop(world)
        catalog = create_action_catalog(loop)
        tree = BehaviorTree({"comportamiento": "Accion", "tipo": "idle"}, catalog)
        assert tree.tick() == NodeStatus.SUCCESS

    def test_gamepad_input(self):
        world = World(seed=42, flat_mode=16)
        loop = GameLoop(world)
        player = loop.add_player(2)
        catalog = create_action_catalog(loop)
        tree = BehaviorTree(
            {"comportamiento": "Accion", "tipo": "gamepad_input", "parametros": {"player_id": 2, "input": {"move": {"x": 0, "z": -1}}}},
            catalog,
        )
        assert tree.tick() == NodeStatus.SUCCESS
        assert player.input_move.z < 0

    def test_moverse_a(self):
        world = World(seed=42, flat_mode=16)
        loop = GameLoop(world)
        player = loop.add_player(2)
        player.position.x = 0.5
        player.position.z = 0.5
        catalog = create_action_catalog(loop)
        tree = BehaviorTree(
            {"comportamiento": "Accion", "tipo": "moverse_a", "parametros": {"x": 5, "z": 0}},
            catalog,
        )
        # El primer tick inicia el path y devuelve RUNNING
        result = tree.tick()
        assert result in (NodeStatus.RUNNING, NodeStatus.SUCCESS)
