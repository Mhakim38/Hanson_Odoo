from odoo import fields, models

class EstateGate(models.Model):
    _name = "estate.gate"
    _description = "Gate"

    name = fields.Char(required=True)
    location_gps = fields.Char()
    property_id = fields.Many2one('estate.property')
