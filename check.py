# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import ast
from ast import literal_eval

from jinja2 import Environment
from simpleeval import FeatureNotAvailable
from trytond.pool import Pool, PoolMeta


def _validate_configurator_expression(expression):
    from .configurator import _get_expression_evaluator

    evaluator = _get_expression_evaluator({})
    tree = evaluator.parse(expression)
    for node in ast.walk(tree):
        if (isinstance(node, (ast.expr, ast.stmt, ast.keyword))
                and type(node) not in evaluator.nodes):
            raise FeatureNotAvailable(
                'Expression element is not available: %s'
                % type(node).__name__)
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id not in evaluator.functions):
            raise FeatureNotAvailable(
                'Expression function is not available: %s'
                % node.func.id)


def _validate_jinja_expression(expression):
    Environment().parse(expression)


class Cron(metaclass=PoolMeta):
    __name__ = 'ir.cron'

    @classmethod
    def _nanchecks(cls):
        checks = super()._nanchecks()[:]
        if 'product_dynamic_configurator' not in checks:
            checks.append('product_dynamic_configurator')
        return checks

    @classmethod
    def _check_product_dynamic_configurator(cls):
        pool = Pool()
        JinjaTemplate = pool.get('configurator.jinja_template')
        Property = pool.get('configurator.property')
        AttributeTemplate = pool.get('product.attribute.field_template')

        issues = []
        issue_index = {}
        validation_cache = {}

        def add_issue(record, field, expression, error):
            key = (record.__name__, field, repr(expression), error)
            issue = issue_index.get(key)
            if issue:
                issue['record_ids'].append(record.id)
                return
            issue = {
                'type': 'configurator_template',
                'model': record.__name__,
                'record_id': record.id,
                'record_ids': [record.id],
                'record_url': record.__href__,
                'record_name': record.rec_name,
                'field': field,
                'expression': expression,
                'error': error,
                }
            issue_index[key] = issue
            issues.append(issue)

        def check(record, field, expression, validator):
            try:
                hash(expression)
                cache_expression = expression
            except TypeError:
                cache_expression = repr(expression)
            cache_key = (validator, cache_expression)
            if cache_key not in validation_cache:
                try:
                    validator(expression)
                    validation_cache[cache_key] = None
                except Exception as exception:
                    validation_cache[cache_key] = str(exception)
            error = validation_cache[cache_key]
            if error:
                add_issue(record, field, expression, error)

        for template in JinjaTemplate.search([]):
            check(template, 'jinja', template.jinja,
                _validate_jinja_expression)

        for template in AttributeTemplate.search([]):
            check(template, 'jinja_template', template.jinja_template,
                _validate_jinja_expression)

        expression_fields = (
            'quantity', 'bom_quantity', 'product_attribute_value')
        expression_literals = Property.get_expression_literals()

        def is_expression_literal(expression):
            try:
                return expression in expression_literals
            except TypeError:
                return False

        for property_ in Property.search([]):
            for field in expression_fields:
                expression = getattr(property_, field)
                if expression and not is_expression_literal(expression):
                    check(property_, field, expression,
                        _validate_configurator_expression)

            if not property_.object_expression:
                continue
            try:
                expressions = literal_eval(property_.object_expression)
                if not isinstance(expressions, dict):
                    raise TypeError('Object expression must be a dictionary')
            except Exception as exception:
                add_issue(property_, 'object_expression',
                    property_.object_expression, str(exception))
                continue

            for key, expression in expressions.items():
                if is_expression_literal(expression):
                    continue
                check(property_, 'object_expression[%s]' % key, expression,
                    _validate_configurator_expression)

        return issues
