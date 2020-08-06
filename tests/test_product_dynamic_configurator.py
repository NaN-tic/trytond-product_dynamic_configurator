# This file is part product_dynamic_configurator module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest


from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import suite as test_suite


class ProductDynamicConfiguratorTestCase(ModuleTestCase):
    'Test Product Dynamic Configurator module'
    module = 'product_dynamic_configurator'


def suite():
    suite = test_suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            ProductDynamicConfiguratorTestCase))
    return suite
