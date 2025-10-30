from odoo import models, fields


class ContainerJourney(models.Model):
    _name = "res.container.journey"
    _description = "Container Journey"
    _order = "id desc"
    _rec_name = "container_id"

    container_id = fields.Many2one("res.container", string="Container Number", required=True, ondelete="cascade")
    transporter_id = fields.Many2one("res.transporter", string="Company Name")

    booking_list_ids = fields.One2many(
        "res.booking.list", "journey_id", string="Booking List"
    )

