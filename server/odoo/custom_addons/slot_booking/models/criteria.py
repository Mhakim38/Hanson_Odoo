from odoo import models, fields


class Criteria(models.Model):
    _name = "res.criteria"
    _description = "Slot Criteria Configuration"
    _order = "criteria_id"
    _rec_name = "criteria_content"

    criteria_id = fields.Char(string="Criteria ID", required=True)
    criteria_content = fields.Char(string="Criteria Content", required=True)
