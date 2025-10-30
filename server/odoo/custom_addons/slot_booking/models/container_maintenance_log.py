from odoo import models, fields


class ContainerMaintenanceLog(models.Model):
    _name = "res.container.maintenance.log"
    _description = "Container Maintenance Log"
    _order = "date desc"

    maintenance_id = fields.Many2one(
        "res.container.maintenance",
        string="Maintenance Record",
        ondelete="cascade",
        required=True,
    )
    date = fields.Date(string="Log Date", default=fields.Date.context_today)
    remarks = fields.Text(string="Remarks")
    attachment = fields.Binary(string="Attachment")
    attachment_filename = fields.Char(string="File Name")
