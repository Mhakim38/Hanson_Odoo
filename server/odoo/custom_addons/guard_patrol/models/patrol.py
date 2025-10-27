from odoo import api, fields, models
from odoo.tools import date_utils

class PatrolRoute(models.Model):
    _name = "patrol.route"
    _description = "Patrol Route"

    name = fields.Char(required=True)
    property_id = fields.Many2one('estate.property')
    description = fields.Text()
    active = fields.Boolean(default=True)
    checkpoint_ids = fields.One2many('patrol.checkpoint', 'route_id')

class PatrolCheckpoint(models.Model):
    _name = "patrol.checkpoint"
    _description = "Patrol Checkpoint"
    _order = "sequence asc, id asc"

    name = fields.Char(required=True)
    route_id = fields.Many2one('patrol.route', required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    qr_code = fields.Char()
    nfc_uid = fields.Char()
    geo_lat = fields.Float()
    geo_lng = fields.Float()
    sla_minutes = fields.Integer(default=10)

class PatrolTour(models.Model):
    _name = "patrol.tour"
    _description = "Patrol Tour"

    name = fields.Char(related='property_id.name')
    property_id = fields.Many2one('estate.property')
    route_id = fields.Many2one('patrol.route', required=True)
    assigned_user_id = fields.Many2one('hr.employee', string="Assigned Guard", required=True)
    start_planned = fields.Datetime(required=True, default=fields.Datetime.now)
    end_planned = fields.Datetime()
    start_actual = fields.Datetime()
    end_actual = fields.Datetime()
    state = fields.Selection([('planned','Planned'),('in_progress','In Progress'),('done','Done'),('late','Late')], default='planned')
    log_ids = fields.One2many('patrol.log', 'tour_id')
    incident_ids = fields.One2many('security.incident', 'tour_id')

class PatrolLog(models.Model):
    _name = "patrol.log"
    _description = "Patrol Log"

    tour_id = fields.Many2one('patrol.tour', required=True, ondelete="cascade")
    checkpoint_id = fields.Many2one('patrol.checkpoint', required=True)
    user_id = fields.Many2one('res.users', default=lambda s: s.env.user.id)
    scan_time = fields.Datetime(default=fields.Datetime.now)
    geo_lat = fields.Float()
    geo_lng = fields.Float()
    on_time = fields.Boolean(compute="_compute_on_time", store=True)
    note = fields.Char()
    photo_ids = fields.Many2many('ir.attachment')

    @api.depends('scan_time','checkpoint_id.sla_minutes','tour_id.start_planned')
    def _compute_on_time(self):
        for r in self:
            if not (r.tour_id.start_planned and r.checkpoint_id.sla_minutes):
                r.on_time = True
            else:
                expected = r.tour_id.start_planned + date_utils.relativedelta(minutes=r.checkpoint_id.sla_minutes)

                r.on_time = (r.scan_time or fields.Datetime.now()) <= expected

class SecurityIncident(models.Model):
    _name = "security.incident"
    _description = "Security Incident"
    _inherit = ['mail.thread']

    title = fields.Char(required=True, tracking=True)
    severity = fields.Selection([('low','Low'),('med','Medium'),('high','High')], default='low')
    reported_at = fields.Datetime(default=fields.Datetime.now)
    description = fields.Text()
    photo_ids = fields.Many2many('ir.attachment')
    tour_id = fields.Many2one('patrol.tour')
    state = fields.Selection([('new','New'),('investigating','Investigating'),('closed','Closed')], default='new', tracking=True)

class EstateGuard(models.Model):
    _name = 'estate.guard'
    _description = 'Estate Security Guard'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Guard Name", required=True, tracking=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True,
        help="Link to the HR employee record for this guard."
    )
    property_id = fields.Many2one(
        'res.partner',
        string="Property",
        domain=[('is_company', '=', True)],
        help="Property where the guard is assigned."
    )

    company_id = fields.Many2one(
        'res.company',
        string="JMB",
        default=lambda self: self.env.company.id,
        domain=[('partner_id.is_company', '=', False)],
    )

    shift = fields.Selection([
        ('morning', 'Morning'),
        ('evening', 'Evening'),
        ('night', 'Night'),
    ], string="Shift", tracking=True)

    active = fields.Boolean(default=True)

    # ✅ Corrected: hr.employee uses 'mobile_phone' in Odoo 17
    phone = fields.Char(related='employee_id.mobile_phone', string="Phone", readonly=True)

    # Keep employee image
    image_128 = fields.Image(related='employee_id.image_128', readonly=True)

    note = fields.Text(string="Remarks")

    _sql_constraints = [
        ('unique_employee', 'unique(employee_id)', 'Each employee can only be assigned to one guard record.')
    ]

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_id:
                rec.name = rec.employee_id.name
