import unittest

from fleeting import utils

class UtilsTests(unittest.TestCase):
    def test_ensure_env_vars_raises_exception(self):
        msg = 'environment variable QWOP is not defined'
        with self.assertRaisesRegexp(KeyError, msg):
            utils.ensure_env_vars(['QWOP'])
