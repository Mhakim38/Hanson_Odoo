from odoo import models, fields

class CrmPort(models.Model):
    _name = 'crm.port'
    _description = 'Port Information'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name of the Place', required=True)
    city = fields.Char(string='City')
    state = fields.Char(string='State')
    country = fields.Char(string='Country')
    type = fields.Selection([
        ('airport', 'Airport'),
        ('seaport', 'Seaport'),
        ('landport', 'Landport'),
        ('others', 'Others')
    ], string='Type', required=True)
