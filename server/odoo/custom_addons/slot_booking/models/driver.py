from odoo import api, fields, models


class Driver(models.Model):
    _name = "res.driver"
    _description = "Driver"
    _order = "name"

    transporter_id = fields.Many2one("res.transporter", string="Company Name", required=True)
    name = fields.Many2one("res.partner", string="Driver Name", required=True, domain=[("company_type", "=", "person")])
    driver_image = fields.Image(string="Driver Photo")
    driver_license_image = fields.Image(string="Driver License Image")
    driver_ic_image = fields.Image(string="Driver IC / Passport Image")
    driver_license_no = fields.Char(string="Driver License No")
    driver_license_expiry = fields.Date(string="Driver License Expiry")
    driver_ic = fields.Char(string="Driver IC / Work Permit / Passport")
    active = fields.Boolean(default=True)
