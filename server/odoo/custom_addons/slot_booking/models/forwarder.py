from odoo import fields, models, api


class Forwarder(models.Model):
    _name = "res.forwarder"
    _description = "Forwarder"
    _order = "name"

    # --- BASIC INFO ---
    name = fields.Many2one(
        "res.partner",
        string="Forwarder Name",
        required=True,
        help="Select the company registered in Contacts that represents this forwarder.",
    )
    forwarder_code = fields.Char()
    contact_number = fields.Char()
    email = fields.Char()
    company_address = fields.Char()
    active = fields.Boolean(default=True)
    remarks = fields.Text()
