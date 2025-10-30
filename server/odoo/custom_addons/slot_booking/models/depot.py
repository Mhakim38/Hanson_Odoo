from odoo import api, fields, models


class Depot(models.Model):
    _name = "res.depot"
    _description = "Depot Operator"
    _order = "name"

    name = fields.Char(required=True, help="Depot name", string="Depot Name")
    depot_id = fields.Char(string="Depot ID", help="Unique depot id")
    location = fields.Char(help="Depot address or location name")
    gps_coordinates = fields.Char(help="Latitude and longitude")
    depot_manager_id = fields.Many2one("res.users", string="Depot Manager ID", help="Responsible depot manager")
    contact_number = fields.Char()
    operating_hours = fields.Char(help="Example: 08:00 – 20:00")
    max_yard_capacity = fields.Integer(help="Maximum number of yards allowed")
    active = fields.Boolean(default=True)
    remarks = fields.Text()
    yard_ids = fields.One2many("res.yard", "depot_id", string="Yards ID")
    company_id = fields.Many2one("res.company", string="Company ID", required=False)
    company_name = fields.Char(related="company_id.name", string="Company Name", store=True)
