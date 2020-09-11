from decimal import Decimal
from trytond.model import ModelView, ModelSQL, fields, sequence_ordered, tree
from trytond.pyson import Eval
from trytond.pool import PoolMeta
from trytond.transaction import Transaction
from copy import copy



class Template(metaclass=PoolMeta):
    __name__ = 'product.template'

    configurator_template = fields.Boolean('Template for Configurator')

