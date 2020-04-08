from mesa.visualization.ModularVisualization import ModularServer, VisualizationElement
from .model import CoronavirusModel

from mesa.visualization.modules import CanvasGrid
from mesa.visualization.modules import ChartModule
from mesa.visualization.UserParam import UserSettableParameter

import numpy as np


class BackgroundSetter(VisualizationElement):
    def __init__(self, url):
        self.js_code = 'document.getElementsByClassName("world-grid")[0].style.background = ' \
        '"url(' + "'{}'".format(url) +')";'


def agent_portrayal(agent):
    return agent.get_portrayal()


map = np.load('map.npy')
if map is None:
    num_cells_row = 50
    num_cells_column = 50
else:
    num_cells_row = map.shape[0]
    num_cells_column = map.shape[1]

grid = CanvasGrid(agent_portrayal, num_cells_row, num_cells_column, 700, 700)

# Uncomment to use remote image as a background
# "back" object must be also included in the ModularServer parameters.
# back = BackgroundSetter("https://www.tooploox.com/cdn/academic-program.png-24378a904f32a566ccf799a2dc4bdf8928d75bbe.png")

chart = ChartModule([
    {"Label": "Infected", "Color": "#FF0000"}, 
    {"Label": "Healthy", "Color": "#00FF00"},
    {"Label": "Recovered", "Color": "#666666"}],
    data_collector_name='datacollector'
)

model_params = {
    "num_agents":
        UserSettableParameter('slider', "Number of agents", 10, 2, 200, 1,
                              description="Choose how many agents to include in the model"),
    "width": num_cells_column,
    "height": num_cells_row,
    "map": map
}

server = ModularServer(CoronavirusModel, [grid, chart], "Coronavirus Model", model_params)
server.port = 8521
