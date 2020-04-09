from enum import Enum

from mesa import Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
import numpy as np

from .agents import CoronavirusAgent, InteriorAgent, CoronavirusAgentState, InteriorType


class CoronavirusModel(Model):
    def __init__(self, grid_map, num_agents=10, infection_probabilities=[0.7, 0.4]):
        self.num_agents = num_agents
        self.grid = MultiGrid(grid_map.shape[0], grid_map.shape[1], False)
        self.schedule = RandomActivation(self)
        self.datacollector = DataCollector(
            model_reporters={"Infected": all_infected,
                             "Healthy": all_healthy,
                             "Recovered": all_recovered}
        )
        self.global_max_index = 0
        self.infection_probabilities = infection_probabilities
        self.setup_interiors(grid_map)
        self.setup_agents()
        self.setup_common_area_entrance()

        self.running = True
        self.datacollector.collect(self)

    def get_unique_id(self):
        unique_id = self.global_max_index
        self.global_max_index += 1

        return unique_id

    def setup_agents(self):
        choices = [CoronavirusAgentState.HEALTHY, CoronavirusAgentState.INFECTED]
        
        home_coors = []
        for info in self.grid.coord_iter():
            contents = info[0]
            coors = info[1:]
            for object in contents:
                if object.interior_type == InteriorType.INSIDE:
                    home_coors.append(coors)

        for i in range(self.num_agents):
            a = CoronavirusAgent(self.get_unique_id(), self, self.random.choice(choices))
            self.schedule.add(a)

            ind = np.random.randint(0, len(home_coors), 1)[0]
            x, y = home_coors[ind]
            self.grid.place_agent(a, (x, y))
            a.set_home_address((x,y))

    def setup_interior(self, row, column, id, interior_type, color="yellow", shape=None):
            interior = InteriorAgent(id, self, color, shape, interior_type)
            # origin of grid here is at left bottom, not like in opencv left top, so we need to flip y axis
            row = self.grid.height - row - 1
            self.grid.place_agent(interior, (column, row))

    def setup_interiors(self, grid_map):
        for r in range(grid_map.shape[0]):
            for c in range(grid_map.shape[1]):
                if grid_map[r, c] == 0:
                    self.setup_interior(r, c, grid_map[r, c], InteriorType.OUTSIDE, color="white")
                else:
                    self.setup_interior(r, c, grid_map[r, c], InteriorType.INSIDE)

    def setup_common_area_entrance(self, entrance_cell=(0,0)):
        self.common_area_entrance = entrance_cell

    def step(self):
        self.schedule.step()
        self.datacollector.collect(self)

    def run_model(self, n):
        for i in range(n):
            self.step()


def all_infected(model):
    return get_all_in_state(model, CoronavirusAgentState.INFECTED)


def all_healthy(model):
    return get_all_in_state(model, CoronavirusAgentState.HEALTHY)


def all_recovered(model):
    return get_all_in_state(model, CoronavirusAgentState.RECOVERED)


def get_all_in_state(model, state):
    return len([1 for agent in model.schedule.agents
                if type(agent) == CoronavirusAgent and agent.state == state])
