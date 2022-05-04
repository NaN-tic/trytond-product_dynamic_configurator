====================
Iso Bag Scenario
====================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()
    >>> from trytond.modules.currency.tests.tools import get_currency

Install mapol::

    >>> config = activate_modules(['product_dynamic_configurator', 'purchase_information_uom'])
    >>> config.price_digits = 6

Get all Units::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> km, = ProductUom.find([('name', '=', 'Kilometer')])
    >>> m, = ProductUom.find([('name', '=', 'Kilogram')])
    >>> kg, = ProductUom.find([('name', '=', 'Kilogram')])
    >>> # m, = ProductUom.find([('name', '=', 'Meter')])
    >>> hour, = ProductUom.find([('name', '=', 'Hour')])
    >>> unit.digits = 6
    >>> unit.rounding = 0.00001
    >>> unit.save()
    >>> km.digits = 6
    >>> km.rounding = 0.0001
    >>> km.save()

    >>> euro = get_currency('EUR')

Company::

    >>> _ = create_company()
    >>> company = get_company()
    >>> tax_identifier = company.party.identifiers.new()
    >>> tax_identifier.type = 'eu_vat'
    >>> tax_identifier.code = 'BE0897290877'
    >>> company.party.save()
    >>> party = company.party


Create Attribute Sets::

    >>> AttributeSet = Model.get('product.attribute.set')
    >>> Attribute = Model.get('product.attribute')
    >>> AttributeRel = Model.get('product.attribute-product.attribute-set')
    >>> AttributeTemplate = Model.get('product.attribute.field_template')

    >>> attribute_set = AttributeSet()
    >>> attribute_set.name = 'Iso Bag'
    >>> attribute_set.use_templates = True
    >>> attribute_set.save()

    >>> template = AttributeTemplate()
    >>> template.field_ = 'product,code'
    >>> template.jinja_template = "code -{{material}}-{{galga}}-{{width}}-{{length}}"
    >>> template.attribute_set = attribute_set
    >>> template.save()

    >>> template = AttributeTemplate()
    >>> template.field_ = 'template,name'
    >>> template.jinja_template = "Name -{{material}}-{{galga}}-{{width}}-{{length}}"
    >>> template.attribute_set = attribute_set
    >>> template.save()

    >>> galga_attr = Attribute()
    >>> galga_attr.name = 'galga'
    >>> galga_attr.display_name = 'Galga'
    >>> galga_attr.type_ = 'char'
    >>> galga_attr.save()

    >>> width_attr = Attribute()
    >>> width_attr.name = 'width'
    >>> width_attr.display_name = 'Width'
    >>> width_attr.type_ = 'char'
    >>> width_attr.save()

    >>> length_attr = Attribute()
    >>> length_attr.name = 'length'
    >>> length_attr.display_name = 'Length'
    >>> length_attr.type_ = 'char'
    >>> length_attr.save()

    >>> material_attr = Attribute()
    >>> material_attr.name = 'material'
    >>> material_attr.display_name = 'Material'
    >>> material_attr.type_ = 'char'
    >>> material_attr.save()

    >>> attribute_set.attributes.append(galga_attr)
    >>> attribute_set.attributes.append(width_attr)
    >>> attribute_set.attributes.append(length_attr)
    >>> attribute_set.attributes.append(material_attr)
    >>> attribute_set.save()


