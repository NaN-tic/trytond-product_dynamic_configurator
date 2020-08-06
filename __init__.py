# This file is part mapol module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import configurator


def register():
    Pool.register(
        configurator.CreatedObject,
        configurator.Property,
        configurator.PriceCategory,
        configurator.QuotationLine,
        configurator.Function,
        configurator.Design,
        configurator.DesignLine,
        configurator.DesignAttribute,
        module='product_dynamic_configurator', type_='model')
