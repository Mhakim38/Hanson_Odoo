from odoo import models, fields, api

class CollectionPreAdviseLine(models.Model):
    _name = "res.collection.preadvise.line"
    _description = "Collection Pre-Advise Line"
    _order = "id desc"

    preadvise_id = fields.Many2one(
        "res.collection.preadvise",
        string="Pre-Advise",
        ondelete="cascade",
    )
    booking_ref = fields.Char(string="Booking Reference")

    container_id = fields.Many2one(
        "res.container",
        string="Container Number",
        domain=[("stage_id.name", "=", "Available")],  # ✅ only containers with "Available" stage
    )
    depot_id = fields.Many2one("res.depot", string="Depot")
    yard_id = fields.Many2one("res.yard", string="Yard")
    block = fields.Char(string="Block")

    # ✅ corrected related field
    status = fields.Char(
        related="container_id.stage_id.name",
        string="Status",
        store=True,
        readonly=True,
    )

    @api.onchange("container_id")
    def _onchange_container_id(self):
        for rec in self:
            if rec.container_id:
                rec.depot_id = rec.container_id.depot_id.id if rec.container_id.depot_id else False
                rec.yard_id = rec.container_id.yard_id.id if hasattr(rec.container_id, "yard_id") else False

