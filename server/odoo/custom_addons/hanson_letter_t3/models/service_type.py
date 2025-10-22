from odoo import models, fields, api

class ServiceType(models.Model):
    _name = 'service.type'
    _description = 'Service Type'

    name = fields.Char(string='Service Type', required=True)
    description = fields.Text(string='Description')
