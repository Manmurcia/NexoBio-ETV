import unittest

from app import app


class Etapa6RoutesTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_home_and_both_sections_render(self):
        for path in (
            '/',
            '/conocimiento-oculto/sintesis',
            '/conocimiento-oculto/informe-video',
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_unknown_section_returns_not_found(self):
        response = self.client.get('/conocimiento-oculto/no-existe')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
