import math
from copy import copy, deepcopy

import pandas as pd
import pytest
import typeguard as tg
from numpy.random import Generator

from mesa_frames import AgentSetPandas, GridPolars, ModelDF


@tg.typechecked
class ExampleAgentSetPandas(AgentSetPandas):
    def __init__(self, model: ModelDF):
        super().__init__(model)
        self.starting_wealth = pd.Series([1, 2, 3, 4], name="wealth")

    def add_wealth(self, amount: int) -> None:
        self.agents["wealth"] += amount

    def step(self) -> None:
        self.add_wealth(1)


@pytest.fixture
def fix1_AgentSetPandas() -> ExampleAgentSetPandas:
    model = ModelDF()
    agents = ExampleAgentSetPandas(model)
    agents["wealth"] = agents.starting_wealth
    agents["age"] = [10, 20, 30, 40]
    model.agents.add(agents)
    return agents


@pytest.fixture
def fix2_AgentSetPandas() -> ExampleAgentSetPandas:
    model = ModelDF()
    agents = ExampleAgentSetPandas(model)
    agents["wealth"] = agents.starting_wealth + 10
    agents["age"] = [100, 200, 300, 400]

    return agents


@pytest.fixture
def fix1_AgentSetPandas_with_pos(fix1_AgentSetPandas) -> ExampleAgentSetPandas:
    space = GridPolars(fix1_AgentSetPandas.model, dimensions=[3, 3], capacity=2)
    fix1_AgentSetPandas.model.space = space
    space.place_agents(
        agents=fix1_AgentSetPandas["unique_id"][:2], pos=[[0, 0], [1, 1]]
    )
    return fix1_AgentSetPandas


