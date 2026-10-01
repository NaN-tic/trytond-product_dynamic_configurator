
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

import math
from types import SimpleNamespace

from jinja2.exceptions import TemplateSyntaxError
from simpleeval import FeatureNotAvailable
from trytond.modules.company.tests import CompanyTestMixin
from trytond.modules.product_dynamic_configurator.check import (
    _validate_configurator_expression, _validate_jinja_expression)
from trytond.modules.product_dynamic_configurator.configurator import (
    Property, _evaluate_expression)
from trytond.tests.test_tryton import ModuleTestCase


class ProductDynamicConfiguratorTestCase(CompanyTestMixin, ModuleTestCase):
    'Test ProductDynamicConfigurator module'
    module = 'product_dynamic_configurator'

    def test_expression_literals_default_empty(self):
        """Modules may define application-specific expression literals."""
        self.assertEqual(Property.get_expression_literals(), {})

    def test_evaluate_expression_with_list_comprehension(self):
        """Expressions support list comprehensions."""
        material = SimpleNamespace(name='BB_material_nom')
        product = SimpleNamespace(attributes=[
                SimpleNamespace(value='PE', attribute=material),
                SimpleNamespace(
                    value='ignored', attribute=SimpleNamespace(name='other')),
                SimpleNamespace(value='PP', attribute=material),
                ])
        names = {
            'Bobina_Estandard': SimpleNamespace(product=product),
            }

        result = _evaluate_expression(
            '",".join([x.value for x in '
            'Bobina_Estandard.product.attributes if x.attribute and '
            'x.attribute.name == "BB_material_nom"])', names)

        self.assertEqual(result, 'PE,PP')

    def test_evaluate_expression_with_locals(self):
        """Expressions can test whether an optional name is defined."""
        expression = (
            '("PR_CO_3F_TIRAS" in locals() and PR_CO_3F_TIRAS) or 1')

        self.assertEqual(_evaluate_expression(expression, {}), 1)
        self.assertEqual(_evaluate_expression(
                expression, {'PR_CO_3F_TIRAS': 3}), 3)

    def test_evaluate_expression_with_math(self):
        """Expressions have safe access to the math module."""
        self.assertEqual(_evaluate_expression(
                'math.floor(value)', {'math': math, 'value': 3.8}), 3)

    def test_validate_configurator_expression(self):
        """Configurator expression syntax and features are validated."""
        _validate_configurator_expression(
            '",".join([x.value for x in attributes if x.attribute])')
        _validate_configurator_expression(
            '("optional" in locals() and optional) or 1')

        with self.assertRaises(SyntaxError):
            _validate_configurator_expression('value +')
        with self.assertRaisesRegex(
                FeatureNotAvailable, 'Expression function is not available'):
            _validate_configurator_expression('unknown_function(value)')

    def test_validate_jinja_expression(self):
        """Jinja template syntax is validated."""
        _validate_jinja_expression('{{ value }}')

        with self.assertRaises(TemplateSyntaxError):
            _validate_jinja_expression('{% if value %}')


del ModuleTestCase
