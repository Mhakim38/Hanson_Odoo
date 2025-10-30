from odoo import models, fields

class ContainerStage(models.Model):
    _name = "res.container.stage"
    _description = "Container Stage"
    _order = "sequence, id"

    name = fields.Char(string="Stage Name", required=True)
    sequence = fields.Integer(default=1)
    fold = fields.Boolean(string="Folded in Kanban", default=False)
    color = fields.Integer(string="Color Index")