Create Template Products::

    >>> Template = Model.get('product.template')
    >>> template = Template(name="Production Template", type="goods")
    >>> template.list_price = Decimal('0')
    >>> template.default_uom = unit
    >>> template.configurator_template = True
    >>> template.attribute_set = attribute_set
    >>> template.producible = True
    >>> template.save()
    >>> production_template, = template.products
    >>> production_template.cost_price_method = 'fixed'
    >>> production_template.save()

    >>> Template = Model.get('product.template')
    >>> template = Template(name="Purchase Template (kg)", type="goods")
    >>> template.list_price = Decimal('0')
    >>> template.default_uom = kg
    >>> template.configurator_template = True
    >>> template.attribute_set = attribute_set
    >>> template.save()
    >>> purchase_template, = template.products
    >>> purchase_template.cost_price_method = 'fixed'
    >>> purchase_template.save()

    >>> Template = Model.get('product.template')
    >>> template = Template(name="Purchase Template (km)", type="goods")
    >>> template.list_price = Decimal('0')
    >>> template.default_uom = km
    >>> template.configurator_template = True
    >>> template.attribute_set = attribute_set
    >>> template.save()
    >>> purchase_template_km, = template.products
    >>> purchase_template_km.cost_price_method = 'fixed'
    >>> purchase_template_km.save()

Create Template Products::
    >>> weight = 0.46
    >>> Template = Model.get('product.template')
    >>> template = Template(name="Foam", type="goods")
    >>> template.list_price = Decimal('0')
    >>> template.default_uom = kg
    >>> template.save()
    >>> foam, = template.products
    >>> foam.cost_price = Decimal('0.0656')
    >>> foam.cost_price_method = 'fixed'
    >>> foam.save()

    >>> weight2 = 0.45
    >>> template = Template(name="B.P. Blanco", type="goods")
    >>> template.default_uom = kg
    >>> template.list_price=Decimal('0')
    >>> template.save()
    >>> blanco, = template.products
    >>> blanco.cost_price = Decimal('0.0019')
    >>> blanco.cost_price_method = 'fixed'
    >>> blanco.save()


    >>> template = Template(name="Asa Delta Politeno negra 33cm", type="goods")
    >>> template.default_uom = unit
    >>> template.list_price=Decimal('0')
    >>> template.save()
    >>> asa, = template.products
    >>> asa.cost_price = Decimal('0.0488')
    >>> asa.cost_price_method = 'fixed'
    >>> asa.save()

    >>> template = Template(name="Treball de Confeccio", type="goods")
    >>> template.default_uom = unit
    >>> template.list_price = Decimal('0')
    >>> template.save()
    >>> confection, = template.products
    >>> confection.cost_price = Decimal('0.008')
    >>> confection.cost_price_method = 'fixed'
    >>> confection.save()

    >>> template = Template(name="Colocacio nanses", type="goods")
    >>> template.default_uom = unit
    >>> template.list_price = Decimal('0')
    >>> template.save()
    >>> colocacionanses, = template.products
    >>> colocacionanses.cost_price = Decimal('0.0396')
    >>> colocacionanses.cost_price_method = 'fixed'
    >>> colocacionanses.save()

    >>> template = Template(name="Treball Impressio 1 color", type="goods")
    >>> template.default_uom = unit
    >>> template.list_price = Decimal('0')
    >>> template.save()
    >>> color1, = template.products
    >>> color1.cost_price = Decimal('0.035')
    >>> color1.cost_price_method = 'fixed'
    >>> color1.save()

    >>> template = Template(name="Treball Rebobinar", type="goods")
    >>> template.default_uom = unit
    >>> template.list_price = Decimal('0')
    >>> template.save()
    >>> rebobinar, = template.products
    >>> rebobinar.cost_price = Decimal('0.0073')
    >>> rebobinar.cost_price_method = 'fixed'
    >>> rebobinar.save()

    >>> template = Template(name="Treball Confecció Triple > 30", type="goods")
    >>> template.default_uom = unit
    >>> template.list_price = Decimal('0')
    >>> template.save()
    >>> triple, = template.products
    >>> triple.cost_price = Decimal('0.0125')
    >>> triple.cost_price_method = 'fixed'
    >>> triple.save()

Create property template::

    >>> Property = Model.get('configurator.property')
    >>> bag = Property(name="Bossa Isotermica", code="iso_bag", type='bom',
    ...    template=True, quantity='1')
    >>> bag.uom = unit
    >>> bag.product_template = production_template
    >>> bag.save()

