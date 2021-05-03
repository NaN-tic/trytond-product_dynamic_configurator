from decimal import Decimal
from trytond.model import (Workflow, ModelView, ModelSQL, fields,
    sequence_ordered, tree)
from trytond.pyson import Eval, Not, If, Bool
from trytond.pool import Pool, PoolMeta
from trytond.config import config
from trytond.transaction import Transaction
from trytond.modules.company.model import (
    employee_field, set_employee, reset_employee)
from copy import copy
import math

try:
    from jinja2 import Template as Jinja2Template
    jinja2_loaded = True
except ImportError:
    jinja2_loaded = False

price_digits = (16, config.getint('product', 'price_decimal', default=4))
_ZERO = Decimal(0)

TYPE = [
    (None, ''),
    ('bom', 'BoM'),
    ('product', 'Product'),
    ('purchase_product', 'Purchase Product'),
    ('group', 'Group'),
    ('match', 'Match'),
    # ('operation', 'Operation'),
    ('options', 'Options'),
    ('number', 'Number'),
    ('text', 'Text'),
    ('function', 'Function'),
    ('attribute', 'Product Attribute'),
]


class PriceCategory(ModelSQL, ModelView):
    """ Price Category """
    __name__ = 'configurator.property.price_category'

    name = fields.Char('Name')


class QuotationCategory(ModelSQL, ModelView):
    """ Price Category """
    __name__ = 'configurator.property.quotation_category'

    name = fields.Char('Name')
    type_ = fields.Selection([('goods', 'Goods'),
        ('works', 'Works'), ('other', 'Other')], 'Type')
    party = fields.Many2One('party.party', 'Default Supplier')


class Template(metaclass=PoolMeta):
    __name__ = 'product.template'

    def get_purchase_context(self):
        return {}


