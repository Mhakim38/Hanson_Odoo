from odoo import models, fields

class EmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    office = fields.Char(string='Office')
    employee_id_bio = fields.Char(string='Employee ID')
    nickname = fields.Char(string='Nickname')