Finished product::

    >>> exterior = bag.childs.new()
    >>> exterior.name = "Exterior"
    >>> exterior.code = "exterior"
    >>> exterior.type = 'bom'
    >>> exterior.product_template = production_template
    >>> exterior.quantity = '1'
    >>> exterior.uom = unit

    >>> interior = bag.childs.new()
    >>> interior.name = "interior"
    >>> interior.code = "interior"
    >>> interior.type = 'bom'
    >>> interior.product_template = production_template
    >>> interior.quantity = '1'
    >>> interior.uom = unit

    >>> foam_prop = bag.childs.new()
    >>> foam_prop.name = "foam"
    >>> foam_prop.code = "foam"
    >>> foam_prop.type = 'bom'
    >>> foam_prop.product_template = production_template
    >>> foam_prop.quantity = '1'
    >>> foam_prop.uom = unit

    >>> asa_prop = bag.childs.new()
    >>> asa_prop.name = "Asa delta Politeno"
    >>> asa_prop.code = "asa_delta"
    >>> asa_prop.type = 'product'
    >>> asa_prop.product = asa
    >>> asa_prop.uom = asa.default_uom
    >>> asa_prop.quantity = "1"

    >>> conf_prop = bag.childs.new()
    >>> conf_prop.name = "Confeccio Isotermica"
    >>> conf_prop.code = "iso_work"
    >>> conf_prop.type = 'product'
    >>> conf_prop.product = confection
    >>> conf_prop.uom = unit
    >>> conf_prop.quantity = "1"

  	>>> colocacio_prop = bag.childs.new()
    >>> colocacio_prop.name = "Colocacio nanses"
    >>> colocacio_prop.code = "asa_work"
    >>> colocacio_prop.type = 'product'
    >>> colocacio_prop.product = colocacionanses
    >>> colocacio_prop.uom = unit
    >>> colocacio_prop.quantity = "1"

Bossa Exterior:

    >>> fca1 = exterior.childs.new()
    >>> fca1.name = "FCA 1 Exterior"
    >>> fca1.code = "fca1_ext"
    >>> fca1.type = 'function'
    >>> fca1.quantity = "fcm_ext*ancho_ext/(100.0*tiras_ext)"


    >>> fca2 = exterior.childs.new()
    >>> fca2.name = "FCA 2 Exterior"
    >>> fca2.code = "fca2_ext"
    >>> fca2.type = 'function'
    >>> fca2.quantity = "0.46*widthprov_ext*galgaprov_ext/(100.0*lamina_ext)"


    >>> largo = exterior.childs.new()
    >>> largo.name = "Exterior Largo"
    >>> largo.code = "largo_ext"
    >>> largo.type = 'number'
    >>> largo.user_input = True

	  >>> ancho = exterior.childs.new()
    >>> ancho.name = "Exterior Ancho"
    >>> ancho.code = "ancho_ext"
    >>> ancho.type = 'number'
    >>> ancho.user_input = True

    >>> galga = exterior.childs.new()
    >>> galga.name = "Exterior Galga"
    >>> galga.code = "galga_ext"
    >>> galga.type = 'number'
    >>> galga.user_input = True

    >>> tiras = exterior.childs.new()
    >>> tiras.name = "Exterior Tiras"
    >>> tiras.code = "tiras_ext"
    >>> tiras.type = 'number'
    >>> tiras.user_input = True

    >>> fcm = exterior.childs.new()
    >>> fcm.name = "Exterior FCM"
    >>> fcm.code = "fcm_ext"
    >>> fcm.type = 'number'
    >>> fcm.user_input = True

    >>> grosor = exterior.childs.new()
    >>> grosor.name = "Exterior grosor"
    >>> grosor.code = "grosor_ext"
    >>> grosor.type = 'number'
    >>> grosor.user_input = True

    >>> lamina = exterior.childs.new()
    >>> lamina.name = "Exterior lamina"
    >>> lamina.code = "lamina_ext"
    >>> lamina.type = 'number'
    >>> lamina.user_input = True

    >>> triple_prop = exterior.childs.new()
    >>> triple_prop.name = "Treball de confeccio triple"
    >>> triple_prop.code = "triple"
    >>> #triple_prop.type = 'operation'
    >>> triple_prop.type = 'product'
    >>> triple_prop.product= triple
    >>> # triple_prop.work_center_category = confeccio
    >>> # triple_prop.operation_type = ot_confeccio
    >>> triple_prop.quantity = '1'
    >>> triple_prop.uom = unit
    >>> #triple_prop.price_category = work

    >>> rebobinar_prop = exterior.childs.new()
    >>> rebobinar_prop.name = "Treball de rebobinar"
    >>> rebobinar_prop.code = "rebobinar_ext"
    >>> rebobinar_prop.type = 'product'
    >>> rebobinar_prop.product= rebobinar
    >>> rebobinar_prop.quantity = "fca1_ext"
    >>> #rebobinar_prop.work_center_category = rebobinar
    >>> #rebobinar_prop.operation_type = ot_rebobinar
    >>> rebobinar_prop.uom = unit
    >>> #rebobinar_prop.price_category = work

    >>> color1_prop = exterior.childs.new()
    >>> color1_prop.name = "Treball Impresio color1"
    >>> color1_prop.code = "color_ext"
    >>> color1_prop.type = 'product'
    >>> color1_prop.product= color1
    >>> color1_prop.quantity = "fca1_ext"
    >>> color1_prop.uom = unit
    >>> #color1_prop.work_center_category = color
    >>> #color1_prop.operation_type = ot_color
    >>> #color1_prop.price_category = work