class Test_AgentSetPandas:
    def test__init__(self):
        model = ModelDF()
        agents = ExampleAgentSetPandas(model)
        assert agents.model == model
        assert isinstance(agents.agents, pd.DataFrame)
        assert agents.agents.index.name == "unique_id"
        assert isinstance(agents._mask, pd.Series)
        assert isinstance(agents.random, Generator)
        assert agents.starting_wealth.tolist() == [1, 2, 3, 4]

    def test_add_with_unique_id(
        self,
        fix1_AgentSetPandas: ExampleAgentSetPandas,
    ):
        agents = fix1_AgentSetPandas

        # Test with a list (Sequence[Any])
        with pytest.raises(ValueError):
            agents.add([10, 5, 10])

        # Test with a dict[str, Any]
        with pytest.raises(ValueError):
            agents.add({"unique_id": [4, 5], "wealth": [5, 6], "age": [50, 60]})

    def test_add(
        self,
        fix1_AgentSetPandas: ExampleAgentSetPandas,
        fix2_AgentSetPandas: ExampleAgentSetPandas,
    ):
        agents = fix1_AgentSetPandas
        agents2 = fix2_AgentSetPandas

        # Test with a DataFrame
        result = agents.add(agents2, inplace=False)
        assert len(result.agents) == 8
        assert agents.agents.index.name == "unique_id"

        # Test with a list (Sequence[Any])
        result = agents.add([5, 10], inplace=False)
        assert len(result.agents) == 5
        assert result.agents.wealth.to_list() == [1, 2, 3, 4, 5]
        assert result.agents.age.to_list() == [10, 20, 30, 40, 10]
        assert agents.agents.index.name == "unique_id"

        # Test with a dict[str, Any]
        agents.add({"wealth": [5, 6], "age": [50, 60]})
        assert len(agents.agents) == 6
        assert agents.agents.wealth.tolist() == [1, 2, 3, 4, 5, 6]
        assert agents.agents.age.tolist() == [10, 20, 30, 40, 50, 60]
        assert agents.agents.index.name == "unique_id"

    def test_contains(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas

        # Test with a single value
        assert agents.contains(agents["unique_id"][0])
        assert not agents.contains("not an id")

        # Test with a list
        assert agents.contains(agents["unique_id"][:2]).values.tolist() == [True, True]

    def test_copy(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas
        agents.test_list = [[1, 2, 3]]

        # Since pandas have Copy-on-Write, we can't test the deep method on DFs
        # Test with deep=False
        agents2 = agents.copy(deep=False)
        agents2.test_list[0].append(4)
        assert agents.test_list[0][-1] == agents2.test_list[0][-1]

        # Test with deep=True
        agents2 = fix1_AgentSetPandas.copy(deep=True)
        agents2.test_list[0].append(4)
        assert agents.test_list[-1] != agents2.test_list[-1]

    def test_discard(self, fix1_AgentSetPandas_with_pos: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas_with_pos

        # Test with a single value
        result = agents.discard(agents["unique_id"][0], inplace=False)
        assert all(result.agents.index == agents["unique_id"][1:])
        assert all(result.pos.index == agents["unique_id"][1:])
        assert result.pos["dim_0"].to_list()[0] == 1
        assert result.pos["dim_1"].to_list()[0] == 1
        assert all(math.isnan(val) for val in result.pos["dim_0"].to_list()[1:])
        assert all(math.isnan(val) for val in result.pos["dim_1"].to_list()[1:])
        result += {"wealth": 1, "age": 10}

        # Test with a list
        result = agents.discard(agents["unique_id"][:2], inplace=False)
        assert all(result.agents.index == agents["unique_id"][2:])
        assert all(result.pos.index == agents["unique_id"][2:])
        assert all(math.isnan(val) for val in result.pos["dim_0"].to_list())
        assert all(math.isnan(val) for val in result.pos["dim_1"].to_list())
        result += pd.DataFrame({"wealth": 1, "age": 10}, index=[0])

        # Test with a pd.DataFrame
        result = agents.discard(agents["unique_id"][:2].to_frame(), inplace=False)
        assert all(result.agents.index == agents[2:])
        assert all(result.pos.index == agents[2:])
        assert all(math.isnan(val) for val in result.pos["dim_0"].to_list())
        assert all(math.isnan(val) for val in result.pos["dim_1"].to_list())

        # Test with active_agents
        agents.active_agents = agents["unique_id"][:2]
        result = agents.discard("active", inplace=False)
        assert all(result.agents.index == agents["unique_id"][2:])
        assert all(result.pos.index == agents["unique_id"][2:])
        assert all(math.isnan(val) for val in result.pos["dim_0"].to_list())
        assert all(math.isnan(val) for val in result.pos["dim_1"].to_list())
        result += pd.DataFrame({"wealth": 1, "age": 10}, index=[0])

        # Test with empty list
        result = agents.discard([], inplace=False)
        assert all(result.agents.index == agents["unique_id"])

    def test_do(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas

        # Test with no_mask
        agents.do("add_wealth", 1)
        assert agents.agents.wealth.tolist() == [2, 3, 4, 5]
        assert agents.do("add_wealth", 1, return_results=True) is None
        assert agents.agents.wealth.tolist() == [3, 4, 5, 6]

        # Test with a mask
        # note that do method does not guarantee that the agents' order does not change
        original_index_order = agents["unique_id"]
        agents.do("add_wealth", 1, mask=agents["wealth"] > 3)
        agents.agents = agents.agents.reindex(original_index_order)
        assert agents.agents.wealth.tolist() == [3, 5, 6, 7]

    def test_get(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas

        # Test with a single attribute
        assert agents.get("wealth").tolist() == [1, 2, 3, 4]

        # Test with a list of attributes
        result = agents.get(["wealth", "age"])
        assert isinstance(result, pd.DataFrame)
        assert result.columns.tolist() == ["wealth", "age"]
        assert (result.wealth == agents.agents.wealth).all()

        # Test with a single attribute and a mask
        selected = agents.select(agents["wealth"] > 1, inplace=False)
        assert selected.get("wealth", mask="active").tolist() == [2, 3, 4]

    def test_remove(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas
        result = agents.remove(agents.index[[0, 1]], inplace=False)
        assert all(result.index == agents.index[[2, 3]])
        with pytest.raises(KeyError):
            agents.remove(["not_present_agent_unique_id"])

    def test_select(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas

        # Test with default arguments. Should select all agents
        selected = agents.select(inplace=False)
        assert selected.active_agents.wealth.tolist() == agents.agents.wealth.tolist()

        # Test with a pd.Series[bool]
        mask = pd.Series([True, False, True, True])
        selected = agents.select(mask, inplace=False)
        assert all(selected.active_agents.index == agents.index[mask])

        # Test with a ListLike
        mask = agents.index[[0, 2]]
        selected = agents.select(mask, inplace=False)
        assert all(selected.active_agents.index == agents.index[[0, 2]])

        # Test with a pd.DataFrame
        mask = pd.DataFrame({"unique_id": agents.index[[0, 1]]})
        selected = agents.select(mask, inplace=False)
        assert all(selected.active_agents.index == agents.index[[0, 1]])

        # Test with filter_func
        def filter_func(agentset: AgentSetPandas) -> pd.Series:
            return agentset.agents.wealth > 1

        selected = agents.select(filter_func=filter_func, inplace=False)
        assert all(selected.active_agents.index == agents.index[[1, 2, 3]])

        # Test with n
        selected = agents.select(n=3, inplace=False)
        assert len(selected.active_agents) == 3

        # Test with n, filter_func and mask
        mask = pd.Series([True, False, True, True])
        selected = agents.select(mask, filter_func=filter_func, n=1, inplace=False)
        assert any(
            el in selected.active_agents.index.tolist() for el in agents.index[[2, 3]]
        )

    def test_set(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas

        # Test with a single attribute
        result = agents.set("wealth", 0, inplace=False)
        assert result.agents.wealth.tolist() == [0, 0, 0, 0]

        # Test with a list of attributes
        result = agents.set(["wealth", "age"], 1, inplace=False)
        assert result.agents.wealth.tolist() == [1, 1, 1, 1]
        assert result.agents.age.tolist() == [1, 1, 1, 1]

        # Test with a single attribute and a mask
        selected = agents.select(agents["wealth"] > 1, inplace=False)
        selected.set("wealth", 0, mask="active")
        assert selected.agents.wealth.tolist() == [1, 0, 0, 0]

        # Test with a dictionary
        agents.set({"wealth": 10, "age": 20})
        assert agents.agents.wealth.tolist() == [10, 10, 10, 10]
        assert agents.agents.age.tolist() == [20, 20, 20, 20]

    def test_shuffle(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas
        for _ in range(10):
            original_order = agents.agents.index.tolist()
            agents.shuffle()
            if original_order != agents.agents.index.tolist():
                return
        assert False

    def test_sort(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas
        agents.sort("wealth", ascending=False)
        assert agents.agents.wealth.tolist() == [4, 3, 2, 1]

    def test__add__(
        self,
        fix1_AgentSetPandas: ExampleAgentSetPandas,
        fix2_AgentSetPandas: ExampleAgentSetPandas,
    ):
        agents = fix1_AgentSetPandas
        agents2 = fix2_AgentSetPandas

        # Test with an AgentSetPandas and another AgentSetPandas
        agents3 = agents + agents2
        assert all(
            agents3.agents.index
            == pd.concat(
                [agents["unique_id"].to_series(), agents2["unique_id"].to_series()]
            )
        )

        # Test with an AgentSetPandas and a list (Sequence[Any])
        agents3 = agents + [5, 5]  # wealth, age
        assert agents3.agents.index.tolist()[:-1] == agents.index.to_list()
        assert len(agents3.agents) == 5
        assert agents3.agents.wealth.tolist() == [1, 2, 3, 4, 5]
        assert agents3.agents.age.tolist() == [10, 20, 30, 40, 5]

        # Test with an AgentSetPandas and a dict
        agents3 = agents + {"wealth": 5}
        assert agents3.agents.wealth.tolist() == [1, 2, 3, 4, 5]

    def test__contains__(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        # Test with a single value
        agents = fix1_AgentSetPandas
        assert agents["unique_id"][0] in agents
        assert "not_present_agent_unique_id" not in agents

    def test__copy__(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas
        agents.test_list = [[1, 2, 3]]

        # Since pandas have Copy-on-Write, we can't test the deep method on DFs
        # Test with deep=False
        agents2 = copy(agents)
        agents2.test_list[0].append(4)
        assert agents.test_list[0][-1] == agents2.test_list[0][-1]

    def test__deepcopy__(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas
        agents.test_list = [[1, 2, 3]]

        agents2 = deepcopy(agents)
        agents2.test_list[0].append(4)
        assert agents.test_list[-1] != agents2.test_list[-1]

    def test__getattr__(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas
        assert isinstance(agents.model, ModelDF)
        assert agents.wealth.tolist() == [1, 2, 3, 4]

    def test__getitem__(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas

        # Testing with a string
        assert agents["wealth"].tolist() == [1, 2, 3, 4]

        # Test with a tuple[AgentMask, str]
        assert agents[agents["unique_id"][0], "wealth"].values == 1

        # Test with a list[str]
        assert agents[["wealth", "age"]].columns.tolist() == ["wealth", "age"]

        # Testing with a tuple[AgentMask, list[str]]
        result = agents[agents["unique_id"][0], ["wealth", "age"]]
        assert result["wealth"].values.tolist() == [1]
        assert result["age"].values.tolist() == [10]

    def test__iadd__(
        self,
        fix1_AgentSetPandas: ExampleAgentSetPandas,
        fix2_AgentSetPandas: ExampleAgentSetPandas,
    ):
        agents = deepcopy(fix1_AgentSetPandas)
        agents2 = fix2_AgentSetPandas

        # Test with an AgentSetPandas and a DataFrame
        agents = deepcopy(fix1_AgentSetPandas)
        agents += agents2
        assert len(agents) == 8

        # Test with an AgentSetPandas and a list
        agents = deepcopy(fix1_AgentSetPandas)
        agents += [5, 5]  # wealth, age
        assert len(agents.agents) == 5
        assert agents.agents.wealth.tolist() == [1, 2, 3, 4, 5]
        assert agents.agents.age.tolist() == [10, 20, 30, 40, 5]

        # Test with an AgentSetPandas and a dict
        agents = deepcopy(fix1_AgentSetPandas)
        agents += {"wealth": 5}
        assert len(agents) == 5
        assert agents.agents.wealth.tolist() == [1, 2, 3, 4, 5]

    def test__iter__(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas
        for i, agent in enumerate(agents):
            assert isinstance(agent, dict)
            assert agent["unique_id"] == agents._agents.index[i]

    def test__isub__(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        # Test with an AgentSetPandas and a DataFrame
        agents = deepcopy(fix1_AgentSetPandas)
        agents -= agents.agents
        assert agents.agents.empty

    def test__len__(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas
        assert len(agents) == 4

    def test__repr__(self, fix1_AgentSetPandas):
        agents: ExampleAgentSetPandas = fix1_AgentSetPandas
        repr(agents)

    def test__reversed__(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas
        reversed_wealth = []
        for i, agent in reversed(agents):
            reversed_wealth.append(agent["wealth"])
        assert reversed_wealth == [4, 3, 2, 1]

    def test__setitem__(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas

        agents = deepcopy(agents)  # To test passing through a df later

        # Test with key=str, value=Any
        agents["wealth"] = 0
        assert agents.agents.wealth.tolist() == [0, 0, 0, 0]

        # Test with key=list[str], value=Any
        agents[["wealth", "age"]] = 1
        assert agents.agents.wealth.tolist() == [1, 1, 1, 1]
        assert agents.agents.age.tolist() == [1, 1, 1, 1]

        # Test with key=tuple, value=Any
        agents[agents["unique_id"][0], "wealth"] = 5
        assert agents.agents.wealth.tolist() == [5, 1, 1, 1]

    def test__str__(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents: ExampleAgentSetPandas = fix1_AgentSetPandas
        str(agents)

    def test__sub__(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents: ExampleAgentSetPandas = fix1_AgentSetPandas
        agents2: ExampleAgentSetPandas = agents - agents.agents
        assert agents2.agents.empty
        assert agents.agents.wealth.tolist() == [1, 2, 3, 4]

    def test_get_obj(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas
        assert agents._get_obj(inplace=True) is agents
        assert agents._get_obj(inplace=False) is not agents

    def test_agents(
        self,
        fix1_AgentSetPandas: ExampleAgentSetPandas,
        fix2_AgentSetPandas: ExampleAgentSetPandas,
    ):
        agents = fix1_AgentSetPandas
        agents2 = fix2_AgentSetPandas
        assert isinstance(agents.agents, pd.DataFrame)

        # Test agents.setter
        agents.agents = agents2.agents
        assert agents.agents.wealth.tolist() == [11, 12, 13, 14]
        assert agents.agents.age.tolist() == [100, 200, 300, 400]

    def test_active_agents(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas

        # Test with select
        agents.select(agents["wealth"] > 2, inplace=True)
        assert all(agents.active_agents.index.tolist() == agents["unique_id"][2:4])

        # Test with active_agents.setter
        agents.active_agents = agents.agents.wealth > 2
        assert all(agents.active_agents.index.tolist() == agents["unique_id"][2:4])

    def test_inactive_agents(self, fix1_AgentSetPandas: ExampleAgentSetPandas):
        agents = fix1_AgentSetPandas

        agents.select(agents["wealth"] > 2, inplace=True)
        assert all(agents.inactive_agents.index.to_list() == agents["unique_id"][:2])

    def test_pos(self, fix1_AgentSetPandas_with_pos: ExampleAgentSetPandas):
        pos = fix1_AgentSetPandas_with_pos.pos
        assert isinstance(pos, pd.DataFrame)
        assert all(pos.index.tolist() == fix1_AgentSetPandas_with_pos["unique_id"][:4])
        assert pos.columns.tolist() == ["dim_0", "dim_1"]
        assert pos["dim_0"].tolist()[:2] == [0, 1]
        assert all(math.isnan(val) for val in pos["dim_0"].tolist()[2:])
        assert pos["dim_1"].tolist()[:2] == [0, 1]
        assert all(math.isnan(val) for val in pos["dim_1"].tolist()[2:])
