from odoo import models, fields, api


class ContainerMaintenance(models.Model):
    _name = "res.container.maintenance"
    _description = "Container Maintenance"
    _order = "pre_inspection_date desc"
    _rec_name = "container_id"

    container_id = fields.Many2one("res.container", string="Container Number", required=True, ondelete="cascade")
    container_owner = fields.Many2one(related="container_id.container_owner", store=True)
    container_type = fields.Selection(related="container_id.container_type", store=True)
    status = fields.Selection([
        ('Available', 'Available'),
        ('In Use', 'In Use'),
        ('Under Repair', 'Under Repair'),
        ('Out of Service', 'Out of Service'),
    ], string="Status", default='Available')

    pre_inspection_date = fields.Date(string="Pre-Inspection Date")
    pre_repair_score = fields.Float(string="Pre-Repair Score")
    post_inspection_date = fields.Date(string="Post-Inspection Date")
    post_repair_score = fields.Float(string="Post-Repair Score")


    # ✅ One2many to log lines
    log_ids = fields.One2many(
        "res.container.maintenance.log",
        "maintenance_id",
        string="Additional Maintenance Logs"
    )
