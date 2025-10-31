from odoo import models, fields, api
import base64
import io
import urllib.parse

class BookingList(models.Model):
    _name = "res.booking.list"
    _description = "Container Booking List"
    _order = "booking_date desc"
    _rec_name = "booking_number"

    booking_date = fields.Date(string="Booking Date", required=True)
    booking_number = fields.Char(string="Booking Number", required=True)
    slot_date = fields.Date(string="Slot Date")

    # 👇 new field relations
    slot_id = fields.Many2one("res.slot", string="Slot", required=True)
    slot_time = fields.Selection(
        selection=[
            ('00:00-02:00', '00:00 - 02:00'),
            ('02:00-04:00', '02:00 - 04:00'),
            ('04:00-06:00', '04:00 - 06:00'),
            ('06:00-08:00', '06:00 - 08:00'),
            ('08:00-10:00', '08:00 - 10:00'),
            ('10:00-12:00', '10:00 - 12:00'),
            ('12:00-14:00', '12:00 - 14:00'),
            ('14:00-16:00', '14:00 - 16:00'),
            ('16:00-18:00', '16:00 - 18:00'),
            ('18:00-20:00', '18:00 - 20:00'),
            ('20:00-22:00', '20:00 - 22:00'),
            ('22:00-00:00', '22:00 - 00:00'),
        ],
        string="Slot Time",
        related="slot_id.slot_time",
        store=True,
        readonly=True
    )
    criteria_id = fields.Many2one("res.criteria", string="Criteria", related="slot_id.criteria_id", readonly=True)
    gate = fields.Selection(
        [('A', 'Gate A'), ('B', 'Gate B'), ('C', 'Gate C')],
        string="Gate",
        related="slot_id.gate",
        readonly=True
    )

    booking_type = fields.Selection([
        ("delivery", "Delivery"),
        ("pickup", "Pick Up"),
    ], string="Booking Type")

    depot_id_from = fields.Many2one("res.partner", string="From")
    depot_id_to = fields.Many2one("res.partner", string="To")
    container_id = fields.Many2one("res.container", string="Container")
    transporter_id = fields.Many2one("res.transporter", string="Transporter")
    vehicle_id = fields.Many2one("res.vehicle", string="Vehicle")
    trailer_id = fields.Many2one("res.trailer", string="Trailer")
    driver_id = fields.Many2one("res.driver", string="Driver")

    booking_status = fields.Selection([
        ("created", "Created"),
        ("accepted", "Accepted"),
        ("in_transit", "In Transit"),
        ("completed", "Completed"),
    ], string="Booking Status", default="created")
    journey_id = fields.Many2one("res.container.journey", string="Journey")

    # QR fields
    qr_code = fields.Binary(string="QR Code", attachment=True, readonly=True)
    qr_code_name = fields.Char(string="QR Filename", readonly=True)
    qr_url = fields.Char(string="QR Fallback URL", readonly=True)

    def _generate_qr_data(self, text):
        """Return tuple (is_binary, value)
        - if is_binary True -> value is base64 string (PNG)
        - if is_binary False -> value is fallback URL (string)
        """
        try:
            import qrcode
            # generate PNG in memory
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(text)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            b = buffer.getvalue()
            return True, base64.b64encode(b).decode('utf-8')
        except Exception:
            # fallback: Google Chart API URL encoded
            return False, 'https://chart.googleapis.com/chart?cht=qr&chs=300x300&chl=' + urllib.parse.quote(text)

    @api.model
    def create(self, vals):
        rec = super(BookingList, self).create(vals)
        # Generate QR in a best-effort manner; don't block create on failure
        try:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
            if base_url:
                qr_text = f"{base_url}/slot_booking/book_slot?booking={rec.id}"
            else:
                qr_text = rec.booking_number or str(rec.id)

            is_binary, value = self._generate_qr_data(qr_text)
            if is_binary:
                rec.sudo().write({'qr_code': value, 'qr_code_name': f"{rec.booking_number or rec.id}.png", 'qr_url': False})
            else:
                rec.sudo().write({'qr_url': value, 'qr_code': False, 'qr_code_name': False})
        except Exception:
            # do not raise; QR generation must not block record creation
            pass
        return rec

    def action_download_qr(self):
        """Return an action that navigates to the download QR controller for this booking."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/slot_booking/download_qr/{self.id}',
            'target': 'self',
        }
