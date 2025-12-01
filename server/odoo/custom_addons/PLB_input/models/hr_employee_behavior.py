from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Behavior tags for the employee (many2many reusing existing crm.lead.tag records)
    behavior = fields.Many2many(
        'crm.lead.tag', 'hr_employee_behavior_rel', 'employee_id', 'tag_id',
        string='Behavior', help='Tag-style behavior entries (enter multiple)'
    )
