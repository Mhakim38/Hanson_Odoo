from odoo import fields, models


class Vehicle(models.Model):
    _name = "res.vehicle"
    _description = "Vehicle"
    _order = "name"
    _rec_name = "vehicle_plate_no"

    name = fields.Char(required=True, store=True, string="Vehicle Name")
    transporter_id = fields.Many2one("res.transporter", string="Company Name", required=True)
    vehicle_plate_no = fields.Char(required=True, string="Vehicle Plate Number")
    vehicle_type = fields.Selection([
        ("truck", "Truck"),
        ("prime_mover", "Prime Mover"),
        ("lorry", "Lorry"),
    ])
    vehicle_capacity = fields.Float()
    insurance_expiry = fields.Date()
    vehicle_roadtax = fields.Char(string="Road Tax")
