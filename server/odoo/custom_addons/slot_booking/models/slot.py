from odoo import models, fields, api


class Slot(models.Model):
    _name = "res.slot"
    _description = "Slot Configuration"
    _order = "slot_id"
    _rec_name = "slot_id"

    slot_id = fields.Char(string="Slot ID", required=True)
    slot_time = fields.Selection([
        ('00:00-02:00', '00:00 - 02:00'),
        ('02:00-04:00', '02:00 - 04:00'),
        ('04:00-06:00', '04:00 - 06:00'),
        ('06:00-08:00', '06:00 - 08:00'),
        ('08:00-10:00', '08:00 - 10:00'),
        ('10:00-12:00', '10:00 - 12:00'),
        ('12:00-14:00', '12:00 - 14:00'),
        ('14:00-16:00', '14:00 - 16:00'),
        ('16:00-18:00', '16:00 - 18:00'),
        ('18:00-20:00', '18:00 - 20:00'),
        ('20:00-22:00', '20:00 - 22:00'),
        ('22:00-00:00', '22:00 - 00:00'),
    ], string="Slot Time", required=True)

    criteria_id = fields.Many2one("res.criteria", string="Criteria")
    gate = fields.Selection([
        ('gate_a', 'Gate A'),
        ('gate_b', 'Gate B'),
        ('gate_c', 'Gate C')
    ], string="Gate", required=True)
