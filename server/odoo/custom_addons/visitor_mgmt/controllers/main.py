from odoo import http, fields
from odoo.http import request

class VisitorAPI(http.Controller):
    @http.route('/visitor/checkin', type='json', auth='public', methods=['POST'], csrf=False)
    def visitor_checkin(self, qr_token=None, plate_no=None, gate_code=None):
        Visit = request.env['estate.visit'].sudo()
        domain = [('state','in',['scheduled'])]
        if qr_token:
            domain = ['|'] + domain + [('qr_token','=',qr_token)]
        if plate_no:
            domain = ['|'] + domain + [('visitor_vehicle_ids.plate_no','=',plate_no)]
        visit = Visit.search(domain, limit=1)
        if not visit:
            return {'ok': False, 'error': 'Visit not found or not valid'}
        now = fields.Datetime.now()
        if not (visit.schedule_from <= now <= visit.schedule_to):
            # allow guards to override at gate integrations; here we just proceed
            pass
        visit.write({'state':'check_in','check_in_at': now, 'gate_in_id': request.env['estate.gate'].sudo().search([('name','=',gate_code)], limit=1).id})
        return {'ok': True, 'visit_id': visit.id}
