from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval


class Template(metaclass=PoolMeta):
    __name__ = 'product.template'

    configurator_template = fields.Boolean('Template for Configurator')
    quotation_uom = fields.Many2One(
        'product.uom', "Quotation UOM",
        domain=[
            ('category', '=', Eval('default_uom_category')),
            ],
        depends=['default_uom_category'])


class Product(metaclass=PoolMeta):
    __name__ = 'product.product'
