from datetime import timedelta, datetime, time

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import base64
import qrcode
from io import BytesIO
import uuid


class EstateVisit(models.Model):
    _name = "estate.visit"
    _description = "Visit"
    _inherit = ['mail.thread']

    # The host who invited the visitor. (Keep a single definition.)
    host_id = fields.Many2one(
        'res.partner',
        string="Host",
        required=True,
        domain="[('is_company', '=', False)]",
        help="The person (resident or owner) who invited the visitor."
    )

    # Visitor is a many2one to estate.visitor. We'll restrict selectable visitors
    # to those that have their host_id set to the chosen host using an onchange.
    id_number = fields.Char(related="visitor_id.id_number", string="I   D Number", index=True, readonly=False, tracking=True)
    name = fields.Char(related="visitor_id.name")
    visitor_id = fields.Many2one('estate.visitor', required=True)
    visitor_vehicle_ids = fields.Many2one('estate.visitor.vehicle', string="Vehicles")

    # @api.onchange('visitor_id')
    # def _onchange_visitor_id(self):
    #     """When a visitor is chosen, auto-fill host_id to the visitor's assigned host."""
    #     if self.visitor_id and getattr(self.visitor_id, 'host_id', False):
    #         self.host_id = self.visitor_id.host_id
    #         # Ensure the unit domain is updated when visitor sets the host
    #         return self._onchange_host()
    #     else:
    #         self.host_id = False
    #         # When host was cleared, also return domain (no restriction)
    #         return self._onchange_host()

    @api.onchange('host_id')
    def _onchange_host(self):
        """Return a domain for `unit_id` based on selected host.

        Shows units where host is either the owner or in resident_partner_ids.
        """
        if self.host_id:
            # Clear unit if it doesn't belong to the selected host
            if self.unit_id and getattr(self.unit_id, 'owner_id', False) and self.unit_id.owner_id.id != self.host_id.id:
                self.unit_id = False
            # Domain: owner = host OR resident_partner_ids contains host
            return {'domain': {'unit_id': ['|', ('owner_id', '=', self.host_id.id), ('resident_partner_ids', 'in', self.host_id.id)]}}
        return {'domain': {'unit_id': []}}

    unit_id = fields.Many2one(
        'estate.unit',
        string="Unit",
        required=True,
        # Domain is controlled dynamically via onchange(host_id, property_id) in the form view
    )
    purpose = fields.Selection([
        ('', 'Please select visitor type'),
        ('visitor', 'Visitor'),
        ('pickup', 'Pickup'),
        ('contractor/service provider', 'Contractor/Service Provider'),
    ], string="Visitor Type", required=True)

    schedule_from = fields.Datetime(required=True, default=fields.Datetime.now)
    schedule_to = fields.Datetime()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('check_in', 'Checked In'),
        ('check_out', 'Checked Out'),
        ('cancel', 'Cancelled')
    ], default='scheduled', tracking=True)
    gate_in_id = fields.Many2one('estate.gate', string="Gate In")
    gate_out_id = fields.Many2one('estate.gate', string="Gate Out")
    check_in_at = fields.Datetime()
    check_out_at = fields.Datetime()
    qr_token = fields.Char(index=True, copy=False)
    qr_expiry = fields.Datetime()
    qr_image = fields.Binary("QR Code", readonly=True, attachment=True)
    photos = fields.Many2many('ir.attachment', string="Photos")

    is_adhoc = fields.Boolean(default=False, index=True)
    origin = fields.Selection([
        ('pre_reg', 'Pre-Registered'),
        ('adhoc', 'Ad-Hoc')
    ], default='pre_reg', required=True)
    check_in_mode = fields.Selection([
        ('qr', 'QR'),
        ('plate', 'Plate'),
        ('manual', 'Manual')
    ], default='manual')
    valid_minutes = fields.Integer(default=120)
    badge_no = fields.Char(readonly=True, copy=False)

    # ----------------------------
    # Constraints
    # ----------------------------
    @api.constrains('schedule_from', 'schedule_to')
    def _check_window(self):
        for r in self:
            if r.schedule_from and r.schedule_to and r.schedule_to < r.schedule_from:
                raise ValidationError(_("Visit end time must be after start time."))

    @api.constrains('valid_minutes')
    def _check_valid_minutes(self):
        for r in self:
            if r.valid_minutes and r.valid_minutes <= 0:
                raise ValidationError(_("Validity minutes must be positive."))

    @api.constrains('host_id', 'visitor_id')
    def _check_visitor_host_match(self):
        # ✅ Skip check kalau datang dari guard context
        if self.env.context.get('from_guard_portal'):
            return

    # ----------------------------
    # Helpers
    # ----------------------------
    def _assign_badge(self):
        for r in self:
            if not r.badge_no:
                r.badge_no = self.env['ir.sequence'].next_by_code('estate.visit.badge') or '/'

    def _generate_qr_code(self):
        """Generate a unique QR code for this visit"""
        for r in self:
            # Create a unique token and expiry
            r.qr_token = str(uuid.uuid4())
            # Set qr_expiry to the end of the scheduled day (visitor's schedule_from date)
            try:
                if getattr(r, 'schedule_from', False):
                    # Convert schedule_from (which may be str or datetime) to a date and set expiry to 23:59:59 of that date
                    sched = r.schedule_from
                    try:
                        if isinstance(sched, str):
                            sched_dt = fields.Datetime.from_string(sched)
                        else:
                            sched_dt = sched
                        sched_date = sched_dt.date()
                        expiry_dt = datetime.combine(sched_date, time.max)
                        # store expiry as a datetime string for consistent storage and comparison
                        try:
                            r.qr_expiry = fields.Datetime.to_string(expiry_dt)
                        except Exception:
                            r.qr_expiry = expiry_dt
                    except Exception:
                        # Fallback to default valid_minutes if any
                        r.qr_expiry = fields.Datetime.now() + timedelta(minutes=r.valid_minutes or 120)
                else:
                    r.qr_expiry = fields.Datetime.now() + timedelta(minutes=r.valid_minutes or 120)
            except Exception:
                r.qr_expiry = fields.Datetime.now() + timedelta(minutes=r.valid_minutes or 120)

            # Example: You can use a portal URL or internal validation route
            qr_url = f"{r.env['ir.config_parameter'].sudo().get_param('web.base.url')}/visitor/verify/{r.qr_token}"

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(qr_url)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')

            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Save to record
            r.qr_image = qr_image_base64

    # ----------------------------
    # Overrides
    # ----------------------------
    @api.model
    def create(self, vals):
        record = super(EstateVisit, self).create(vals)
        record._assign_badge()
        record._generate_qr_code()
        return record

    # ----------------------------
    # Actions
    # ----------------------------
    def action_checkin_adhoc(self):
        for r in self:
            if r.visitor_id.blacklisted:
                raise UserError(_("Visitor is blacklisted."))
        now = fields.Datetime.now()
        self.write({
            'state': 'check_in',
            'check_in_at': now,
            'schedule_from': now - timedelta(minutes=5),
            'schedule_to': now + timedelta(minutes=self.valid_minutes or 120),
            'origin': 'adhoc',
            'is_adhoc': True,
        })
        self._assign_badge()
        self._generate_qr_code()
        return True

    # ----------------------------
    # Guard Actions
    # ----------------------------
    def action_guard_checkin(self):
        for r in self:
            if r.state != 'scheduled':
                raise UserError(_("Only scheduled visits can be checked in."))
            if r.visitor_id.blacklisted:
                raise UserError(_("Visitor is blacklisted and cannot be checked in."))

            r.write({
                'state': 'check_in',
                'check_in_at': fields.Datetime.now(),
            })
        return True

    def action_guard_checkout(self):
        for r in self:
            if r.state != 'check_in':
                raise UserError(_("Only checked-in visits can be checked out."))
            r.write({
                'state': 'check_out',
                'check_out_at': fields.Datetime.now(),
            })
        return True
