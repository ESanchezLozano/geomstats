"""
Plot a geodesic of SO(3) equipped
with its left-invariant canonical METRIC.
"""

import matplotlib.pyplot as plt
import numpy as np
import os

import geomstats.visualization as visualization

from geomstats.special_orthogonal_group import SpecialOrthogonalGroup

SO3_GROUP = SpecialOrthogonalGroup(n=3)
METRIC = SO3_GROUP.bi_invariant_metric


def main():
    initial_point = SO3_GROUP.identity
    initial_tangent_vec = [0.5, 0.5, 0.8]
    geodesic = METRIC.geodesic(initial_point=initial_point,
                               initial_tangent_vec=initial_tangent_vec)

    n_steps = 10
    t = np.linspace(0, 1, n_steps)

    points = geodesic(t)
    visualization.plot(points, space='SO3_GROUP')
    plt.show()


if __name__ == "__main__":
    if os.environ['GEOMSTATS_BACKEND'] == 'tensorflow':
        print('Examples with visualizations are only implemented '
              'with numpy backend.\n'
              'To change backend, change '
              'the environmental variable GEOMSTATS_BACKEND.')
    else:
        main()
