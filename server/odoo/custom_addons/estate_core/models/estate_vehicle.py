from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class EstateVehicle(models.Model):
    _name = "estate.vehicle"
    _description = "Resident Vehicle"
    _sql_constraints = [('plate_unique','unique(plate_no)','Plate already registered!')]


    name = fields.Char(related="plate_no")
    unit_id = fields.Many2one('estate.unit', required=True)
    host_id = fields.Many2one(
        'res.partner',
        string="Host",
        help="The resident or owner this vehicle belongs to."
    )
    plate_no = fields.Char(required=True, index=True)
    make = fields.Char()
    model = fields.Char()
    color = fields.Char()
    tag_type = fields.Selection([('sticker','Sticker'),('qr','QR'),('rfid','RFID')], default='sticker')
    tag_code = fields.Char()
    valid_from = fields.Date(default=fields.Date.today)
    valid_to = fields.Date()
    status = fields.Boolean(string="Active")

    @api.constrains('valid_to')
    def _check_validity(self):
        for r in self:
            if r.valid_to and r.valid_to < date.today():
                raise ValidationError(_("Vehicle validity date is in the past."))
