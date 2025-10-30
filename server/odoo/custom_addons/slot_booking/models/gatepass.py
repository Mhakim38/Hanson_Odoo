from odoo import models, fields, api

class GatePass(models.Model):
    _name = "res.gatepass"
    _description = "Gate Pass Application and Approval"
    _order = "application_date desc"
    _rec_name = "gatepass_number"

    # --- Basic Info ---
    gatepass_number = fields.Char(
        string="Gate Pass Number",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('res.gatepass')
    )
    application_date = fields.Datetime(string="Application Date", default=fields.Datetime.now)
    applicant_name = fields.Char(string="Applicant Name", required=True)

    # --- Related Container / Transport Info ---
    container_id = fields.Many2one("res.container", string="Container", required=True)
    haulier_id = fields.Many2one("res.transporter", string="Haulier", required=True)
    preadvise_id = fields.Many2one("res.collection.preadvise", string="Related Pre-advise")
    vehicle_id = fields.Many2one("res.vehicle", string="Vehicle")
    driver_id = fields.Many2one("res.driver", string="Driver")

    # --- Attachments ---
    attachment_ids = fields.Many2many("ir.attachment", string="Attached Documents")

    # --- Validation / Approval Process ---
    payment_validated = fields.Boolean(string="Payment Validated", default=False)
    application_validated = fields.Boolean(string="Application Validated", default=False)

    status = fields.Selection([
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_validation", "Under Validation"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ], string="Status", default="draft", tracking=True)

    remarks = fields.Text(string="Remarks")

    # --- Button Actions ---
    def action_submit(self):
        for rec in self:
            rec.status = "submitted"

    def action_validate(self):
        for rec in self:
            rec.status = "under_validation"
            rec.application_validated = True

    def action_approve(self):
        for rec in self:
            rec.status = "approved"

    def action_reject(self):
        for rec in self:
            rec.status = "rejected"