Material Base A:

	  >>> matA = exterior.childs.new()
    >>> matA.name = "Material Base Bossa Exterior"
    >>> matA.code = "mat_ext"
    >>> matA.type = "purchase_product"
    >>> matA.uom = m
    >>> matA.quantity = "0.46*widthprov_ext*galga_ext/(100*lamina_ext)"
    >>> matA.product_template = purchase_template_km
    >>> matA.object_expression = "{'info_ratio':'fca2_ext'}"

    >>> supplier_width = matA.childs.new()
    >>> supplier_width.name = "Exterior Supplier Width"
    >>> supplier_width.code = "widthprov_ext"
    >>> supplier_width.type = "number"
    >>> supplier_width.user_input = True

    >>> supplier_galga = matA.childs.new()
    >>> supplier_galga.name = "Exterior Supplier Galga"
    >>> supplier_galga.code = "galgaprov_ext"
    >>> supplier_galga.type = "number"
    >>> supplier_galga.user_input = True


Semi Elaborate Material A::

    >>> material = matA.childs.new()
    >>> material.name = "Exterior Material"
    >>> material.code = "material_ext"
    >>> material.user_input = True
    >>> material.type = "options"

    >>> blanco_prop = material.childs.new()
    >>> blanco_prop.name = "B.P. Blanco > 40 xm"
    >>> blanco_prop.code = "blanco_ext"
    >>> blanco_prop.type = "product"
    >>> blanco_prop.product = blanco
    >>> blanco_prop.uom = kg
    >>> blanco_prop.quantity = "fca2_ext"
    >>> #blanco_prop.price_category = price_material