class Property(tree(separator=' / '), sequence_ordered(), ModelSQL, ModelView):
    """ Property """
    __name__ = 'configurator.property'
    # Code may not contain spaces or special characters (usable in formulas)
    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)
    type = fields.Selection(TYPE, 'Type', required=True)
    user_input = fields.Boolean('User Input',
        states={
            'invisible': Not(Eval('type').in_(['number', 'options', 'text'])),
        })
    template = fields.Boolean('Template',
        states={
            'invisible': Not(Eval('type').in_(['bom', 'purchase_product']))
        })
    product = fields.Many2One('product.product', 'Product',
        states={
            'invisible': Eval('type') != 'product',
        }
    )
    uom = fields.Many2One('product.uom', 'UoM', states={
        'invisible': Eval('type').in_(['function', 'text', 'number',
            'options', 'group', 'attribute']),
        'required': Eval('type').in_(['bom', 'product', 'purchase_product'])
        },
        domain=[If(Bool(Eval('product_uom_category')),
            ('category', '=', Eval('product_uom_category', -1)), ())],
        depends=['product_uom_category', 'type'])
    childs = fields.One2Many('configurator.property', 'parent', 'childs',
        states={
            'invisible': Not(Eval('type').in_(['bom', 'purchase_product',
                'options', 'group', 'match']))
        })
    parent = fields.Many2One('configurator.property', 'Parent', select=True,
        ondelete='CASCADE')
    quantity = fields.Char('Quantity', states={
        'invisible': Not(Eval('type').in_(['purchase_product',
            'bom', 'product', 'function', 'match'])),
        'required': Eval('type').in_(['bom', 'product', 'purchase_product'])
    }, depends=['type'])
    price_category = fields.Many2One('configurator.property.price_category',
        'Price Category',
        states={
            'invisible': Eval('type').in_(['function', 'text', 'number',
                'attribute', 'group']),
        },)
    object_expression = fields.Char('Object Expression',
        states={
            'invisible': Not(Eval('type').in_(['purchase_product', 'bom']))
        }
    )
    work_center_category = fields.Many2One('production.work_center.category',
        'Work Center Category', states={
            'invisible': Eval('type') != 'operation',
            'required': Eval('type').in_(['operation'])
        }, depends=['type'])
    operation_type = fields.Many2One('production.operation.type',
        'Operation Type', states={
            'invisible': Eval('type') != 'operation',
            'required': Eval('type').in_(['operation'])
        }, depends=['type'])

    attribute_set = fields.Many2One('product.attribute.set', 'Attribute Set',
        states={
            'invisible': Eval('type') != 'attribute',
            'required': Eval('type') == 'attribute',
        })
    product_attribute = fields.Many2One('product.attribute',
        'Product Attribute',
        domain=[('sets', '=', Eval('attribute_set'))],
        depends=['attribute_set'],
        states={
            'invisible': Eval('type') != 'attribute',
            'required': Eval('type') == 'attribute',
        })
    attribute_search_op = fields.Char('Operator', states={
        'invisible': Eval('type') != 'attribute',
    })
    product_attribute_value = fields.Char('Product Attribute Value', states={
        'invisible': Eval('type') != 'attribute',
        'required': Eval('type') == 'attribute',
    })
    product_template = fields.Many2One('product.template', 'Product Template',
        domain=[('configurator_template', '=', True)],
        states={
            'invisible': Not(Eval('type').in_(['purchase_product', 'bom'])),
            'required': Eval('type').in_(['purchase_product', 'bom'])
        }, depends=['type']
    )
    product_uom_category = fields.Function(
        fields.Many2One('product.uom.category', 'Product Uom Category'),
        'on_change_with_product_uom_category')

    quotation_category = fields.Many2One(
        'configurator.property.quotation_category', 'Quoatation Category',
        states={
            'invisible': Eval('type').in_(['function', 'text', 'number',
                'attribute', 'group']),
        },)
    code_template = fields.Text('Code Template',
        states={
            'invisible': Not(Eval('type').in_(['purchase_product', 'bom']))
        })
    name_template = fields.Text('Name Template',
        states={
            'invisible': Not(Eval('type').in_(['purchase_product', 'bom']))
        }, translate=True)

    @staticmethod
    def default_sequence():
        return 99

    def get_rec_name(self, name):
        res = ''
        parent = self.get_parent()
        if self.code:
            res = '[%s] ' % self.code
        if self.code and parent and parent.parent:
            res = '[%s/%s] ' % (parent.code, self.code)
        res += self.name
        return res

    def get_full_code(self):
        res = ''
        parent = self.get_parent()
        if self.code:
            res = '%s' % self.code
        if self.code and parent and parent.parent:
            res = '%s_%s ' % (parent.code, self.code)
        return res

    def render_expression_record(self, expression, record):
        template = Jinja2Template(expression)
        return template.render(record)

    @fields.depends('user_input', 'quantity', 'uom', 'template', 'product',
        'price_category', 'object_expression', 'attribute_set',
        'work_center_category', 'operation_type', 'product_attribute',
        'product_attribute_value', 'product_template')
    def on_change_type(self):
        self.quantity = None
        self.uom = None
        self.template = None
        self.product = None
        self.price_category = None
        self.object_expression = None
        self.attribute_set = None
        self.work_center_category = None
        self.operation_type = None
        self.product_attribute = None
        self.product_attribute_value = None
        self.product_template = None

    @fields.depends('product')
    def on_change_product(self):
        if self.product:
            self.uom = self.product.default_uom

    @fields.depends('product_template')
    def on_change_product_template(self):
        if self.product_template:
            self.uom = self.product_template.default_uom

    @fields.depends('product', 'product_template')
    def on_change_with_product_uom_category(self, name=None):
        if self.product:
            return self.product.default_uom_category.id
        if self.product_template:
            return self.product_template.default_uom_category.id

    def get_parent(self):
        if self.type == 'bom':
            return self
        if not self.parent:
            return self
        return self.parent.get_parent()

    def compute_attributes(self, design, attributes=None):
        Attribute = Pool().get('configurator.design.attribute')
        if not attributes:
            attributes = {}
        res = []
        attribute = attributes.get(self.code)
        if self.user_input:
            if not attribute:
                attribute = Attribute()
                attribute.design = design
                attribute.property = self
                attribute.property_type = \
                    attribute.on_change_with_property_type()
                if attribute.property_type == 'options':
                    attribute.property_options = \
                        attribute.on_change_with_property_options()
                attribute.option = None
                attributes[self.code] = attribute
            res.append(attribute)

            if self.type == 'options' and attribute.option:
                res += attribute.option.compute_attributes(design,
                    attributes)
        else:
            for child in self.childs:
                res += child.compute_attributes(design, attributes)
        return res

    @staticmethod
    def _create_objects(objects):
        pool = Pool()
        design = Transaction().context.get('design')
        if not design:
            return

        CreatedObject = pool.get('configurator.object')
        to_create = [design.create_object(obj) for obj in objects]
        if to_create:
            CreatedObject.save(to_create)

    def evaluate(self, expression, values):
        custom_locals = copy(locals())
        custom_locals['math'] = math
        for prop, attr in values.items():
            if isinstance(attr, dict):
                continue
            if prop.type == 'function':
                custom_locals[prop.code] = attr
            else:
                custom_locals[prop.code] = attr.number or attr.option
        try:
            code = compile(expression, "<string>", "eval")
            return eval(code, custom_locals)
        except BaseException:
            pass
            # raise UserError(gettext(
            #     'product_dynamic_configurator.msg_expression_error',
            #     property=self.name, expression=self.quantity,
            #     invalid=str(e)))

    def create_prices(self, design, values):
        created_obj = {}
        if self.type not in ('options', 'match'):
            for prop in self.childs:
                parent = prop.get_parent()
                val = values
                if parent in values:
                    val = values[parent]
                res = prop.create_prices(design, val)
                if res is None:
                    continue
                created_obj.update(res)
        parent = self.get_parent()
        val = values
        if parent in values:
            val = values[parent]
        res = getattr(self, 'get_%s' % self.type)(
            design, val, created_obj)
        if res is None:
            return created_obj
        created_obj.update(res)
        return created_obj

    def get_match_domain(self, design):
        return []

    def get_match(self, design, values, created_obj):
        pool = Pool()
        Product = pool.get('product.product')
        BomInput = pool.get('production.bom.input')
        Uom = pool.get('product.uom')
        domain = []

        suppliers = dict((x.category, x.supplier) for x in design.suppliers)
        if self.quotation_category:
            domain += [('product_suppliers.party', '=',
                suppliers[self.quotation_category].id)]

        for child in self.childs:
            attribute = child.product_attribute
            value = self.evaluate(child.product_attribute_value, values)

            if isinstance(value, Product):
                val = None
                for attr in value.attributes:
                    if attr.attribute == attribute:
                        val = attr.value
                        break
                if not val:
                    return {self: (None, [])}
                value = val
            op = child.attribute_search_op or '='
            type_ = attribute.type_
            domain += [('template.attribute_set', '=', child.attribute_set.id),
                ('attributes.attribute.id', '=', attribute.id),
                ('attributes.value_%s' % type_, op, value),
                ]
        domain += self.get_match_domain(design)
        products = Product.search(domain)
        if not products:
            return {self: (None, [])}

        product = None
        for prod in products:
            if len(prod.attributes) > len(self.childs):
                continue
            product = prod

        if not product:
            return {self: (None, [])}

        quantity = self.evaluate(self.quantity, values)
        quantity = Uom.compute_qty(self.uom, quantity,
             product.default_uom)
        bom_input = BomInput()
        bom_input.product = product
        bom_input.on_change_product()
        bom_input.quantity = quantity
        return {self: (bom_input, [])}

    def get_number(self, design, values, created_obj):
        pass

    def get_text(self, design, values, created_obj):
        pass

    def get_function(self, design, values, created_obj):
        value = self.evaluate(self.quantity, values),
        return {self: (value, [])}

    def get_options(self, design, values, created_obj):
        attribute = values.get(self)
        if attribute and attribute.option:
            res = attribute.option.create_prices(design, values)
            option = res.get(attribute.option, None)
            if option:
                res.update({self: (option[0], [])})
                return res
        return {self: (None, [])}

    def get_attribute(self, design, values, created_obj):
        pool = Pool()
        ProductAttribute = pool.get('product.product.attribute')
        product_attribute = ProductAttribute()
        product_attribute.attribute = self.product_attribute
        product_attribute.value = self.product_attribute_value
        return {self: (product_attribute, [])}

    def get_operation(self, design, values, created_obj):
        pool = Pool()
        Uom = pool.get('product.uom')
        Operation = pool.get('production.route.operation')
        operation = Operation()
        operation.work_center_category = self.work_center_category
        operation.operation_type = self.operation_type
        operation.time = 1  # TODO: hardcoded
        operation.time_uom = 9  # TODO: hardcoded
        operation.quantity_uom = self.uom
        operation.quantity = Uom.compute_qty(self.uom,
            self.evaluate(self.quantity, values), self.uom)
        operation.calculation = 'standard'
        return {self: (operation, [])}

    def get_product_attribute_typed(self, prop, value):
        if prop.product_attribute.type_ == 'boolean':
            return ('bool', bool(value))
        elif prop.product_attribute.type_ == 'integer':
            return('integer', int(value))
        elif prop.product_attribute.type_ == 'char':
            return ('char', str(value))
        elif prop.product_attribute.type_ == 'numeric':
            return ('numeric', Decimal(str(value)))
        elif prop.product_attribute.type_ == 'date':
            raise 'Not Implemented'
        elif prop.product_attribute.type_ == 'datetime':
            raise 'Not Implemented'
        elif prop.product_attribute.type_ == 'selection':
            raise 'Not Implemented'

    def get_product_template_object_copy(self, template):
        Template = Pool().get('product.template')
        ntemplate = Template()
        ntemplate.attribute_set = None
        ntemplate.attributes = tuple()
        for f in template._fields:
            setattr(ntemplate, f, getattr(template, f))
        ntemplate.configurator_template = False
        ntemplate.categories_all = None
        ntemplate.products = []
        return ntemplate

    def get_product_product_object_copy(self, product):
        Product = Pool().get('product.product')
        nproduct = Product()
        for f in product._fields:
            if not hasattr(nproduct, f):
                continue
            setattr(nproduct, f, getattr(product, f))
        nproduct.attributes = tuple()
        nproduct.account_category = None
        nproduct.template = None
        return nproduct

    def get_field_name_from_attributes(self, attribute_set, name, record):
        BomInput = Pool().get('production.bom.input')
        values = {}
        for key, val in record.items():
            if isinstance(val, BomInput):
                values[key] = val.product.name
            else:
                values[key] = val
        name_field = getattr(attribute_set, name)
        return attribute_set.render_expression_record(name_field, values)

    def get_purchase_product(self, design, values, created_obj):
        pool = Pool()
        BomInput = pool.get('production.bom.input')
        Uom = pool.get('product.uom')
        Product = pool.get('product.product')
        Attribute = pool.get('product.product.attribute')

        if not self.product_template:
            return
        template = self.get_product_template_object_copy(self.product_template)
        template.name = self.name + "(" + design.name + ")"
        template.list_price = 0
        product = self.get_product_product_object_copy(
            self.product_template.products[0])
        product.template = template
        product.default_uom = self.uom
        product.list_price = 0
        product.code = design.code
        if not hasattr(product, 'attributes'):
            product.attributes = tuple()
        for prop, child_res in created_obj.items():
            child_res = child_res[0]
            if prop.type == 'attribute':
                template.attribute_set = prop.attribute_set
                type_, value = self.get_product_attribute_typed(prop,
                    self.evaluate(prop.product_attribute_value, values))
                setattr(child_res, 'value_' + type_, value)
                setattr(child_res, 'value', value)
                product.attributes += (child_res,)
            elif prop.type == 'match' and child_res:
                for attribute in child_res.product.attributes:
                    attr = Attribute()
                    attr.template = template
                    attr.attribute = attribute.attribute
                    attr.attribute_type = attribute.attribute_type
                    setattr(attr, 'value_' + attribute.attribute_type,
                        attribute.value)
                    product.attributes += (attr,)

        if self.object_expression:
            expressions = eval(self.object_expression)
            for key, value in expressions.items():
                val = self.evaluate(value, values)
                setattr(template, key, val)

        template.products = (product,)
        if template.attribute_set:
            template._update_attributes_values()
        template.products = None

        exists_product = Product.search([('code', '=', product.code)])
        if exists_product:
            product = exists_product[0]

        bom_input = BomInput()
        bom_input.product = product
        bom_input.on_change_product()
        bom_input.quantity = Uom.compute_qty(self.uom,
            self.evaluate(self.quantity, values), product.default_uom)

        # Calculate cost_price for purchase_product
        cost_price = 0
        suppliers = dict((x.category, x.supplier) for x in design.suppliers)
        goods_supplier = None
        for category, supplier in suppliers.items():
            if category.type_ == 'goods':
                goods_supplier = supplier
                break

        if not goods_supplier:
            return {self: (bom_input, [])}

        ProductSupplier = pool.get('purchase.product_supplier')
        Price = pool.get('purchase.product_supplier.price')
        product_supplier = ProductSupplier()
        product_supplier.party = goods_supplier
        product_supplier.on_change_party()
        product_supplier.prices = ()
        design_qty = self.evaluate(design.template.quantity, values)
        for quote in design.prices:
            cost_price = 0
            qty = Uom.compute_qty(design.template.uom, design_qty,
                design.quotation_uom)
            for prop, v in created_obj.items():
                v = v[0]
                if not v or prop.type not in ('product', 'match', 'bom'):
                    continue
                parent = prop.get_parent()
                if isinstance(v, BomInput):
                    quantity = v.quantity * quote.quantity
                    product = v.product
                elif isinstance(v, Product):
                    quantity = prop.evaluate(prop.quantity,
                        design.as_dict()[parent])
                    quantity = quantity * quote.quantity
                    product = v
                supplier = None
                if prop.quotation_category:
                    supplier = suppliers[prop.quotation_category]
                quantity = bom_input.quantity * quantity
                cost_price += quote.get_unit_price(product,
                    quantity, prop.uom, supplier)
            if cost_price:
                price = Price()
                price.quantity = ((quote.quantity / qty) * bom_input.quantity)
                price.unit_price = cost_price
                product_supplier.prices += (price,)

        template.product_suppliers = [product_supplier]
        return {self: (bom_input, [])}

    def get_group(self, design, values, created_obj):
        res = {}
        for child in self.childs:
            r = getattr(child, 'get_%s' % child.type)(
                design, values, created_obj)
            if not r:
                continue
            res.update(r)
        return res

    def get_product(self, design, values, created_obj):
        pool = Pool()
        BomInput = pool.get('production.bom.input')
        Uom = pool.get('product.uom')

        if not self.product:
            return

        attribute = None
        if self.parent and self.parent.type == 'options':
            attribute = values.get(self.parent)
        product = self.product
        if attribute and attribute.number:
            quantity = attribute.number
        else:
            quantity = self.evaluate(self.quantity, values)

        quantity = Uom.compute_qty(self.uom, quantity, product.default_uom)
        bom_input = BomInput()
        bom_input.product = product
        bom_input.on_change_product()
        bom_input.quantity = quantity
        return {self: (bom_input, [])}

    def get_bom(self, design, values, created_obj):
        pool = Pool()
        Product = pool.get('product.product')
        Bom = pool.get('production.bom')
        BomInput = pool.get('production.bom.input')
        BomOutput = pool.get('production.bom.output')
        ProductBom = pool.get('product.product-production.bom')
        Operation = pool.get('production.route.operation')
        Route = pool.get('production.route')
        Uom = pool.get('product.uom')
        Attribute = pool.get('product.product.attribute')

        def create_bom_input(property_):
            if property_.type == 'purchase_product':
                return False
            if property_.parent:
                return create_bom_input(property_.parent)
            return True

        bom, = Bom.search([('name', '=', self.name)]) or [None]
        if bom:
            return {self: bom}

        res_obj = []
        bom = Bom()
        bom.name = self.name + " ( " + design.code + " ) "
        bom.active = True
        bom.inputs = ()
        bom.outputs = ()
        operations_route = ()
        for child, child_res in created_obj.items():
            if child.parent != self:
                continue
            child_res, _ = child_res
            if isinstance(child_res, BomInput):
                # TODO: needed to make purchase_product a composite of products
                # then we need to avoid on bom.
                if child_res.product.template.type == 'service':
                    continue
                if child.type == 'product':
                    bom.inputs += (child_res,)
                elif child.type == 'purchase_product':
                    bom.inputs += (child_res,)
                elif child.type == 'options':
                    bom.inputs += (child_res,)

            elif isinstance(child_res, Bom):
                bom_input = BomInput()
                child_output, = child_res.outputs
                bom_input.product = child_output.product
                bom_input.on_change_product()
                bom_input.quantity = child_output.quantity
                bom.inputs += (bom_input,)
            elif isinstance(child_res, Operation):
                operations_route += (child_res,)

        route = None
        if operations_route:
            route = Route()
            route.uom = operations_route[0].quantity_uom
            route.name = design.name + "(" + design.code + ")"
            route.operations = operations_route
            res_obj.append(route)

        template = None
        if not self.product_template:
            return
        template = self.get_product_template_object_copy(self.product_template)
        template.name = self.name + "(" + design.code + ")"
        product = self.get_product_product_object_copy(
            self.product_template.products[0])
        product.template = template
        product.default_uom = self.uom
        product.list_price = 0
        product.code = self.code + "(" + design.code + ")"
        if not hasattr(template, 'attributes'):
            template.attributes = tuple()
        for prop, child_res in created_obj.items():
            child_res = child_res[0]
            if prop.type == 'attribute':
                template.attribute_set = prop.attribute_sets
                type_, value = self.get_product_attribute_typed(prop,
                    self.evaluate(prop.product_attribute_value, values))
                setattr(child_res, 'value_' + type_, value)
                setattr(child_res, 'value', value)
                template.attributes += (child_res,)
            elif prop.type == 'match' and child_res:
                for attribute in child_res.product.attributes:
                    attr = Attribute()
                    attr.template = template
                    attr.attribute = attribute.attribute
                    attr.attribute_type = attribute.attribute_type
                    setattr(attr, 'value_' + attribute.attribute_type,
                        attribute.value)
                    product.attributes += (attr,)

        template._update_attributes_values()
        exists_product = Product.search([('code', '=', product.code)])
        if exists_product:
            product = exists_product[0]
        output = BomOutput()
        output.bom = bom
        output.product = product
        output.uom = product.default_uom
        output.quantity = Uom.compute_qty(self.uom,
            self.evaluate(self.quantity, values), product.default_uom)
        bom.outputs += (output,)
        bom.name = template.name
        product_bom = ProductBom()
        product_bom.product = product
        product_bom.bom = bom
        if route:
            product_bom.route = route
        res_obj.append(product_bom)
        exists_bom = Bom.search([('name', '=', bom.name)])
        if exists_bom:
            return {self: (exists_bom[0], res_obj)}
        return {self: (bom, res_obj)}

    def get_ratio_for_prices(self, values, ratio):
        if not self.parent:
            return ratio

        parent = self.parent
        ratio_parent = self.evaluate(parent.quantity or '1.0', values) or 1.0
        return parent.get_ratio_for_prices(values,
            (ratio or 1.0) * ratio_parent)

    def create_design_line(self, quantity, uom, unit_price, quote):
        DesignLine = Pool().get('configurator.design.line')
        Uom = Pool().get('product.uom')

        quantity = Uom.compute_qty(self.uom, quantity, uom, round=False)
        dl = DesignLine()
        dl.quotation = quote
        dl.quantity = quantity
        dl.uom = uom
        dl.unit_price = unit_price
        return dl

    def get_quotation_categories(self):
        categories = []
        if not self.childs:
            if self.quotation_category:
                return [self.quotation_category]
            return []

        for child in self.childs:
            if child.quotation_category:
                categories += [child.quotation_category]
            categories += child.get_quotation_categories()
        return categories


