from odoo import models, fields, api

class CollectionPreAdvise(models.Model):
    _name = "res.collection.preadvise"
    _description = "Collection Pre-Advise"
    _order = "preadvise_date desc"

    preadvise_number = fields.Char(string="Pre-Advise Number", readonly=True, copy=False)
    preadvise_date = fields.Datetime(string="Pre-Advise Date", default=fields.Datetime.now)
    depot_id = fields.Many2one("res.depot", string="Depot")
    location = fields.Char(string="Location")
    transporter_id = fields.Many2one("res.transporter", string="Transporter")
    readiness_status = fields.Selection([
        ("pending", "Pending"),
        ("ready", "Ready"),
    ], string="Readiness Status", default="pending")

    publish_status = fields.Selection([
        ("draft", "Draft"),
        ("published", "Published"),
        ("monitored", "Monitored"),
        ("completed", "Completed"),
    ], string="Publish Status", default="draft")

    remarks = fields.Text(string="Remarks")
    monitor_notes = fields.Text(string="Monitoring Notes")

    line_ids = fields.One2many(
        "res.collection.preadvise.line",
        "preadvise_id",
        string="Available Containers"
    )

    # ------------------------------------------------------------
    # OVERRIDE CREATE to prefill available containers automatically
    # ------------------------------------------------------------
    @api.model
    def create(self, vals):
        record = super(CollectionPreAdvise, self).create(vals)

        available_containers = self.env["res.container"].search([
            ("stage_id.name", "=", "Available")
        ])

        line_vals = []
        for c in available_containers:
            line_vals.append((0, 0, {
                "container_id": c.id,
                "depot_id": c.depot_id.id if c.depot_id else False,
                "yard_id": c.yard_id.id if hasattr(c, "yard_id") else False,
                "block": getattr(c, "block", False),
                "status": c.stage_id.name,
            }))

        record.write({"line_ids": line_vals})
        return record

    # ----------------------------------------------------------------------
    # Workflow buttons (no change)
    # ----------------------------------------------------------------------
    def action_publish_to_forwarder(self):
        for rec in self:
            rec.publish_status = "published"

    def action_start_monitoring(self):
        for rec in self:
            rec.publish_status = "monitored"

    def action_mark_completed(self):
        for rec in self:
            rec.publish_status = "completed"