Bossa Interior:

    >>> fcaa1 = interior.childs.new()
    >>> fcaa1.name = "Interior FCA 1"
    >>> fcaa1.code = "fca1_int"
    >>> fcaa1.type = 'function'
    >>> fcaa1.quantity = "fcm_int*ancho_int/(100*tiras_int)"

    >>> fcaa2 = interior.childs.new()
    >>> fcaa2.name = "FCA 2 interior"
    >>> fcaa2.code = "fca2_int"
    >>> fcaa2.type = 'function'
    >>> fcaa2.quantity = "0.45*widthprov_int*galgaprov_int/(100*lamina_int)"

    >>> largo_int = interior.childs.new()
    >>> largo_int.name = "Interior Largo"
    >>> largo_int.code = "largo_int"
    >>> largo_int.type = 'number'
    >>> largo_int.user_input = True

	  >>> ancho_int = interior.childs.new()
    >>> ancho_int.name = "Interior Ancho"
    >>> ancho_int.code = "ancho_int"
    >>> ancho_int.type = 'number'
    >>> ancho_int.user_input = True

    >>> galga_int = interior.childs.new()
    >>> galga_int.name = "Exterior Galga"
    >>> galga_int.code = "galga_int"
    >>> galga_int.type = 'number'
    >>> galga_int.user_input = True

    >>> tiras_int = interior.childs.new()
    >>> tiras_int.name = "Interior Tiras"
    >>> tiras_int.code = "tiras_int"
    >>> tiras_int.type = 'number'
    >>> tiras_int.user_input = True

    >>> fcm_int = interior.childs.new()
    >>> fcm_int.name = "Interior FCM"
    >>> fcm_int.code = "fcm_int"
    >>> fcm_int.type = 'number'
    >>> fcm_int.user_input = True


    >>> lamina_int = interior.childs.new()
    >>> lamina_int.name = "Interior lamina"
    >>> lamina_int.code = "lamina_int"
    >>> lamina_int.type = 'number'
    >>> lamina_int.user_input = True

    >>> triple_prop = interior.childs.new()
    >>> triple_prop.name = "Treball de confeccio triple"
    >>> triple_prop.code = "triple"
    >>> triple_prop.type = 'product'
    >>> triple_prop.product= triple
    >>> triple_prop.quantity = '1'
    >>> triple_prop.uom = unit
    >>> #triple_prop.work_center_category = confeccio
    >>> #triple_prop.operation_type = ot_confeccio
    >>> #triple_prop.price_category = work

    >>> rebobinar_prop = interior.childs.new()
    >>> rebobinar_prop.name = "Treball de rebobinar"
    >>> rebobinar_prop.code = "rebobinar"
    >>> rebobinar_prop.type = 'product'
    >>> rebobinar_prop.product= rebobinar
    >>> rebobinar_prop.quantity = "fca1_int"
    >>> rebobinar_prop.uom = unit
    >>> #rebobinar_prop.work_center_category = rebobinar
    >>> #rebobinar_prop.operation_type = ot_rebobinar
    >>> #rebobinar_prop.price_category = work

Material Base Interior:

	>>> matA = interior.childs.new()
    >>> matA.name = "Material Base Bossa Interior"
    >>> matA.code = "mat_int"
    >>> matA.type = "purchase_product"
    >>> matA.uom = m
    >>> matA.quantity = "fca1_int"
    >>> matA.product_template = purchase_template_km
    >>> matA.object_expression = "{'info_ratio':'fca2_int'}"


    >>> supplier_width = matA.childs.new()
    >>> supplier_width.name = "Interior Supplier Width"
    >>> supplier_width.code = "widthprov_int"
    >>> supplier_width.type = "number"
    >>> supplier_width.user_input = True

    >>> supplier_galga = matA.childs.new()
    >>> supplier_galga.name = "Interior Supplier Galga"
    >>> supplier_galga.code = "galgaprov_int"
    >>> supplier_galga.type = "number"
    >>> supplier_galga.user_input = True


Semi Elaborate Material A::

    >>> material = matA.childs.new()
    >>> material.name = "Exterior Material"
    >>> material.code = "material_int"
    >>> material.user_input = True
    >>> material.type = "options"

    >>> blanco_prop = material.childs.new()
    >>> blanco_prop.name = "B.P. Blanco > 40 xm"
    >>> blanco_prop.code = "blanco_int"
    >>> blanco_prop.type = "product"
    >>> blanco_prop.product = blanco
    >>> blanco_prop.uom = kg
    >>> blanco_prop.quantity = "fca1_int * fca2_int"
    >>> #blanco_prop.price_category = price_material