class CreatedObject(ModelSQL, ModelView):
    """ Created Object """
    __name__ = 'configurator.object'

    design = fields.Many2One('configurator.design', 'Design', required=True,
        ondelete='CASCADE')
    object = fields.Reference('Object', selection='get_object', required=True)

    @classmethod
    def _get_created_object_type(cls):
        """Return list of Model names for object Reference"""
        return [
            'production.bom',
            'production.bom.input',
            'production.bom.output',
            'product.product',
            'production.route',
            'product.product-production.bom',
        ]

    @classmethod
    def get_object(cls):
        IrModel = Pool().get('ir.model')
        models = cls._get_created_object_type()
        models = IrModel.search([
            ('model', 'in', models),
        ])
        return [(None, '')] + [(m.model, m.name) for m in models]

    def get_rec_name(self, name):
        return self.object and self.object.rec_name


READONLY_STATE = {
    'readonly': (Eval('state') != 'draft'),
    }

STATES = [('draft', 'draft'), ('done', 'Done'), ('cancel', 'Cancel')]


class Design(Workflow, ModelSQL, ModelView):
    'Design'
    __name__ = 'configurator.design'

    company = fields.Many2One('company.company', 'Company', required=True,
        states={
            'readonly': (Eval('state') != 'draft'),
            },
        domain=[
            ('id', If(Eval('context', {}).contains('company'), '=', '!='),
                Eval('context', {}).get('company', -1)),
            ],
        depends=['state'], select=True)
    code = fields.Char('Code', states=READONLY_STATE, depends=['state'])
    name = fields.Char('Name', states=READONLY_STATE, depends=['state'],
        translate=True)
    manual_code = fields.Char('Manual Code',
        states={
            'readonly': ~Eval('attributes', [0]) & READONLY_STATE,
        },
        depends=['state', 'attributes'])
    manual_name = fields.Char('Manual Name',
        states={
            'readonly': ~Eval('attributes', [0]) & READONLY_STATE,
        },
        depends=['state', 'attributes'], translate=True)
    party = fields.Many2One('party.party', 'Party', states=READONLY_STATE,
        depends=['state'])
    template = fields.Many2One('configurator.property', 'Template',
        domain=[('template', '=', True)],
        states=READONLY_STATE, depends=['state', 'template'])
    design_date = fields.Date('Design Date', states=READONLY_STATE,
        depends=['state'])
    currency = fields.Many2One('currency.currency', 'Currency',
        states=READONLY_STATE, depends=['state'])
    attributes = fields.One2Many('configurator.design.attribute', 'design',
        'Attributes', states=READONLY_STATE, depends=['state'])
    prices = fields.One2Many('configurator.quotation.line', 'design',
        'Quotations', states=READONLY_STATE, depends=['state'])
    objects = fields.One2Many('configurator.object', 'design', 'Objects',
        readonly=True)
    state = fields.Selection(STATES, 'State', readonly=True, required=True)
    product = fields.Many2One('product.product', 'Product Designed',
        readonly=True)
    suppliers = fields.One2Many('configurator.quotation.supplier', 'design',
        'Suppliers')
    quotation_uom = fields.Many2One('product.uom', 'Quotation Uom',
        states={
            'readonly': Bool(Eval('prices', [0])),
            'required': True,
        },
        domain=[
            If(Bool(Eval('product_uom_category')),
                ('category', '=', Eval('product_uom_category')),
                ('category', '!=', -1)),
            ],
        depends=['prices', 'product_uom_category', 'state'])
    product_exists = fields.Function(fields.Many2One('product.product',
        'Searched Product'), 'get_product_exist')
    quotation_date = fields.Date('Quotation Date', readonly=True)
    quoted_by = employee_field("Quoted By")
    process_date = fields.Date('Quotation Date', readonly=True)
    process_by = employee_field("Processed By")
    product_uom_category = fields.Function(
        fields.Many2One('product.uom.category', 'Product Uom Category'),
        'on_change_with_product_uom_category')

    @classmethod
    def __setup__(cls):
        super(Design, cls).__setup__()
        cls._transitions |= set((
            ('draft', 'done'),
            ('draft', 'cancel'),
        ))
        cls._buttons.update({
            'cancel': {
                'invisible': ~Eval('state').in_(['draft']),
                'depends': ['state'],
                },
            'update': {
                'invisible': ~Eval('state').in_(['draft']),
                'depends': ['state'],
            },
            'process': {
                'invisible': Eval('state').in_(['done', 'cancel']),
                'depends': ['state'],
            },
            'create_prices': {
                'invisible': ~Eval('state').in_(['draft']),
                'depends': ['state'],
            },
        })

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            return company.currency.id

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_design_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_state():
        return 'draft'

    @fields.depends('template', 'code', 'product_exists', methods=[
        'design_full_dict', 'get_product_exist'])
    def on_change_manual_code(self):
        if not self.template:
            return
        custom_locals = self.design_full_dict()
        self.code = self.template.render_expression_record(
            self.template.code_template or '', custom_locals)
        self.product_exists = self.get_product_exist()

    @fields.depends('template', 'name', methods=['design_full_dict'])
    def on_change_manual_name(self):
        if not self.template:
            return
        custom_locals = self.design_full_dict()
        self.name = self.template.render_expression_record(
            self.template.name_template or '', custom_locals)

    @fields.depends('template')
    def on_change_with_product_uom_category(self, name=None):
        if self.template:
            return self.template.product_template.default_uom_category.id

    @classmethod
    def copy(cls, designs, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('process_by', None)
        default.setdefault('process_date', None)
        default.setdefault('quoted_by', None)
        default.setdefault('quotion_date', None)
        default.setdefault('objects', None)
        default.setdefault('product', None)
        return super(Design, cls).copy(designs, default=default)

    def get_product_exist(self, name=None):
        if self.product:
            return self.product.id
        Product = Pool().get('product.product')
        products = Product.search([
            ('code', '=', self.code)], limit=1)
        if not products:
            return None
        product, = products
        return product.id

    @classmethod
    @ModelView.button
    @Workflow.transition('cancel')
    def cancel(cls, designs):
        pass

    def as_dict(self):
        Function = Pool().get('configurator.property')
        functions = Function.search([('type', '=', 'function'),
            ('parent', 'child_of', [self.template.id])])
        res = {}
        for attribute in self.attributes:
            parent = attribute.property.get_parent()
            if parent not in res:
                res[parent] = {}
            res[parent][attribute.property] = attribute

        for function_ in functions:
            parent = function_.get_parent()
            res[parent][function_] = function_.evaluate(function_.quantity,
                    res[parent])
        return res

    def create_object(self, object):
        pool = Pool()
        CreatedObject = pool.get('configurator.object')
        created = CreatedObject()
        created.object = object
        created.design = self
        return created

    def get_attributes(self):
        values = {}
        if not self.template:
            return []
        for attribute in self.attributes:
            values[attribute.property.code] = attribute
        return self.template.compute_attributes(self, values)

    @classmethod
    @ModelView.button
    def update(cls, designs):
        QuotationSupplier = Pool().get(
            'configurator.quotation.supplier')
        for design in designs:
            design.attributes = design.get_attributes()
            categories = design.template.get_quotation_categories()
            suppliers = []
            for category in set(categories):
                q = QuotationSupplier(category=category)
                q.supplier = category.party
                suppliers.append(q)
            design.suppliers = suppliers

        cls.save(designs)

    @classmethod
    @ModelView.button
    def create_prices(cls, designs):
        pool = Pool()
        User = pool.get('res.user')
        DesignLine = pool.get('configurator.design.line')
        Design = pool.get('configurator.design')
        Lang = pool.get('ir.lang')
        remove_lines = []
        BomInput = pool.get('production.bom.input')
        Product = pool.get('product.product')
        Uom = pool.get('product.uom')
        Date = Pool().get('ir.date')
        to_save = []

        for design in designs:
            prices = {}
            remove_lines = []
            for price in design.prices:
                remove_lines += price.prices

            design.quotation_date = Date.today()
            design.quoted_by = User(Transaction().user).employee
            values = design.as_dict()
            res = design.template.create_prices(design, values)

            suppliers = dict((x.category, x.supplier)
                for x in design.suppliers)
            for quote in design.prices:
                quote_quantity = Uom.compute_qty(design.quotation_uom,
                    quote.quantity, design.template.uom, round=False)
                for prop, v in res.items():
                    v = v[0]
                    key = (prop.price_category or prop.id, quote)
                    dl = prices.get(key)
                    quantity = 0
                    cost_price = None
                    product = None
                    if prop.type not in ('product', 'match'):
                        continue
                    if prop.type in ('product', 'match'):
                        if isinstance(v, BomInput):
                            quantity = v.quantity * quote_quantity
                            product = v.product
                        elif isinstance(v, Product):
                            parent = prop.get_parent()
                            quantity = prop.evaluate(prop.quantity,
                                design.as_dict()[parent])
                            quantity = quantity * quote_quantity
                            product = v
                    # if prop.type == 'operation':
                    #     quantity = prop.evaluate(prop.quantity,
                    #                      design.as_dict())
                    #     quantity = quantity * quote.quantity
                    #     quantity = v.compute_time(quantity, v.time_uom)
                    #     cost_price = prop.work_center_category.cost_price
                    dl = prices.get(key)
                    if not dl:
                        supplier = None
                        if prop.quotation_category:
                            supplier = suppliers[prop.quotation_category]
                        parent = prop.get_parent()
                        qty_ratio = prop.get_ratio_for_prices(
                            values.get(parent, {}), 1)
                        if not product:
                            continue
                        cost_price = quote.get_unit_price(product,
                            quantity * qty_ratio, prop.uom, supplier)
                        dl = prop.create_design_line(quantity * qty_ratio,
                            prop.uom, cost_price, quote)
                        dl.qty_ratio = qty_ratio
                        dl.debug_quantity = quantity
                        if not prop.price_category:
                            dl.property = prop
                        prices[key] = dl
                    else:
                        parent = prop.get_parent()
                        qty_ratio = prop.get_ratio_for_prices(
                            values.get(parent, {}), 1)
                        cost_price = (Decimal(qty_ratio * quantity) / (
                                dl.unit_price
                                + Decimal(qty_ratio * quantity) * cost_price))
                        cost_price = Decimal(cost_price).quantize(Decimal(
                            str(10.0 ** -price_digits[1])))
                        dl.quantity += quantity * qty_ratio
                        dl.debug_quantity = quantity
                        dl.unit_price = cost_price

            langs = Lang.search([('active', '=', True),
                ('translatable', '=', True)])

            for lang in langs:
                design.render_fields(lang)

            to_save = prices.values()
            DesignLine.save(to_save)
        DesignLine.delete(remove_lines)

    def design_full_dict(self):
        record = self.as_dict()
        custom_locals = {}

        Property = Pool().get('configurator.property')
        properties = Property.search([
            ('parent', 'child_of', [self.template.id])])

        custom_locals['design'] = self
        for property in properties:
            custom_locals[property.get_full_code()] = property

        for parent_prop, attributes in record.items():
            for prop, attr in attributes.items():
                custom_locals[prop.get_full_code()] = attr
        return custom_locals

    def get_design_render_fields(self):
        return [('name_template', 'name'), ('code_template', 'code')]

    def get_product_render_fields(self):
        return []

    def render_fields(self, lang):
        pool = Pool()
        Design = pool.get('configurator.design')

        design_fields = self.get_design_render_fields()
        product_fields = self.get_product_render_fields()

        with Transaction().set_context(language=lang.code):
            design = Design(self.id)
            product = design.product
            custom_locals = design.design_full_dict()
            ptemplate = design.template
            for tmpl_field, field in design_fields:
                f = getattr(ptemplate, tmpl_field)
                if not f:
                    continue
                val = ptemplate.render_expression_record(f, custom_locals)
                val = val.replace('\n', '').replace('\t', '')
                setattr(design, field, val)
            design.save()

            if not design.product:
                return

            product.template.name = design.name
            product.code = design.code
            for tmpl_field, field in product_fields:
                f = getattr(ptemplate, tmpl_field)
                val = ptemplate.render_expression_record(f, custom_locals)
                setattr(product, field, val)
            product.save()

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def process(cls, designs):
        CreatedObject = Pool().get('configurator.object')
        to_delete = []
        for design in designs:
            to_delete += [x for x in design.objects]
            res = design.template.create_prices(design, design.as_dict())
            for prop, objs in res.items():
                obj, additional = objs
                if prop.type == 'bom':
                    # TODO: update list price of product.
                    obj.save()
                    ref = design.create_object(obj)
                    ref.save()
                    for input_ in obj.inputs:
                        ref = design.create_object(input_)
                        ref.save()
                    for output_ in obj.outputs:
                        ref = design.create_object(output_)
                        ref.save()
                        if prop.parent is None:
                            design.product = output_.product
                            design.save()

                for obj in additional:
                    obj.save()
                    ref = design.create_object(obj)
                    ref.save()

                product = design.product
                if not hasattr(product, 'product_customer'):
                    continue

                ProductCustomer = Pool().get('sale.product_customer')
                product_customer = ProductCustomer()
                product_customer.template = product.template
                product_customer.product = product
                product.party = design.party
                product.name = design.name
                product.code = design.code
                if hasattr(product_customer, 'product_customer_only'):
                    product_customer.product_customer_only = True
                product_customer.save()

        CreatedObject.delete(to_delete)


class QuotationSupplier(ModelSQL, ModelView):
    """ Quotation Supplier """
    __name__ = 'configurator.quotation.supplier'

    design = fields.Many2One('configurator.design', 'Design')
    category = fields.Many2One('configurator.property.quotation_category',
        'Category')
    supplier = fields.Many2One('party.party', 'Supplier')


class QuotationLine(ModelSQL, ModelView):
    """  Quotation Line """
    __name__ = 'configurator.quotation.line'

    design = fields.Many2One('configurator.design', 'Design', required=True,
        ondelete='CASCADE')
    quantity = fields.Float('Quantity', digits=(16, 4),
        states={
            'readonly': Bool(Eval('unit_price'))
        }, depends=['unit_price'])
    prices = fields.One2Many('configurator.design.line', 'quotation', 'Prices')
    global_margin = fields.Float('Global Margin', digits=(16, 4),
        # states={'readonly': 'design_state' != 'draft'},
        depends=['design_state'])
    cost_price = fields.Function(fields.Numeric('Cost Price',
        digits=price_digits), 'get_prices')
    list_price = fields.Function(fields.Numeric('Total Price',
        digits=price_digits), 'get_prices')
    manual_list_price = fields.Numeric('Manual List Price',
        digits=price_digits)
    margin = fields.Function(fields.Numeric('Margin', digits=(16, 4)),
        'get_prices')
    unit_price = fields.Function(fields.Numeric('Unit Price',
        digits=price_digits), 'get_prices')
    product_uom_category = fields.Function(
        fields.Many2One('product.uom.category', 'Product Uom Category'),
        'get_product_uom_category')
    design_state = fields.Function(fields.Selection(STATES, 'Design State'),
        'on_change_with_design_state')
    material_cost_price = fields.Function(fields.Numeric('Cost Material',
        digits=(16, 4)), 'get_prices')
    margin_material = fields.Function(fields.Numeric('Margin Material',
        digits=(16, 4)), 'get_prices')
    cost_price_no_manual = fields.Function(fields.Numeric(
        'Cost Price No Manual', digits=price_digits), 'get_prices')

    def get_rec_name(self, name):
        return '%s - %s' % (str(self.quantity),
            self.design.name)

    @fields.depends('design', '_parent_design.state')
    def on_change_with_design_state(self, name=None):
        if self.design:
            return self.design.state

    def get_product_uom_category(self, name=None):
        if self.design and self.design.template:
            return self.design.template.uom.category.id

    def _get_context_purchase_price(self, uom=None):
        context = {}
        context['currency'] = self.design.currency and self.design.currency.id
        context['purchase_date'] = self.design.design_date
        if uom:
            context['uom'] = uom and uom.id
        return context

    def get_unit_price(self, product, quantity, uom, supplier):
        pool = Pool()
        Product = pool.get('product.product')
        Uom = pool.get('product.uom')

        context = self._get_context_purchase_price()
        context.update(product.template.get_purchase_context())
        if supplier:
            context['supplier'] = supplier.id
        elif context.get('supplier'):
            del context['supplier']

        context[uom] = uom and uom.id
        with Transaction().set_context(context):
            quantity2 = Uom.compute_qty(uom,
                abs(quantity), product.purchase_uom)

            unit_price = Product.get_purchase_price(
                [product], abs(quantity2 or 0))[product.id]
            if unit_price:
                unit_price = unit_price.quantize(
                    Decimal(1) / 10 ** price_digits[1])

            return unit_price

    @classmethod
    def get_prices(cls, quotations, names):
        pool = Pool()
        Uom = pool.get('product.uom')
        res = {}
        quantize = Decimal(str(10.0 ** -price_digits[1]))
        for name in {'cost_price', 'list_price', 'margin', 'unit_price',
                'material_cost_price', 'margin_material',
                'cost_price_no_manual'}:
            res[name] = {}.fromkeys([x.id for x in quotations], Decimal(0))

        for quote in quotations:
            cost_price = 0
            list_price = 0
            cost_price_noman = 0
            material_cost_price = 0
            quote_quantity = Uom.compute_qty(quote.design.quotation_uom,
                quote.quantity, quote.design.template.uom, round=False)

            unit_price_uom = quote.design.template.product_template.default_uom
            quote_quantity2 = Uom.compute_qty(quote.design.template.uom,
                quote_quantity, unit_price_uom, round=True)

            for line in quote.prices:
                price = (line.manual_unit_price or line.unit_price)*Decimal(
                    1 + (line.margin or 0))
                cost_price += (Decimal(line.quantity or 0)
                    * (price or 0))
                cost_price_noman += Decimal(line.quantity) * line.unit_price
                list_price += line.amount
                material_cost_price += Decimal(line.property.quotation_category
                    and line.property.quotation_category.type_ == 'goods'
                    and line.quantity or 0) * price
            list_price = (list_price
                * Decimal(1 + ((quote.global_margin or 0)) or 0
                )).quantize(quantize)

            unit_price = Decimal(float(list_price) / quote_quantity2
                ).quantize(quantize)

            res['list_price'][quote.id] = Decimal(quote_quantity) * (
                quote.manual_list_price or unit_price)
            res['cost_price'][quote.id] = cost_price
            res['cost_price_no_manual'][quote.id] = cost_price_noman
            res['margin'][quote.id] = (res['list_price'][quote.id]
                - cost_price_noman)
            res['unit_price'][quote.id] = unit_price
            res['material_cost_price'][quote.id] = material_cost_price
            res['margin_material'][quote.id] = (res['list_price'][quote.id]
                - material_cost_price)
        return res


class DesignLine(sequence_ordered(), ModelSQL, ModelView):
    'Design Line'
    __name__ = 'configurator.design.line'
    quotation = fields.Many2One('configurator.quotation.line', 'Quotation',
        readonly=True, required=True,
        ondelete='CASCADE')
    category = fields.Many2One('configurator.property.price_category',
        'Category', readonly=True)
    property = fields.Many2One('configurator.property', 'Property',
        readonly=True)
    quantity = fields.Float('Quantity', readonly=True)
    uom = fields.Many2One('product.uom', 'UoM', readonly=True)
    unit_price = fields.Numeric('Unit Price', digits=price_digits,
        readonly=True)
    manual_unit_price = fields.Numeric('Manual Unit Price',
        digits=price_digits)
    margin = fields.Float('Margin', digits=(16, 4), )
    amount = fields.Function(fields.Numeric('Amount', digits=price_digits),
        'on_change_with_amount')
    currency = fields.Function(fields.Many2One('currency.currency',
        'Currency'),
        'get_currency')
    qty_ratio = fields.Float('Quantity Ratio', readonly=True)
    debug_quantity = fields.Float('Debug Qty', readonly=True)  # TODO: remove
    debug_amount = fields.Function(fields.Numeric('Debug Amount',
        digits=price_digits), 'on_change_with_debug_amount')  # TODO: remove

    @fields.depends('quantity', 'unit_price', 'manual_unit_price')
    def on_change_with_amount(self, name=None):
        if not self.quantity or not (self.unit_price
                or self.manual_unit_price):
            return _ZERO
        price = self.manual_unit_price or self.unit_price
        return Decimal(str(self.quantity)) * price * Decimal(
            self.margin and 1 + self.margin / 100.0 or 1)

    @fields.depends('debug_quantity', 'unit_price', 'manual_unit_price')
    def on_change_with_debug_amount(self, name=None):
        if not self.debug_quantity or not (self.unit_price
                or self.manual_unit_price):
            return _ZERO
        price = self.manual_unit_price or self.unit_price
        return Decimal(str(self.debug_quantity)) * price * Decimal(
            self.margin and 1 + self.margin / 100.0 or 1)

    def get_currency(self, name=None):
        return self.quotation.design.currency


class DesignAttribute(sequence_ordered(), ModelSQL, ModelView):
    'Design Attribute'
    __name__ = 'configurator.design.attribute'
    design = fields.Many2One('configurator.design', 'Design', required=True,
        ondelete='CASCADE')
    property = fields.Many2One('configurator.property',
        'Property', required=True, readonly=True)
    property_type = fields.Function(fields.Selection(TYPE, 'Type'),
        'on_change_with_property_type')
    use_property = fields.Boolean('Add',
        states={
            'invisible': Eval('property_type') != 'bom',
        },
    )
    property_options = fields.Function(fields.Many2Many(
        'configurator.property', None, None, 'Options'),
        'on_change_with_property_options')
    option = fields.Many2One('configurator.property', 'Option', domain=[
        ('id', 'in', Eval('property_options')),
    ], states={
        'invisible': Eval('property_type') != 'options',
        'readonly': Eval('design_state') != 'draft',
    }, depends=['property_type', 'property_options', 'design_state'])
    number = fields.Float('Number', states={
        'invisible': Eval('property_type') != 'number',
        'readonly': Eval('design_state') != 'draft',
    }, depends=['property_type', 'design_state'])
    text = fields.Char('Text', states={
        'invisible': Eval('property_type') != 'text',
        'readonly': Eval('design_state') != 'draft',
    }, depends=['property_type', 'design_state'])
    design_state = fields.Function(fields.Selection(STATES, 'Design State'),
        'on_change_with_design_state')

    @fields.depends('design', '_parent_design.state')
    def on_change_with_design_state(self, name=None):
        if self.design:
            return self.design.state

    @fields.depends('property')
    def on_change_with_property_type(self, name=None):
        if not self.property:
            return
        return self.property.type

    @fields.depends('property')
    def on_change_with_property_options(self, name=None):
        if not self.property:
            return []
        res = [x.id for x in self.property.childs]
        return res
