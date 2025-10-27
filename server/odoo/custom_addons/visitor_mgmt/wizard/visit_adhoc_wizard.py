from odoo import api, fields, models, _
from odoo.exceptions import UserError

class VisitAdhocWizard(models.TransientModel):
    _name = "visit.adhoc.wizard"
    _description = "Ad-Hoc Visitor Check-In Wizard"

    visitor_name = fields.Char(required=True)
    id_type = fields.Selection([('ic','IC/MyKad'),('passport','Passport'),('license','Driving License'),('other','Other')], required=True, default='ic')
    id_number = fields.Char(required=True)
    phone = fields.Char()

    plate_no = fields.Char()
    make = fields.Char()
    model = fields.Char()
    color = fields.Char()

    host_partner_id = fields.Many2one('res.partner')
    unit_id = fields.Many2one('estate.unit', required=True, help="Required if host is unknown")
    purpose = fields.Char(required=True, default="Visit")

    gate_in_id = fields.Many2one('estate.gate', required=True)
    valid_minutes = fields.Integer(default=120)

    def action_confirm(self):
        self.ensure_one()
        Visitor = self.env['estate.visitor'].sudo()
        Visit = self.env['estate.visit'].sudo()

        if not (self.host_partner_id or self.unit_id):
            raise UserError(_("Select a Host or a Unit."))

        visitor = Visitor.search([('id_type','=',self.id_type),('id_number','=',self.id_number)], limit=1)
        if not visitor:
            visitor = Visitor.create({
                'name': self.visitor_name,
                'id_type': self.id_type,
                'id_number': self.id_number,
                'phone': self.phone,
            })
        if visitor.blacklisted:
            raise UserError(_("Visitor is blacklisted."))

        vehicle = False
        if self.plate_no:
            vehicle = self.env['estate.visitor.vehicle'].search([('plate_no','=',self.plate_no)], limit=1)
            if not vehicle:
                vehicle = self.env['estate.visitor.vehicle'].create({
                    'visitor_id': visitor.id,
                    'plate_no': self.plate_no,
                    'make': self.make,
                    'model': self.model,
                    'color': self.color,
                })

        active_visit = Visit.search([('visitor_id','=',visitor.id), ('state','in', ['scheduled','check_in'])], limit=1)
        if active_visit:
            raise UserError(_("This visitor already has an active visit."))

        visit = Visit.create({
            'visitor_id': visitor.id,
            'host_partner_id': self.host_partner_id.id if self.host_partner_id else False,
            'unit_id': self.unit_id.id,
            'purpose': self.purpose,
            'gate_in_id': self.gate_in_id.id,
            'valid_minutes': self.valid_minutes,
            'check_in_mode': 'manual',
            'origin': 'adhoc',
            'is_adhoc': True,
            'state': 'scheduled',
            'schedule_from': fields.Datetime.now(),
            'schedule_to': fields.Datetime.now(),
        })
        visit.action_checkin_adhoc()

        if vehicle:
            # link through inverse relation contextually (simple association already exists at visitor level)
            pass
        return True
