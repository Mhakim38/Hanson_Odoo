from odoo import models, fields, api

class ReleaseOrderTransport(models.Model):
    _name = "res.rot"
    _description = "Release Order Transport"
    _order = "rot_date desc, id desc"
    _rec_name = "rot_number"

    # --- Basic Information ---
    rot_number = fields.Char(string="ROT Number", required=True, copy=False, readonly=True,
                             default=lambda self: self.env['ir.sequence'].next_by_code('res.rot'))
    rot_date = fields.Datetime(string="ROT Date", default=fields.Datetime.now)

    # --- Gate Pass Information ---
    gate_pass_ref = fields.Char(string="Gate Pass Reference", required=True)
    gate_pass_request_date = fields.Date(string="Gate Pass Request Date")

    # --- Transporter Info ---
    transporter_id = fields.Many2one("res.transporter", string="Transporter", required=True)
    vehicle_id = fields.Many2one("res.vehicle", string="Vehicle", help="Vehicle assigned to this ROT.")
    trailer_id = fields.Many2one("res.trailer", string="Trailer", help="Trailer attached to this ROT.")
    driver_id = fields.Many2one("res.driver", string="Driver", help="Driver assigned for transport.")
    container_id = fields.Many2one("res.container", string="Container Number")

    # --- Attachments ---
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "rot_attachment_rel",
        "rot_id",
        "attachment_id",
        string="Attached Documents"
    )

    # --- Status Management ---
    status = fields.Selection([
        ("draft", "Draft"),
        ("sent", "Sent to Haulier"),
        ("pending", "Pending Acceptance"),
        ("acknowledged", "Acknowledged"),
        ("cancelled", "Cancelled"),
    ], string="Status", default="draft", tracking=True)

    acknowledgement_date = fields.Datetime(string="Acknowledgement Date", readonly=True)

    # --- Workflow Helpers ---
    remarks = fields.Text(string="Remarks")

    # --- Relation to Slot Booking (optional) ---
    booking_list_id = fields.Many2one("res.booking.list", string="Related Slot Booking")

    @api.model
    def create(self, vals):
        """Auto-generate ROT number"""
        if not vals.get("rot_number"):
            vals["rot_number"] = self.env["ir.sequence"].next_by_code("res.rot")
        return super(ReleaseOrderTransport, self).create(vals)

    def action_send_to_haulier(self):
        """Simulate sending ROT to haulier"""
        for record in self:
            record.status = "sent"

    def action_mark_pending(self):
        """Mark as pending acceptance"""
        for record in self:
            record.status = "pending"

    def action_acknowledge(self):
        """Acknowledge the ROT"""
        for record in self:
            record.status = "acknowledged"
            record.acknowledgement_date = fields.Datetime.now()
