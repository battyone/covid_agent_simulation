from mesa import Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
import numpy as np

from .agents import (CoronavirusAgent, InteriorAgent,
                     CoronavirusAgentState, InteriorType, WallAgent)


class Counter:
    _count = 0

    @property
    def count(self):
        return self._count

    def add(self):
        self._count += 1

    def subtract(self):
        if self._count > 0:
            self._count -= 1


class CoronavirusModel(Model):
    def __init__(self, num_agents=10,
                 config=None, scenario='store', going_out_prob_mean=0.5,
                 num_agents_allowed_outside=None):

        self.config = config
        np.random.RandomState(config['common']['random_seed'])
        self.grid_map = self.load_gridmap(scenario)

        self.num_agents = num_agents
        self.grid = MultiGrid(self.grid_map.shape[0], self.grid_map.shape[1], False)
        self.schedule = RandomActivation(self)
        self.datacollector = DataCollector(
            model_reporters={"Infected": all_infected,
                             "Healthy": all_healthy,
                             "Recovered": all_recovered}
        )

        # select cells that will be used as possible target cells
        # for agents to head to.
        # In current "outside" cells have value 0.
        outside_cells = np.asarray(list(zip(*np.where(self.grid_map == 0))))
        self.available_target_cells =\
            outside_cells[np.random.choice(range(len(outside_cells)),
                                           size=self.config['environment'][scenario]['num_target_cells'])]
        self.counter = Counter()
        self.num_agents_allowed_outside = self.config['environment'][scenario]['num_agents_allowed']
        if num_agents_allowed_outside is not None:
            self.num_agents_allowed_outside = num_agents_allowed_outside

        self.going_out_prob_mean = going_out_prob_mean
        self.global_max_index = 0
        self.house_colors = {}
        self.infection_probabilities = self.config['common']['infection_probabilities']

        self.setup_interiors(self.grid_map)

        self.setup_agents()
        self.setup_common_area_entrance(self.config['environment'][scenario]['entrance_cells'])
        # Maybe it will look better with walls
        # if we're going to have irregular shapes, but I don't know...
        self.setup_walls()

        self.running = True
        self.datacollector.collect(self)

    def load_gridmap(self, scenario):
        path = self.config['environment'][scenario]['map_path']
        grid_map = np.load(path)

        return grid_map

    @staticmethod
    def clipped_normal_dist_prob(mu):
        prob = np.random.normal(mu, mu/2)
        prob = np.clip(prob, 0, 1)

        return prob

    def get_unique_id(self):
        unique_id = self.global_max_index
        self.global_max_index += 1

        return unique_id

    def setup_walls(self):
        """
        The idea here is that if we had 3 types of cells,
        we could draw interiors as some irregular shapes where
        agents can walk like aisles inside a store or alleys in a park.
        In that case, to improve it visually we could bound those shapes
        with "walls". Unfortunately it doesn't look that good in practice...
        """

        interiors = np.asarray(np.where(self.grid_map == 0))
        x_coors = interiors[1, :]
        y_coors = self.grid.height - interiors[0, :] - 1

        x_min = min(x_coors) - 1
        x_max = max(x_coors) + 2
        y_min = min(y_coors) - 1
        y_max = max(y_coors) + 1

        for x in range(x_min, x_max):
            w_1 = WallAgent(self.get_unique_id(), self)
            w_2 = WallAgent(self.get_unique_id(), self)

            if [x, y_max - 1] not in self.common_area_entrance:
                self.grid.place_agent(w_1, (x, y_max))
            if [x, y_min + 1] not in self.common_area_entrance:
                self.grid.place_agent(w_2, (x, y_min))

        for y in range(y_min + 1, y_max):
            w_1 = WallAgent(self.get_unique_id(), self)
            w_2 = WallAgent(self.get_unique_id(), self)
            if [x_min + 1, y] not in self.common_area_entrance:
                self.grid.place_agent(w_1, (x_min, y))
            if [x_max - 1, y] not in self.common_area_entrance:
                self.grid.place_agent(w_2, (x_max - 1, y))

    def setup_agents(self):

        home_coors = []
        for info in self.grid.coord_iter():
            contents = info[0]
            coors = info[1:]
            for object in contents:
                try:
                    if object.interior_type == InteriorType.INSIDE:
                        home_coors.append(coors)
                except AttributeError:
                    pass

        if self.num_agents > len(home_coors):
            self.num_agents = len(home_coors)
            print(f'Too many agents, they cannot fit into homes. Creating just: {self.num_agents}')

        for i in range(self.num_agents):
            ind = np.random.randint(0, len(home_coors), 1)[0]
            x, y = home_coors[ind]
            del home_coors[ind]  # make sure agents are not placed in the same cell

            home_id = [a.home_id for a in self.grid.get_cell_list_contents((x, y)) if type(a) == InteriorAgent]
            state = CoronavirusAgentState.HEALTHY
            if np.random.rand() < self.config['common']['initially_infected_population']:
                state = CoronavirusAgentState.INFECTED
            a = CoronavirusAgent(self.get_unique_id(), self, state, home_id=home_id,
                                 config=self.config,
                                 going_out_prob=self.clipped_normal_dist_prob(self.going_out_prob_mean),
                                 outside_agents_counter=self.counter)
            self.schedule.add(a)
            self.grid.place_agent(a, (x, y))
            a.set_home_address((x, y))

    def setup_interior(self, row, column, agent_id, interior_type, home_id=None, color="white", shape=None,
                       accessible=True):
            interior = InteriorAgent(agent_id, self, color, shape, interior_type, home_id, accessible)
            # origin of grid here is at left bottom, not like in opencv left top, so we need to flip y axis
            row = self.grid.height - row - 1
            self.grid.place_agent(interior, (column, row))

    def setup_interiors(self, grid_map):
        self.generate_house_colors(grid_map)
        for r in range(grid_map.shape[0]):
            for c in range(grid_map.shape[1]):
                if grid_map[r, c] == 0:
                    self.setup_interior(r, c, self.get_unique_id(), grid_map[r, c], color="#9d9dff")
                elif grid_map[r, c] == -1:
                    self.setup_interior(r, c, self.get_unique_id(), grid_map[r, c], color="white",
                                        accessible=False)
                else:
                    self.setup_interior(r, c, self.get_unique_id(), InteriorType.INSIDE, grid_map[r, c],
                                        color=self.house_colors[grid_map[r, c]])

    def setup_common_area_entrance(self, entrance_cell=[(0, 0)]):
        # It could be extracted from a list of interior patches
        # laying on the edge.
        self.common_area_entrance = entrance_cell

    def generate_house_colors(self, grid_map):
        house_num = int(grid_map.max())
        colors = [80, 130, 200]
        for i in range(1, house_num + 1):
            # self.house_colors[i] = "#%06x" % random.randint(0, 0xFFFFFF)

            # generate only grey houses
            # completely random generation leads to similar colors
            # next to each other
            self.house_colors[i] =\
                '#%02x%02x%02x' % tuple([colors[i % len(colors)]] * 3)

    def get_cell_id(self, pos):
        agents_in_cell = self.grid.get_cell_list_contents(pos)
        for a in agents_in_cell:
            if type(a) == InteriorAgent:
                return a.home_id
        raise RuntimeError('Cell without inferior agent found')

    def step(self):
        self.schedule.step()
        self.datacollector.collect(self)

    def run_model(self, n):
        for i in range(n):
            self.step()


def all_infected(model):
    return get_all_in_state(model, CoronavirusAgentState.INFECTED)\
           / len(model.schedule.agents) * 100


def all_healthy(model):
    return get_all_in_state(model, CoronavirusAgentState.HEALTHY)\
           / len(model.schedule.agents) * 100


def all_recovered(model):
    return get_all_in_state(model, CoronavirusAgentState.RECOVERED)\
          / len(model.schedule.agents) * 100


def get_all_in_state(model, state):
    return len([1 for agent in model.schedule.agents
                if type(agent) == CoronavirusAgent and agent.state == state])
