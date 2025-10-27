from odoo import fields, models

class ResPartner(models.Model):
    _inherit = "res.partner"

    is_owner = fields.Boolean(string="Is Owner", default=False)
    is_resident = fields.Boolean(string="Is Resident", default=False)
    is_tenant = fields.Boolean(string="Is Tenant", default=False)

    id_type = fields.Selection([
        ('ic', 'IC/MyKad'),
        ('passport', 'Passport'),
        ('license', 'License'),
        ('other', 'Other')
    ], string="ID Type")

    id_number = fields.Char(string="ID Number")
    valid_from = fields.Date(string="Valid From")
    valid_to = fields.Date(string="Valid To")

    # Updated One2many (already correct)
    estate_unit_ids = fields.One2many(
        'estate.unit',
        'owner_id',
        string="Owned Units"
    )
