from odoo import models, fields, api

class CollectionPreadvise(models.Model):
    _name = "res.collection.preadvise"
    _description = "Collection Pre-advise"
    _order = "preadvise_date desc"
    _rec_name = "preadvise_number"

    # --- Identification ---
    preadvise_number = fields.Char(
        string="Pre-advise Number",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('res.collection.preadvise')
    )
    preadvise_date = fields.Datetime(string="Pre-advise Date", default=fields.Datetime.now)

    # --- Container Information ---
    container_id = fields.Many2one("res.container", string="Container", required=True)
    depot_id = fields.Many2one("res.yard", string="Depot / Yard")
    transporter_id = fields.Many2one("res.transporter", string="Transporter")
    readiness_status = fields.Selection([
        ("not_ready", "Not Ready"),
        ("ready", "Ready for Collection"),
    ], string="Readiness Status", default="not_ready")

    location = fields.Char(string="Current Location")
    remarks = fields.Text(string="Remarks")

    # --- Publishing & Monitoring ---
    publish_status = fields.Selection([
        ("draft", "Draft"),
        ("published", "Published to Forwarder"),
        ("monitored", "Under Monitoring"),
        ("completed", "Completed"),
    ], string="Status", default="draft", tracking=True)

    published_date = fields.Datetime(string="Published Date", readonly=True)
    monitor_notes = fields.Text(string="Monitoring Notes")

    def action_publish_to_forwarder(self):
        for rec in self:
            rec.publish_status = "published"
            rec.published_date = fields.Datetime.now()

    def action_start_monitoring(self):
        for rec in self:
            rec.publish_status = "monitored"

    def action_mark_completed(self):
        for rec in self:
            rec.publish_status = "completed"
