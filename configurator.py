from decimal import Decimal
from trytond.model import (Workflow, ModelView, ModelSQL, fields,
    sequence_ordered, tree)
from trytond.pyson import Eval, Not, If, Bool
from trytond.pool import Pool
from trytond.config import config
from trytond.transaction import Transaction
from copy import copy
from trytond.exceptions import UserError
from trytond.i18n import gettext
import math

price_digits = (16, config.getint('product', 'price_decimal', default=4))


_ZERO = Decimal(0)
TYPE = [
    (None, ''),
    ('bom', 'BoM'),
    ('product', 'Product'),
    ('purchase_product', 'Purchase Product'),
    ('group', 'Group'),
    # ('operation', 'Operation'),
    ('options', 'Options'),
    ('number', 'Number'),
    ('text', 'Text'),
    ('function', 'Function'),
    ('attribute', 'Product Attribute')
]

class PriceCategory(ModelSQL, ModelView):
    """ Price Category """
    __name__ = 'configurator.property.price_category'

    name = fields.Char('Name')


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
        'required': Eval('type').in_(['bom', 'product', 'purchase_product',
            'product_attribute'])
        },
        domain=[('category', '=', Eval('product_uom_category', -1))],
        depends=['product_uom_category', 'type'])
    childs = fields.One2Many('configurator.property', 'parent', 'childs',
        states={
            'invisible': Not(Eval('type').in_(['bom', 'purchase_product',
                'options', 'group']))
        })
    parent = fields.Many2One('configurator.property', 'Parent', select=True,
        ondelete='CASCADE')
    quantity = fields.Text('Quantity', states={
        'invisible': Not(Eval('type').in_(['purchase_product',
            'bom', 'product', 'function'])),
        'required': Eval('type').in_(['bom', 'product', 'purchase_product'])
    }, depends=['type'])
    price_category = fields.Many2One('configurator.property.price_category',
        'Price Category',
        states={
            'invisible': Eval('type').in_(['function', 'text', 'number',
                'attribute', 'group']),
        },)
    object_expression = fields.Text('Object Expression',
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

    # Summary should be a Jinja2 template
    summary = fields.Text('Summary')

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
        except BaseException as e:
            raise UserError(gettext(
                'product_dynamic_configurator.msg_expression_error',
                property=self.name, expression=self.quantity,
                invalid=str(e)))

    def create_prices(self, design, values):
        created_obj = {}
        if self.type != 'options':
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
            if not hasattr(product, f):
                continue
            setattr(nproduct, f, getattr(product, f))

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

        for prop, child_res in created_obj.items():
            if prop.parent != self:
                continue
            child_res = child_res[0]
            if prop.type == 'attribute':
                if not hasattr(template, 'attributes'):
                    template.attributes = tuple()
                template.attribute_set = prop.attribute_set
                type_, value = self.get_product_attribute_typed(prop,
                    self.evaluate(prop.product_attribute_value, values))
                setattr(child_res, 'value_' + type_, value)
                setattr(child_res, 'value', value)
                template.attributes += (child_res,)

        if self.object_expression:
            expressions = eval(self.object_expression)
            for key, value in expressions.items():
                val = self.evaluate(value, values)
                setattr(template, key, val)

        template.products = (product,)
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
        qty = 0
        for child in self.childs:
            if child.type in ('number', 'char', 'attribute', 'text',
                    'bom', 'group'):
                continue
            obj, _ = created_obj[child]
            if isinstance(obj, BomInput):
                cost_price += (Decimal(obj.quantity) * obj.product.cost_price)
                qty += obj.quantity

        quantize = Decimal(str(10.0 ** -price_digits[1]))
        if cost_price:
            product.cost_price = (Decimal(qty)/Decimal(cost_price)
                ).quantize(quantize)

        bom_input.product = product
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
        Template = pool.get('product.template')
        Bom = pool.get('production.bom')
        BomInput = pool.get('production.bom.input')
        BomOutput = pool.get('production.bom.output')
        ProductBom = pool.get('product.product-production.bom')
        Operation = pool.get('production.route.operation')
        Route = pool.get('production.route')
        Uom = pool.get('product.uom')

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
                if child_res.product.type == 'service':
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
        for prop, child_res in created_obj.items():
            if prop.parent != self:
                continue
            child_res = child_res[0]
            if prop.type == 'attribute':
                if not hasattr(template, 'attributes'):
                    template.attributes = tuple()
                template.attribute_set = prop.attribute_sets
                type_, value = self.get_product_attribute_typed(prop,
                    self.evaluate(prop.product_attribute_value, values))
                setattr(child_res, 'value_' + type_, value)
                setattr(child_res, 'value', value)
                template.attributes += (child_res,)

        # if len(template.attributes):
        #     product = self.set_template_fields(product)
        Template.update_attributes_values([template])
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
        ratio_parent = self.evaluate(parent.quantity or '1', values)
        return parent.get_ratio_for_prices(values, ratio*ratio_parent)

    def create_design_line(self, quantity, uom, unit_price, quote):
        DesignLine = Pool().get('configurator.design.line')
        dl = DesignLine()
        dl.quotation = quote
        dl.quantity = quantity
        dl.uom = uom
        dl.unit_price = unit_price
        return dl


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
    code = fields.Char('Code', states=READONLY_STATE, depends=['state'])
    name = fields.Char('Name', states=READONLY_STATE, depends=['state'])
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
    summary = fields.Function(fields.Text('Summary'), 'get_summary')
    objects = fields.One2Many('configurator.object', 'design', 'Objects',
        readonly=True)
    state = fields.Selection(STATES, 'State', readonly=True, required=True)
    product = fields.Many2One('product.product', 'Product Designed',
        readonly=True)

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
    def default_design_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_state():
        return 'draft'

    def get_summary(self, name):
        return

    @classmethod
    def copy(cls, designs, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('quotations', None)
        default.setdefault('lines', None)
        default.setdefault('prices', None)
        return super(Design, cls).copy(designs, default=default)

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
        for design in designs:
            design.attributes = design.get_attributes()
        cls.save(designs)

    @classmethod
    @ModelView.button
    def create_prices(cls, designs):
        pool = Pool()
        DesignLine = pool.get('configurator.design.line')
        remove_lines = []
        BomInput = pool.get('production.bom.input')
        Product = pool.get('product.product')
        Uom = pool.get('product.uom')
        to_save = []
        for design in designs:
            prices = {}
            remove_lines = []
            for price in design.prices:
                remove_lines += price.prices

            values = design.as_dict()
            res = design.template.create_prices(design, values)

            for quote in design.prices:
                for prop, v in res.items():
                    v = v[0]
                    key = (prop.price_category or prop.id, quote)
                    dl = prices.get(key)
                    quantity = 0
                    cost_price = None
                    if prop.type not in ('product', 'operation', ):
                        continue
                    if prop.type == 'product':
                        if isinstance(v, BomInput):
                            quote_quantity = Uom.compute_qty(quote.uom,
                                quote.quantity, design.template.uom)
                            quantity = v.quantity*quote_quantity
                            cost_price = quote.get_unit_price(v.product,
                                quantity)
                        elif isinstance(v, Product):
                            parent = prop.get_parent()
                            quantity = prop.evaluate(prop.quantity,
                                design.as_dict()[parent])
                            quote_quantity = Uom.compute_qty(quote.uom,
                                quote.quantity, design.template.uom)
                            quantity = quantity * quote_quantity
                            cost_price = quote.get_unit_price(v, quantity)
                    # if prop.type == 'operation':
                    #     quantity = prop.evaluate(prop.quantity, design.as_dict())
                    #     quantity = quantity * quote.quantity
                    #     quantity = v.compute_time(quantity, v.time_uom)
                    #     cost_price = prop.work_center_category.cost_price
                    dl = prices.get(key)
                    if not dl:
                        dl = prop.create_design_line(quantity, prop.uom,
                            cost_price, quote)
                        parent = prop.get_parent()
                        qty_ratio = prop.get_ratio_for_prices(
                            values.get(parent, {}), 1)
                        dl.category = prop.price_category
                        dl.qty_ratio = qty_ratio
                        if not prop.price_category:
                            dl.property = prop
                        prices[key] = dl
                    else:
                        cost_price = (Decimal(quantity)/(
                                dl.unit_price +
                                Decimal(quantity)*cost_price))
                        cost_price = Decimal(cost_price).quantize(Decimal(
                            str(10.0 ** -price_digits[1])))
                        dl.quantity += quantity
                        dl.unit_price = cost_price

            to_save = prices.values()
            DesignLine.save(to_save)
        DesignLine.delete(remove_lines)

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

        CreatedObject.delete(to_delete)

class QuotationLine(ModelSQL, ModelView):
    """  Quotation Line """
    __name__ = 'configurator.quotation.line'

    design = fields.Many2One('configurator.design', 'Design', required=True,
        ondelete='CASCADE')
    quantity = fields.Float('Quantity', digits=(16, 4),
        states={
            'readonly': Bool(Eval('unit_price'))
        }, depends=['unit_price'])
    uom = fields.Many2One('product.uom', 'UoM',
        domain=[
            If(Bool(Eval('product_uom_category')),
                ('category', '=', Eval('product_uom_category')),
                ('category', '!=', -1))],
        states={'readonly': Bool(Eval('unit_price'))},
        depends=['product_uom_category', 'unit_price'])
    prices = fields.One2Many('configurator.design.line', 'quotation', 'Prices')
    global_margin = fields.Float('Global Margin', digits=(16, 4),
        # states={'readonly': 'design_state' != 'draft'},
        depends=['design_state'])
    cost_price = fields.Function(fields.Numeric('Cost Price',
        digits=price_digits), 'get_prices')
    list_price = fields.Function(fields.Numeric('List Price',
        digits=price_digits), 'get_prices')
    margin = fields.Function(fields.Numeric('Margin', digits=(16, 4)),
        'get_prices')
    unit_price = fields.Function(fields.Numeric('Unit Price',
        digits=price_digits), 'get_prices')
    product_uom_category = fields.Function(
        fields.Many2One('product.uom.category', 'Product Uom Category'),
        'get_product_uom_category')
    design_state = fields.Function(fields.Selection(STATES, 'Design State'),
        'on_change_with_design_state')

    def get_rec_name(self, name):
        return '%s(%s) - %s' % (str(self.quantity), str(self.uom.symbol),
            self.design.name)

    @fields.depends('design', '_parent_design.state')
    def on_change_with_design_state(self, name=None):
        if self.design:
            return self.design.state

    def get_product_uom_category(self, name=None):
        if self.design and self.design.template:
            return self.design.template.uom.category.id

    def _get_context_purchase_price(self):
        context = {}
        context['currency'] = self.design.currency and self.design.currency.id
        context['purchase_date'] = self.design.design_date
        if self.uom:
            context['uom'] = self.uom.id
        return context

    def get_unit_price(self, product, quantity):
        Product = Pool().get('product.product')

        with Transaction().set_context(self._get_context_purchase_price()):
            unit_price = Product.get_purchase_price(
                [product], abs(quantity or 0))[product.id]
            if unit_price:
                unit_price = unit_price.quantize(
                    Decimal(1) / 10 ** price_digits[1])
            return unit_price

    @classmethod
    def get_prices(cls, quotations, names):
        res = {}
        quantize = Decimal(str(10.0 ** -price_digits[1]))
        for name in {'cost_price', 'list_price', 'margin', 'unit_price'}:
            res[name] = {}.fromkeys([x.id for x in quotations], Decimal(0))
        for quote in quotations:
            for line in quote.prices:
                res['cost_price'][quote.id] += (Decimal(line.quantity or 0) *
                    (line.unit_price or 0) * Decimal(line.qty_ratio or 0))
                res['list_price'][quote.id] += line.amount * Decimal(
                    line.qty_ratio or 0)

            list_price = res['list_price'].get(quote.id, 0)
            cost_price = res['cost_price'].get(quote.id, 0)

            if list_price and cost_price:
                res['margin'][quote.id] = (list_price / cost_price - 1
                    ).quantize(quantize)
            res['list_price'][quote.id] = (list_price
                * Decimal(1 + ((quote.global_margin or 0) / 100) or 0
                )).quantize(quantize)
            res['unit_price'][quote.id] = Decimal(float(cost_price) /
                quote.quantity*quote.uom.rate).quantize(quantize)
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
    qty_ratio = fields.Float('Quantity Ratio', readonly=True)
    uom = fields.Many2One('product.uom', 'UoM', readonly=True)
    unit_price = fields.Numeric('Unit Price', digits=price_digits,
        readonly=True)
    margin = fields.Float('Margin', digits=(16, 4), )
    amount = fields.Function(fields.Numeric('Amount', digits=price_digits),
        'on_change_with_amount')
    currency = fields.Function(fields.Many2One('currency.currency', 'Currency'),
        'get_currency')

    @fields.depends('quantity', 'unit_price')
    def on_change_with_amount(self, name=None):
        if not self.quantity or not self.unit_price:
            return _ZERO
        return Decimal(str(self.quantity)) * self.unit_price * Decimal(
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
    property_options = fields.Function(fields.Many2Many('configurator.property',
        None, None, 'Options'), 'on_change_with_property_options')
    option = fields.Many2One('configurator.property', 'Option', domain=[
        ('id', 'in', Eval('property_options')),
    ], states={
        'invisible': Eval('property_type') != 'options',
        'readonly': Eval('design_state') != 'draft',
    }, depends=['property_type', 'property_options', 'design_state'])
    number = fields.Float('Number', states={
        'invisible': Eval('property_type') not in ('number', 'options'),
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