Foam:

	  >>> material = foam_prop.childs.new()
    >>> material.name = "Material Foam"
    >>> material.code = "material_foam"
    >>> material.user_input = True
    >>> material.type = "options"

    >>> blanco_prop = material.childs.new()
    >>> blanco_prop.name = "Foam 150 cm i 2 mm gruix"
    >>> blanco_prop.code = "foam_150x2"
    >>> blanco_prop.type = "product"
    >>> blanco_prop.product = foam
    >>> blanco_prop.uom = kg
    >>> blanco_prop.quantity = "(largo_cortes_foam/100)/(largo_foam*cortes_foam)*1000"
    >>> #blanco_prop.price_category = price_material

	  >>> largo_foam = foam_prop.childs.new()
    >>> largo_foam.name = "Foam Largo"
    >>> largo_foam.code = "largo_foam"
    >>> largo_foam.type = 'number'
    >>> largo_foam.user_input = True

	  >>> ancho_foam = foam_prop.childs.new()
    >>> ancho_foam.name = "Foam Ancho"
    >>> ancho_foam.code = "ancho_foam"
    >>> ancho_foam.type = 'number'
    >>> ancho_foam.user_input = True

    >>> cortes_foam = foam_prop.childs.new()
    >>> cortes_foam.name = "Cortes foam"
    >>> cortes_foam.code = "cortes_foam"
    >>> cortes_foam.type = 'number'
    >>> cortes_foam.user_input = True

    >>> ancho_cortes_foam = foam_prop.childs.new()
    >>> ancho_cortes_foam.name = "Ancho Cortes Foam"
    >>> ancho_cortes_foam.code = "ancho_cortes_foam"
    >>> ancho_cortes_foam.type = 'number'
    >>> ancho_cortes_foam.user_input = True

    >>> largo_cortes_foam = foam_prop.childs.new()
    >>> largo_cortes_foam.name = "Interior FCM"
    >>> largo_cortes_foam.code = "largo_cortes_foam"
    >>> largo_cortes_foam.type = 'number'
    >>> largo_cortes_foam.user_input = True


Save property::

    >>> bag.save()
    >>> bag.reload()

Create Design::

    >>> Design = Model.get('configurator.design')
    >>> Attribute = Model.get('configurator.design.attribute')
    >>> design = Design(name='Bossa isotermica 1', code = 'isotermica 1', template=bag,
    ...    currency=euro, quotation_uom=unit)
    >>> design.party = party
    >>> design.save()
    >>> design.click('update')

Fill Design Exterior::

	>>> ancho_ext, = Attribute.find([('property.code', '=', 'ancho_ext')])
	>>> ancho_ext.number = 45
	>>> ancho_ext.save()
	>>> largo_ext, = Attribute.find([('property.code', '=', 'largo_ext')])
	>>> largo_ext.number = 45
	>>> largo_ext.save()
	>>> galga_ext, = Attribute.find([('property.code', '=', 'galga_ext')])
	>>> galga_ext.number = 300
	>>> galga_ext.save()
	>>> tiras_ext, = Attribute.find([('property.code', '=', 'tiras_ext')])
	>>> tiras_ext.number = 1
	>>> tiras_ext.save()
	>>> fcm_ext, = Attribute.find([('property.code', '=', 'fcm_ext')])
	>>> fcm_ext.number = 1.01
	>>> fcm_ext.save()
	>>> lamina_ext, = Attribute.find([('property.code', '=', 'lamina_ext')])
	>>> lamina_ext.number = 2
	>>> lamina_ext.save()

	>>> width_prov_ext, = Attribute.find([('property.code', '=', 'widthprov_ext')])
	>>> width_prov_ext.number = 93
	>>> width_prov_ext.save()
	>>> galga_prov_ext, = Attribute.find([('property.code', '=', 'galgaprov_ext')])
	>>> galga_prov_ext.number = 300
	>>> galga_prov_ext.save()

	>>> mat_ext, = Attribute.find([('property.code', '=', 'material_ext')])
	>>> option_ext, = Property.find([('code', '=', 'blanco_ext')])
	>>> mat_ext.option = option_ext
	>>> mat_ext.save()


