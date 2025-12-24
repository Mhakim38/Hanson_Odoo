from odoo import models, fields, api


class TargetKPISettings(models.Model):
    _name = 'target.kpi.settings'
    _description = 'Target KPI Settings'

    name = fields.Char(string='Settings', default='Target KPI Settings', readonly=True)
    yearly_target = fields.Integer(
        string='Company Yearly Target',
        default=0,
        help='Overall company yearly target'
    )
    employee_target_ids = fields.One2many(
        'employee.target.line',
        'settings_id',
        string='Employee Targets'
    )

    @api.model
    def get_settings(self):
        """Get or create the singleton settings record"""
        settings = self.search([], limit=1)
        if not settings:
            settings = self.create({'name': 'Target KPI Settings'})

        # Auto-populate employees if not already added
        existing_employee_ids = settings.employee_target_ids.mapped('employee_id.id')
        all_employees = self.env['hr.employee'].search([])

        for employee in all_employees:
            if employee.id not in existing_employee_ids:
                self.env['employee.target.line'].create({
                    'settings_id': settings.id,
                    'employee_id': employee.id,
                    'personal_target': 0
                })

        return settings


class EmployeeTargetLine(models.Model):
    _name = 'employee.target.line'
    _description = 'Employee Target Line'

    settings_id = fields.Many2one('target.kpi.settings', string='Settings', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    personal_target = fields.Integer(
        string='Personal Target',
        default=0,
        help='Personal yearly sales target for this employee'
    )


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    target_yearly = fields.Integer(
        string='Yearly Target',
        default=0,
        help='Yearly sales target for this employee',
        compute='_compute_target_yearly',
        store=True
    )

    @api.depends('name')
    def _compute_target_yearly(self):
        """Get target from employee target line"""
        for employee in self:
            target_line = self.env['employee.target.line'].search([
                ('employee_id', '=', employee.id)
            ], limit=1)
            employee.target_yearly = target_line.personal_target if target_line else 0

