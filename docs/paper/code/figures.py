"""Generate figures for paper.md
"""

from shapeflow.config import loads
from shapeflow.video import init


if __name__ == '__main__':
    # Example figure: SIMPLE-iSIMPLE shuttle
    va = init(loads("../assets/shuttle.json"))

    va.analyze()

