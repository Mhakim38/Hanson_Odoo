from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    user_type = fields.Selection([
        ('resident', 'Resident'),
        ('guard', 'Guard'),
    ], string="User Type")
