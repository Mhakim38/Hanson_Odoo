from odoo import fields, models


class Trailer(models.Model):
    _name = "res.trailer"
    _description = "Trailer"
    _order = "name"
    _rec_name = "trailer_plate_no"

    name = fields.Char(required=True, store=True, string="Trailer Name")
    transporter_id = fields.Many2one("res.transporter", string="Company Name", required=True)
    trailer_plate_no = fields.Char(required=True, string="Trailer Plate Number")
    container_id = fields.Many2one("res.container", string="Container ID")
    trailer_capacity = fields.Selection([("20ft", "20FT"), ("40ft", "40FT")])
    insurance_expiry = fields.Date()
    trailer_permit = fields.Char(string="Permit")