Fill Design Interior::

	>>> ancho_int, = Attribute.find([('property.code', '=', 'ancho_int')])
	>>> ancho_int.number = 41
	>>> ancho_int.save()
	>>> largo_int, = Attribute.find([('property.code', '=', 'largo_int')])
	>>> largo_int.number = 45
	>>> largo_int.save()
	>>> galga_int, = Attribute.find([('property.code', '=', 'galga_int')])
	>>> galga_int.number = 200
	>>> galga_int.save()
	>>> tiras_int, = Attribute.find([('property.code', '=', 'tiras_int')])
	>>> tiras_int.number = 1
	>>> tiras_int.save()
	>>> fcm_int, = Attribute.find([('property.code', '=', 'fcm_int')])
	>>> fcm_int.number = 1.01
	>>> fcm_int.save()
	>>> lamina_int, = Attribute.find([('property.code', '=', 'lamina_int')])
	>>> lamina_int.number = 2
	>>> lamina_int.save()

	>>> width_prov_int, = Attribute.find([('property.code', '=', 'widthprov_int')])
	>>> width_prov_int.number = 93
	>>> width_prov_int.save()
	>>> galga_prov_int, = Attribute.find([('property.code', '=', 'galgaprov_int')])
	>>> galga_prov_int.number = 200
	>>> galga_prov_int.save()

	>>> mat_int, = Attribute.find([('property.code', '=', 'material_int')])
	>>> option_int, = Property.find([('code', '=', 'blanco_int')])
	>>> mat_int.option = option_int
	>>> mat_int.save()


Fill Foam::

	>>> fill_largo_foam, = Attribute.find([('property.code', '=', 'largo_foam')])
	>>> fill_largo_foam.number = 250
	>>> fill_largo_foam.save()
	>>> fill_ancho_foam, = Attribute.find([('property.code', '=', 'ancho_foam')])
	>>> fill_ancho_foam.number = 150
	>>> fill_ancho_foam.save()
	>>> fill_cortes_foam, = Attribute.find([('property.code', '=', 'cortes_foam')])
	>>> fill_cortes_foam.number = 3
	>>> fill_cortes_foam.save()
	>>> fill_ancho_cortes_foam, = Attribute.find([('property.code', '=', 'ancho_cortes_foam')])
	>>> fill_ancho_cortes_foam.number = 47
	>>> fill_ancho_cortes_foam.save()
	>>> fill_largo_cortes_foam, = Attribute.find([('property.code', '=', 'largo_cortes_foam')])
	>>> fill_largo_cortes_foam.number = 96
	>>> fill_largo_cortes_foam.save()
	>>> mat_foam, = Attribute.find([('property.code', '=', 'material_foam')])
	>>> option_foam, = Property.find([('code', '=', 'foam_150x2')])
	>>> mat_foam.option = option_foam
	>>> mat_foam.save()


Fill Quotation::

  >>> Quotation = Model.get('configurator.quotation.line')
  >>> quotation = Quotation()
  >>> quotation.design = design
  >>> quotation.quantity = 1
  >>> quotation.save()

  >>> design.click('create_prices')
  >>> quotation.reload()
  >>> design.click('process')
  >>> design.reload()
  >>> len(design.product.boms)
  1
  >>> bom, = design.product.boms
  >>> len(bom.bom.inputs)
  3
