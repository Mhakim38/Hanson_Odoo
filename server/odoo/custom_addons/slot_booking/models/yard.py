from odoo import api, fields, models


class Yard(models.Model):
    _name = "res.yard"
    _description = "Yard"
    _order = "name"

    name = fields.Char(required=True)
    yard_code = fields.Char(string="Yard Code")
    address = fields.Char(string="Yard Address")
    block = fields.Char(string="Block")
    depot_id = fields.Many2one("res.depot", string="Depot ID", required=True)
    capacity = fields.Integer(help="Maximum number of containers")
    occupied_slots = fields.Integer(default=0)
    available_slots = fields.Integer(compute="_compute_available_slots", store=True)
    yard_supervisor_id = fields.Many2one("res.users", string="Supervisor")
    yard_status = fields.Selection([
        ("active", "Active"),
        ("maintenance", "Maintenance"),
        ("full", "Full"),
    ], default="active")
    remarks = fields.Text()

    # ✅ GEOLOCALIZATION FIELDS
    partner_latitude = fields.Float(string="Latitude", digits=(16, 5))
    partner_longitude = fields.Float(string="Longitude", digits=(16, 5))
    date_localization = fields.Datetime(string="Geo Localized On")
    map_url = fields.Char(string="Map URL", compute="_compute_map_url", store=False)

    @api.depends("capacity", "occupied_slots")
    def _compute_available_slots(self):
        for rec in self:
            rec.available_slots = max((rec.capacity or 0) - (rec.occupied_slots or 0), 0)

    @api.depends("partner_latitude", "partner_longitude")
    def _compute_map_url(self):
        for record in self:
            if record.partner_latitude and record.partner_longitude:
                record.map_url = f"https://www.google.com/maps?q={record.partner_latitude},{record.partner_longitude}"
            else:
                record.map_url = False

    def action_geolocate(self):
        """Use Odoo's base_geolocalize service to fetch coordinates."""
        for record in self:
            if record.address:
                geo = record.env["res.partner"]._geo_localize(record.address, None, None)
                if geo:
                    record.partner_latitude, record.partner_longitude = geo
                    record.date_localization = fields.Datetime.now()
        return True
