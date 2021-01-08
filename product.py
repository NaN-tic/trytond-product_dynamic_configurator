from trytond.model import fields
from trytond.pool import PoolMeta


class Template(metaclass=PoolMeta):
    __name__ = 'product.template'

    configurator_template = fields.Boolean('Template for Configurator')
