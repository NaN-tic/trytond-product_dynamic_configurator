from trytond.model import (Workflow, ModelView, ModelSQL,
    DeactivableMixin, fields, sequence_ordered)
from trytond.pool import Pool, PoolMeta
try:
    from jinja2 import Template as Jinja2Template
    jinja2_loaded = True
except ImportError:
    jinja2_loaded = False



class JinjaTemplate(ModelSQL, ModelView):
    'Jinja Template'
    __name__ = 'configurator.jinja_template'

    name = fields.Char('Name', required=True)
    type_= fields.Selection([('macro', 'Macro'), ('base', 'Base')], 'Type',
        required=True)
    macros = fields.Many2Many('jinja_template-jinja_template_macro',
        'template', 'macro', 'Macros',
        domain = [('type_', '=', 'macro')])
    jinja = fields.Text('Jinja Expression')
    full_content = fields.Function(fields.Text('Full Content'),
        'get_full_content')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('name', 'ASC'))


    def get_full_content(self, name=None):
        text = [x.jinja for x in self.macros if x]
        text.append(self.jinja)
        return "\n".join(text)

    def render(self, record):
        template = Jinja2Template(self.full_content, trim_blocks=True)
        res = template.render(record)
        if res:
            res = res.replace('\t', '').replace('\n', '').strip()
        return res


class JinjaTemplateMacros(ModelSQL):
    'Jinja template - Jinja template macros'
    __name__ = 'jinja_template-jinja_template_macro'

    template = fields.Many2One('configurator.jinja_template', 'Template',
        domain = [('type_', '=', 'base')], required=True, ondelete='CASCADE')
    macro = fields.Many2One('configurator.jinja_template', 'Macro',
        domain = [('type_', '=', 'macro')], required=True,  ondelete='CASCADE')