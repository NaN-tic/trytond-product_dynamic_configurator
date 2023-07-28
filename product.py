import html
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

    def get_rec_name(self, name):
        emoji = ''
        if not self.active:
            emoji = '🔴'
        return html.unescape(emoji) + " " + super(Product, self).get_rec_name(name)
