# This file is part mapol module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import configurator
from . import product
from . import jinja_templates

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
        configurator.QuotationCategory,
        configurator.QuotationSupplier,
        jinja_templates.JinjaTemplateMacros,
        jinja_templates.JinjaTemplate,
        product.Template,
        module='product_dynamic_configurator', type_='model')
