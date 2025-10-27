from odoo import api, fields, models

class EstateUnit(models.Model):
    _name = "estate.unit"
    _description = "Property Unit"
    _rec_name = "display_name"

    name = fields.Char(string="Lot No.", required=True)
    property_id = fields.Many2one('estate.property', required=True)
    street = fields.Char()
    bedrooms = fields.Integer()
    status = fields.Selection([
        ('vacant', 'Vacant'),
        ('occupied', 'Occupied')
    ], default='vacant')

    # Changed from Many2many to Many2one
    owner_id = fields.Many2one(
        'res.partner',
        string="Owner",
        domain="[('is_company', '=', False)]"  # optional filter
    )

    resident_partner_ids = fields.Many2many(
        'res.partner',
        'estate_unit_resident_rel',
        'unit_id',
        'partner_id',
        string="Residents"
    )

    vehicle_ids = fields.One2many('estate.vehicle', 'unit_id')
    display_name = fields.Char(compute="_compute_display_name", store=False)

    @api.depends('name', 'property_id.name')
    def _compute_display_name(self):
        for r in self:
            if r.name and r.property_id:
                r.display_name = f"{r.name} / {r.property_id.name}"
            else:
                r.display_name = r.name or r.property_id.name or ''

    def name_get(self):
        result = []
        for r in self:
            name = r.name or ''
            if r.property_id:
                name = f"{r.name} / {r.property_id.name}"
            result.append((r.id, name))
        return result

    unit_type = fields.Selection([
        ('type_a1', 'Type A1 (3,638 sq ft)'),
        ('type_a2', 'Type A2 (3,519 sq ft)'),
        ('type_b', 'Type B (3,810 sq ft)'),
        ('type_c1_e1', 'Type C1/E1 (4,370 sq ft)'),
        ('type_c2_e2', 'Type C2/E2 (4,434 sq ft)'),
    ], string='Unit Type', required=True)
