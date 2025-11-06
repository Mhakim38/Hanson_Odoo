from odoo import http
from odoo.http import request
from datetime import datetime

class GuardRegisterVisit(http.Controller):

    # 🟩 Papar form daftar visit untuk guard
    @http.route(['/guard/register_visit'], type='http', auth='user', website=True)
    def guard_register_visit(self, **kw):
        """Page form untuk guard daftar visitor"""
        user = request.env.user

        # Ambil data asas
        visitors = request.env['estate.visitor'].sudo().search([], order='name')
        vehicles = request.env['estate.visitor.vehicle'].sudo().search([], order='plate_no')
        units = request.env['estate.unit'].sudo().search([], order='name')
        gates = request.env['estate.gate'].sudo().search([], order='name')

        # 🔹 Tambahan penting: ambil senarai host/resident (bukan company)
        all_hosts = request.env['res.partner'].sudo().search([
            ('is_company', '=', False)
        ], order='name')

        return request.render('multi_user.guard_register_visit_form', {
            'visitors': visitors,
            'vehicles': vehicles,
            'units': units,
            'gates': gates,
            'all_hosts': all_hosts,
            'success': kw.get('success'),
            'error': kw.get('error'),
        })

    # 🟦 Simpan data visit
    @http.route(['/guard/register_visit/submit'], type='http', auth='user', website=True, methods=['POST'])
    def guard_register_visit_submit(self, **post):
        """Simpan data form"""
        try:
            vals = {
                'purpose': post.get('purpose'),
                'host_id': int(post.get('host_id')) if post.get('host_id') else False,
                'visitor_id': int(post.get('visitor_id')) if post.get('visitor_id') else False,
                'visitor_vehicle_ids': int(post.get('vehicle_id')) if post.get('vehicle_id') else False,
                'unit_id': int(post.get('unit_id')) if post.get('unit_id') else False,
                'schedule_from': post.get('schedule_from'),
                'schedule_to': post.get('schedule_to'),
                'gate_in_id': int(post.get('gate_in_id')) if post.get('gate_in_id') else False,
                'gate_out_id': int(post.get('gate_out_id')) if post.get('gate_out_id') else False,
                'origin': 'adhoc',
                'is_adhoc': True,
                'check_in_mode': post.get('check_in_mode', 'manual'),
            }

            visit = request.env['estate.visit'].sudo().create(vals)
            return request.redirect('/guard/register_visit?success=1')

        except Exception as e:
            # Log error untuk debug dalam odoo log
            request.env.cr.rollback()
            _logger = http.logging.getLogger(__name__)
            _logger.error("Error when guard registering visit: %s", str(e))
            return request.redirect('/guard/register_visit?error=1')
