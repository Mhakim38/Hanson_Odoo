from odoo import fields, models

class EstateVisitor(models.Model):
    _name = "estate.visitor"
    _description = "Visitor"
    _inherit = ['mail.thread']

    _sql_constraints = [
        ('id_number_unique', 'unique(id_number)', 'ID Number must be unique!')
    ]

    name = fields.Char(required=True, tracking=True)
    id_type = fields.Selection([
        ('ic', 'IC/MyKad'),
        ('passport', 'Passport'),
        ('license', 'License'),
        ('other', 'Other')
    ], default='ic', tracking=True)
    id_number = fields.Char(index=True, tracking=True)
    phone = fields.Char()
    blacklisted = fields.Boolean(default=False)
    notes = fields.Text()
    # The host/resident this visitor is assigned to. Required per your request.
    host_id = fields.Many2one(
        'res.partner',
        string='Host / Resident',
        ondelete='restrict'
    )


class EstateVisitorVehicle(models.Model):
    _name = "estate.visitor.vehicle"
    _description = "Visitor Vehicle"

    name = fields.Char(related="plate_no")
    visitor_id = fields.Many2one('estate.visitor', required=True, ondelete="cascade")
    plate_no = fields.Char(index=True)
    make = fields.Char()
    model = fields.Char()
    color = fields.Char()


from datetime import timedelta
from odoo import api, _
from odoo.exceptions import UserError
import base64
import qrcode
from io import BytesIO
import uuid

class EstateVisitorQR(models.Model):
    _inherit = 'estate.visitor'

    qr_token = fields.Char(index=True, copy=False)
    qr_image = fields.Binary("QR Code", readonly=True, attachment=True)
    qr_expiry = fields.Datetime()

    @api.model
    def create(self, vals):
        record = super(EstateVisitorQR, self).create(vals)
        record._generate_qr_code()
        return record

    def _generate_qr_code(self):
        """Generate a visitor-specific QR code that links to a visitor info page."""
        for r in self:
            # Ensure a token
            r.qr_token = str(uuid.uuid4())
            # Set expiry to 1 year by default (changeable)
            r.qr_expiry = fields.Datetime.now() + timedelta(days=365)

            base = r.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
            qr_url = f"{base}/visitor/info/{r.qr_token}"

            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(qr_url)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_image_base64 = base64.b64encode(buffer.getvalue())

            r.qr_image = qr_image_base64

    def action_regenerate_qr(self):
        """Public method to regenerate a visitor's QR token and image."""
        for r in self:
            r._generate_qr_code()
        return True
