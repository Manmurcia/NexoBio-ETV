import unittest
from unittest.mock import patch

from olap import consultas as C


class ConsultaValidationTests(unittest.TestCase):
    def test_rejects_unknown_grouping_level_before_opening_database(self):
        with patch.object(C, "_con") as open_database:
            with self.assertRaisesRegex(ValueError, "Nivel.*desconocido"):
                C._consulta_sql(["regoin"], "casos")

        open_database.assert_not_called()

    def test_rejects_repeated_grouping_level(self):
        with patch.object(C, "_con") as open_database:
            with self.assertRaisesRegex(ValueError, "repetidos"):
                C._consulta_sql(["region", "region"], "casos")

        open_database.assert_not_called()

    def test_rejects_unknown_measure_before_opening_database(self):
        with patch.object(C, "_con") as open_database:
            with self.assertRaisesRegex(ValueError, "Medida.*desconocida"):
                C._consulta_sql([], "casoz")

        open_database.assert_not_called()

    def test_rejects_unknown_filter_level_before_opening_database(self):
        with patch.object(C, "_con") as open_database:
            with self.assertRaisesRegex(ValueError, "Filtros.*desconocidos"):
                C._donde({"regoin": ["Andina"]}, False, None)

        open_database.assert_not_called()

    def test_rejects_unknown_level_in_value_lookup_before_opening_database(self):
        with patch.object(C, "_con") as open_database:
            with self.assertRaisesRegex(ValueError, "Nivel.*desconocido"):
                C.valores_nivel("regoin")

        open_database.assert_not_called()


if __name__ == "__main__":
    unittest.main()
