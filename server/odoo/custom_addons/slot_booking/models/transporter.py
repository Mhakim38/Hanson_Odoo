from odoo import fields, models, api


class Transporter(models.Model):
    _name = "res.transporter"
    _description = "Transporter"
    _order = "name"

    name = fields.Many2one(
        "res.partner",
        string="Company Name",
        required=True,
        domain=[("is_company", "=", True)],
        help="Select the company registered in Contacts that represents this transporter.",
    )

    forwarder_ids = fields.Many2many(
        "res.forwarder",
        "forwarder_transporter_rel",
        "transporter_id",
        "forwarder_id",
        string="Forwarders",
    )

    transporter_code = fields.Char(string="Transporter Code")
    contact_number = fields.Char(
        string="Contact Number",
        related="name.phone",
        readonly=False
    )
    email = fields.Char(
        string="Email",
        related="name.email",
        readonly=False
    )
    company_address = fields.Char(
        string="Address",
        related="name.contact_address",
        readonly=True
    )
    active = fields.Boolean(default=True)
    remarks = fields.Text()

    driver_ids = fields.One2many("res.driver", "transporter_id", string="Drivers ID")
    vehicle_ids = fields.One2many("res.vehicle", "transporter_id", string="Vehicles ID")
    trailer_ids = fields.One2many("res.trailer", "transporter_id", string="Trailers ID")

    # --- Smart button counts ---
    driver_count = fields.Integer(string="Driver Count", compute="_compute_counts")
    vehicle_count = fields.Integer(string="Vehicle Count", compute="_compute_counts")
    trailer_count = fields.Integer(string="Trailer Count", compute="_compute_counts")

    @api.depends("driver_ids", "vehicle_ids", "trailer_ids")
    def _compute_counts(self):
        for rec in self:
            rec.driver_count = len(rec.driver_ids)
            rec.vehicle_count = len(rec.vehicle_ids)
            rec.trailer_count = len(rec.trailer_ids)

    # --- Custom Display Name ---
    def name_get(self):
        """Show readable name instead of res.partner(id,)"""
        result = []
        for rec in self:
            name = rec.name.name or "Unnamed Transporter"
            result.append((rec.id, name))
        return result

    # --- Smart button actions ---
    def action_view_drivers(self):
        return {
            "name": "Drivers",
            "type": "ir.actions.act_window",
            "res_model": "res.driver",
            "view_mode": "tree,form",
            "domain": [("transporter_id", "=", self.id)] if self.id else [],
            "context": {"default_transporter_id": self.id or False},
            "target": "current",
        }

    def action_view_vehicles(self):
        return {
            "name": "Vehicles",
            "type": "ir.actions.act_window",
            "res_model": "res.vehicle",
            "view_mode": "tree,form",
            "domain": [("transporter_id", "=", self.id)] if self.id else [],
            "context": {"default_transporter_id": self.id or False},
            "target": "current",
        }

    def action_view_trailers(self):
        return {
            "name": "Trailers",
            "type": "ir.actions.act_window",
            "res_model": "res.trailer",
            "view_mode": "tree,form",
            "domain": [("transporter_id", "=", self.id)] if self.id else [],
            "context": {"default_transporter_id": self.id or False},
            "target": "current",
        }

