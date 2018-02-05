"""Computations on the Lie group of rigid transformations."""

import numpy as np

import geomstats.special_orthogonal_group as so_group

from geomstats.euclidean_space import EuclideanSpace
from geomstats.lie_group import LieGroup
from geomstats.special_orthogonal_group import SpecialOrthogonalGroup


class SpecialEuclideanGroup(LieGroup):

    def __init__(self, n):
        assert n > 1

        if n is not 3:
            raise NotImplementedError('Only SE(3) is implemented.')

        self.n = n
        self.dimension = int((n * (n - 1)) / 2 + n)
        super(SpecialEuclideanGroup, self).__init__(
                          dimension=self.dimension,
                          identity=np.zeros(self.dimension))
        self.rotations = SpecialOrthogonalGroup(n=n)
        self.translations = EuclideanSpace(dimension=n)

    def belongs(self, transfo):
        """
        Check that the transformation belongs to
        the special euclidean group.
        """
        if transfo.ndim == 1:
            transfo = np.expand_dims(transfo, axis=0)
        assert transfo.ndim == 2

        return transfo.shape[1] == self.dimension

    def regularize(self, point):
        """
        Regularize an element of the group SE(3),
        by extracting the rotation vector r from the input [r t]
        and using self.rotations.regularize.

        :param point: 6d vector, element in SE(3) represented as [r t].
        :returns self.regularized_point: 6d vector, element in SE(3)
        with self.regularized rotation.
        """
        assert self.belongs(point)
        if point.ndim == 1:
            point = np.expand_dims(point, axis=0)
        assert point.ndim == 2

        rotations = self.rotations
        dim_rotations = rotations.dimension

        regularized_point = np.zeros_like(point)
        rot_vec = point[:, :dim_rotations]
        regularized_point[:, :dim_rotations] = rotations.regularize(rot_vec)
        regularized_point[:, dim_rotations:] = point[:, dim_rotations:]

        return regularized_point

    def compose(self, point_1, point_2):
        """
        Compose two elements of group SE(3).

        Formula:
        point_1 . point_2 = [R1 * R2, (R1 * t2) + t1]
        where:
        R1, R2 are rotation matrices,
        t1, t2 are translation vectors.

        :param point_1, point_2: 6d vectors elements of SE(3)
        :returns composition: composition of point_1 and point_2
        """
        rotations = self.rotations
        dim_rotations = rotations.dimension

        point_1 = self.regularize(point_1)
        point_2 = self.regularize(point_2)
        assert point_1.shape == point_2.shape

        rot_vec_1 = point_1[:, :dim_rotations]
        rot_mat_1 = rotations.matrix_from_rotation_vector(rot_vec_1)

        rot_mat_1 = so_group.closest_rotation_matrix(rot_mat_1)

        rot_vec_2 = point_2[:, :dim_rotations]
        rot_mat_2 = rotations.matrix_from_rotation_vector(rot_vec_2)
        rot_mat_2 = so_group.closest_rotation_matrix(rot_mat_2)

        translation_1 = point_1[:, dim_rotations:]
        translation_2 = point_2[:, dim_rotations:]

        composition = np.zeros_like(point_1)
        composition_rot_mat = np.matmul(rot_mat_1, rot_mat_2)

        composition[:, :dim_rotations] = rotations.rotation_vector_from_matrix(
                                                          composition_rot_mat)
        composition[:, dim_rotations:] = (np.dot(translation_2,
                                                 np.transpose(
                                                        rot_mat_1,
                                                        axes=(0, 2, 1)))
                                          + translation_1)

        composition = self.regularize(composition)
        return composition

    def inverse(self, point):
        """
        Compute the group inverse in SE(3).

        Formula:
        (R, t)^{-1} = (R^{-1}, R^{-1}.(-t))

        :param point: 6d vector element in SE(3)
        :returns inverse_point: 6d vector inverse of point
        """
        rotations = self.rotations
        dim_rotations = rotations.dimension

        point = self.regularize(point)

        rot_vec = point[:, :dim_rotations]
        translation = point[:, dim_rotations:]

        inverse_point = np.zeros_like(point)
        inverse_point[:, :dim_rotations] = -rot_vec
        rot_mat = rotations.matrix_from_rotation_vector(-rot_vec)
        inverse_point[:, dim_rotations:] = np.dot(-translation,
                                                  np.transpose(
                                                        rot_mat,
                                                        axes=(0, 2, 1)))

        inverse_point = self.regularize(inverse_point)
        return inverse_point

    def jacobian_translation(self, point, left_or_right='left'):
        """
        Compute the jacobian matrix of the differential
        of the left/right translations
        from the identity to point in the Lie group SE(3).

        :param point: 6D vector element of SE(3)
        :returns jacobian: 6x6 matrix
        """
        assert self.belongs(point)
        assert left_or_right in ('left', 'right')

        dim = self.dimension
        rotations = self.rotations
        dim_rotations = rotations.dimension

        point = self.regularize(point)
        rot_vec = point[:, :dim_rotations]

        jacobian = np.zeros((point.shape[0], dim, dim))

        if left_or_right == 'left':
            jacobian_rot = self.rotations.jacobian_translation(
                                                      point=rot_vec,
                                                      left_or_right='left')
            jacobian_trans = self.rotations.matrix_from_rotation_vector(
                    rot_vec)

            jacobian[:, :dim_rotations, :dim_rotations] = jacobian_rot
            jacobian[:, dim_rotations:, dim_rotations:] = jacobian_trans

        else:
            jacobian_rot = self.rotations.jacobian_translation(
                                                      point=rot_vec,
                                                      left_or_right='right')

            inv_skew_mat = - so_group.skew_matrix_from_vector(rot_vec)
            jacobian[:, :dim_rotations, :dim_rotations] = jacobian_rot
            jacobian[:, dim_rotations:, :dim_rotations] = inv_skew_mat
            jacobian[:, dim_rotations:, dim_rotations:] = np.eye(self.n)

        assert jacobian.ndim == 3
        return jacobian

    def group_exp_from_identity(self,
                                tangent_vec):
        """
        Compute the group exponential of vector tangent_vector,
        at point base_point.

        :param tangent_vector: tangent vector of SE(3) at base_point.
        :param base_point: 6d vector element of SE(3).
        :returns group_exp_transfo: 6d vector element of SE(3).
        """
        if tangent_vec.ndim == 1:
            tangent_vec = np.expand_dims(tangent_vec, axis=0)
        assert tangent_vec.ndim == 2

        rotations = self.rotations
        dim_rotations = rotations.dimension

        rot_vec = tangent_vec[:, :dim_rotations]
        rot_vec = self.rotations.regularize(rot_vec)
        translation = tangent_vec[:, dim_rotations:]
        angle = np.linalg.norm(rot_vec)

        if np.isclose(angle, np.pi):
            rot_vec = rotations.regularize(rot_vec)

        group_exp_transfo = np.zeros_like(tangent_vec)
        group_exp_transfo[:, :dim_rotations] = rot_vec

        skew_mat = so_group.skew_matrix_from_vector(rot_vec)

        if angle == 0:
            coef_1 = 0
            coef_2 = 0
        elif np.isclose(angle, 0):
            coef_1 = 1. / 2. - angle ** 2 / 24. + angle ** 4 / 720.
            coef_2 = 1. / 6 - angle ** 2 / 120. + angle ** 4 / 5040.

        else:
            coef_1 = (1. - np.cos(angle)) / angle ** 2
            coef_2 = (angle - np.sin(angle)) / angle ** 3

        sq_skew_mat = np.matmul(skew_mat, skew_mat)
        term_1 = coef_1 * np.dot(translation,
                                 np.transpose(skew_mat, axes=(0, 2, 1)))
        term_2 = coef_2 * np.dot(translation,
                                 np.transpose(sq_skew_mat, axes=(0, 2, 1)))

        group_exp_transfo[:, dim_rotations:] = translation + term_1 + term_2

        group_exp_transfo = self.regularize(group_exp_transfo)
        return group_exp_transfo

    def group_log_from_identity(self,
                                point):
        """
        Compute the group logarithm of point point,
        from the identity.
        """
        assert self.belongs(point)
        point = self.regularize(point)

        rotations = self.rotations
        dim_rotations = rotations.dimension

        rot_vec = point[:, :dim_rotations]
        angle = np.linalg.norm(rot_vec)
        translation = point[:, dim_rotations:]

        group_log = np.zeros_like(point)
        group_log[:, :dim_rotations] = rot_vec
        skew_rot_vec = so_group.skew_matrix_from_vector(rot_vec)
        sq_skew_rot_vec = np.matmul(skew_rot_vec, skew_rot_vec)

        if angle == 0:
            coef_1 = 0
            coef_2 = 0

        elif np.isclose(angle, 0):
            coef_1 = - 0.5
            coef_2 = 0.5 - angle ** 2 / 90

        elif np.isclose(angle, np.pi):
            delta_angle = angle - np.pi
            coef_1 = - 0.5
            psi = 0.5 * angle * (- delta_angle / 2. - delta_angle ** 3 / 24.)
            coef_2 = (1 - psi) / (angle ** 2)

        else:
            coef_1 = - 0.5
            psi = 0.5 * angle * np.sin(angle) / (1 - np.cos(angle))
            coef_2 = (1 - psi) / (angle ** 2)

        term_1 = coef_1 * np.dot(translation,
                                 np.transpose(skew_rot_vec, axes=(0, 2, 1)))
        term_2 = coef_2 * np.dot(translation,
                                 np.transpose(sq_skew_rot_vec, axes=(0, 2, 1)))

        group_log[:, dim_rotations:] = translation + term_1 + term_2

        assert group_log.ndim == 2
        return group_log

    def random_uniform(self):
        """
        Generate an 6d vector element of SE(3) uniformly,
        by generating separately a rotation vector uniformly
        on the hypercube of sides [-1, 1] in the tangent space,
        and a translation in the hypercube of side [-1, 1] in
        the euclidean space.
        """
        random_rot_vec = self.rotations.random_uniform()
        random_translation = self.translations.random_uniform()

        random_transfo = np.concatenate([random_rot_vec, random_translation],
                                        axis=1)
        random_transfo = self.regularize(random_transfo)
        return random_transfo

    def exponential_matrix(self, rot_vec):
        """
        Compute the exponential of the rotation matrix
        represented by rot_vec.

        :param rot_vec: 3D rotation vector
        :returns exponential_mat: 3x3 matrix
        """

        rot_vec = self.rotations.regularize(rot_vec)
        n_rot_vecs = rot_vec.shape[0]
        angle = np.linalg.norm(rot_vec, axis=1)
        if angle.ndim == 1:
            angle = np.expand_dims(angle, axis=1)
        assert angle.shape == (n_rot_vecs, 1), angle.shape
        skew_rot_vec = so_group.skew_matrix_from_vector(rot_vec)

        coef_1 = np.empty_like(angle)
        coef_2 = np.empty_like(coef_1)

        mask_0 = np.equal(angle, 0)
        mask_0 = np.squeeze(mask_0, axis=1)
        mask_close_to_0 = np.isclose(angle, 0)
        mask_close_to_0 = np.squeeze(mask_close_to_0, axis=1)
        mask_else = ~mask_0 & ~mask_close_to_0

        if np.any(mask_close_to_0):
            coef_1[mask_close_to_0] = (1. / 2.
                                       - angle[mask_close_to_0] ** 2 / 24.)
            coef_2[mask_close_to_0] = (1. / 6.
                                       - angle[mask_close_to_0] ** 3 / 120.)

        if np.any(mask_0):
            coef_1[mask_0] = 0
            coef_2[mask_0] = 0

        if np.any(mask_else):
            coef_1[mask_else] = (angle[mask_else] ** (-2)
                                 * (1. - np.cos(angle[mask_else])))
            coef_2[mask_else] = (angle[mask_else] ** (-2)
                                 * (1. - (np.sin(angle[mask_else])
                                          / angle[mask_else])))

        term_1 = np.zeros((n_rot_vecs, self.n, self.n))
        term_2 = np.zeros_like(term_1)

        for i in range(n_rot_vecs):
            term_1[i] = np.eye(self.n) + skew_rot_vec[i] * coef_1[i]
            term_2[i] = np.matmul(skew_rot_vec[i], skew_rot_vec[i]) * coef_2[i]

        exponential_mat = term_1 + term_2
        assert exponential_mat.ndim == 3
        return exponential_mat

    def group_exponential_barycenter(self, points, weights=None):
        """
        Compute the group exponential barycenter.

        :param points: SE3 data points, Nx6 array
        :param weights: data point weights, Nx1 array
        """

        n_points = points.shape[0]
        assert n_points > 0

        if weights is None:
            weights = np.ones((n_points, 1))
        if weights.ndim == 1:
            weights = np.expand_dims(weights, axis=1)
        assert weights.shape == (n_points, 1)
        n_weights = weights.shape[0]
        assert n_points == n_weights

        dim = self.dimension
        rotations = self.rotations
        dim_rotations = rotations.dimension

        rotation_vectors = points[:, :dim_rotations]
        translations = points[:, dim_rotations:dim]
        assert rotation_vectors.shape == (n_points, dim_rotations)
        assert translations.shape == (n_points, self.n)

        mean_rotation = rotations.group_exponential_barycenter(
                                                points=rotation_vectors,
                                                weights=weights)
        mean_rotation_mat = rotations.matrix_from_rotation_vector(
                    mean_rotation)

        matrix = np.zeros([1, self.n, self.n])
        translation_aux = np.zeros([1, self.n])

        inv_rot_mats = rotations.matrix_from_rotation_vector(
                -rotation_vectors)
        # TODO(nina): this is the same mat multiplied several times
        matrix_aux = np.matmul(mean_rotation_mat, inv_rot_mats)
        assert matrix_aux.shape == (n_points, dim_rotations, dim_rotations)

        vec_aux = rotations.rotation_vector_from_matrix(matrix_aux)
        matrix_aux = self.exponential_matrix(vec_aux)
        matrix_aux = np.linalg.inv(matrix_aux)

        for i in range(n_points):
            matrix += weights[i] * matrix_aux[i]
            translation_aux += weights[i] * np.dot(np.matmul(
                                                        matrix_aux[i],
                                                        inv_rot_mats[i]),
                                                   translations[i])

        mean_translation = np.dot(translation_aux,
                                  np.transpose(np.linalg.inv(matrix),
                                               axes=(0, 2, 1)))

        exp_bar = np.zeros([1, dim])
        exp_bar[0, :dim_rotations] = mean_rotation
        exp_bar[0, dim_rotations:dim] = mean_translation

        return exp_bar
