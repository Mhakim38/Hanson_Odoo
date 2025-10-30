from odoo import models, fields, api

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
