from odoo import fields, models

class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Property"

    name = fields.Char(
        string="Residential Area",
        related='property_id.name',
        store=True,
        readonly=False
    )
    code = fields.Char()
    address = fields.Char()
    company_id = fields.Many2one(
        'res.company',
        string="R.A",
        default=lambda self: self.env.company.id,
        domain=[('partner_id.is_company', '=', False)],
    )

    property_id = fields.Many2one(
        'res.partner',
        string='Residential Name',
        domain=[('is_company', '=', True)],
        help='Select the property (company) this unit belongs to.'
    )
    unit_ids = fields.One2many('estate.unit', 'property_id')

    unit_type = fields.Selection([
        ('type_a1', 'Type A1 (3,638 sq ft)'),
        ('type_a2', 'Type A2 (3,519 sq ft)'),
        ('type_b', 'Type B (3,810 sq ft)'),
        ('type_c1_e1', 'Type C1/E1 (4,370 sq ft)'),
        ('type_c2_e2', 'Type C2/E2 (4,434 sq ft)'),
    ], string='Unit Type')