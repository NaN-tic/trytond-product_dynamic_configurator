# This file is part mapol module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import configurator
from . import product

def register():
    Pool.register(
        configurator.CreatedObject,
        configurator.Template,
        configurator.Property,
        configurator.PriceCategory,
        configurator.QuotationLine,
        configurator.Design,
        configurator.DesignLine,
        configurator.DesignAttribute,
        product.Template,
        module='product_dynamic_configurator', type_='model')
