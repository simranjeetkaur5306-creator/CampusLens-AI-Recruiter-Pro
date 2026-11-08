import math

import numpy as np
from django.test import SimpleTestCase

from .services.similarity import cosine_similarity, rank_vectors, similarity_to_score


class CosineSimilarityTests(SimpleTestCase):
    def test_identical_vectors(self):
        self.assertAlmostEqual(cosine_similarity([1, 2, 3], [1, 2, 3]), 1.0)

    def test_opposite_vectors(self):
        self.assertAlmostEqual(cosine_similarity([1, 2, 3], [-1, -2, -3]), -1.0)

    def test_orthogonal_vectors(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 1]), 0.0)

    def test_known_value(self):
        # cos(45 degrees) = sqrt(2) / 2
        self.assertAlmostEqual(cosine_similarity([1, 0, 0], [1, 1, 0]), math.sqrt(2) / 2)

    def test_scale_does_not_matter(self):
        self.assertAlmostEqual(cosine_similarity([1, 2, 3], [10, 20, 30]), 1.0)

    def test_accepts_lists_tuples_and_numpy(self):
        self.assertAlmostEqual(cosine_similarity((1, 0), np.array([1.0, 0.0])), 1.0)

    def test_result_is_a_plain_float_within_range(self):
        value = cosine_similarity([0.1, 0.2, 0.3], [0.3, 0.2, 0.1])
        self.assertIsInstance(value, float)
        self.assertTrue(-1.0 <= value <= 1.0)

    def test_invalid_input_raises_value_error(self):
        bad_pairs = [
            ([1, 2], [1, 2, 3]),          # different lengths
            ([0, 0], [1, 1]),             # zero vector
            ([1, 1], [0, 0]),
            ([], []),                     # empty
            ([1, float("nan")], [1, 1]),  # NaN
            ([1, float("inf")], [1, 1]),  # infinite
            ([[1, 2]], [[1, 2]]),         # not one-dimensional
        ]
        for a, b in bad_pairs:
            with self.assertRaises(ValueError, msg=(a, b)):
                cosine_similarity(a, b)


class ScoreTests(SimpleTestCase):
    def test_score_is_similarity_as_percentage(self):
        self.assertEqual(similarity_to_score(0.5), 50.0)
        self.assertEqual(similarity_to_score(0.8123), 81.2)
        self.assertEqual(similarity_to_score(1.0), 100.0)

    def test_negative_similarity_is_shown_as_zero(self):
        self.assertEqual(similarity_to_score(-0.4), 0.0)

    def test_score_never_exceeds_100(self):
        self.assertEqual(similarity_to_score(1.0000001), 100.0)


class RankVectorsTests(SimpleTestCase):
    def test_best_match_first(self):
        query = [1, 0, 0]
        items = {"far": [0, 1, 0], "near": [1, 0.1, 0], "middle": [1, 1, 0]}
        ranked = rank_vectors(query, items)
        self.assertEqual([row[0] for row in ranked], ["near", "middle", "far"])
        similarities = [row[1] for row in ranked]
        self.assertEqual(similarities, sorted(similarities, reverse=True))

    def test_rows_contain_similarity_and_score(self):
        item_id, similarity, score = rank_vectors([1, 0], {"a": [1, 0]})[0]
        self.assertEqual((item_id, round(similarity, 6), score), ("a", 1.0, 100.0))

    def test_empty_items(self):
        self.assertEqual(rank_vectors([1, 0], {}), [])