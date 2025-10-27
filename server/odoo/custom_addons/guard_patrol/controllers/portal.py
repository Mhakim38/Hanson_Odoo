from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import json
from datetime import datetime


class PatrolPortalController(CustomerPortal):

    @http.route(['/my/patrol/<int:tour_id>'], type='http', auth='user', website=True)
    def portal_patrol_detail(self, tour_id, **kwargs):
        """Display patrol tour details and QR scanner."""
        tour = request.env['patrol.tour'].sudo().browse(tour_id)
        if not tour.exists():
            return request.not_found()

        logs = request.env['patrol.log'].sudo().search([
            ('tour_id', '=', tour.id)
        ], order='scan_time desc')

        return request.render('guard_patrol.portal_patrol_detail', {
            'tour': tour,
            'logs': logs,
        })

    @http.route(['/my/patrol/checkin'], type='json', auth='user', methods=['POST'], website=True, csrf=False)
    def portal_patrol_checkin(self, **kwargs):
        """Handle QR scan log submission."""
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            params = data.get('params', {})

            tour_id = params.get('tour_id')
            checkpoint_code = params.get('checkpoint_code')
            lat = params.get('lat')
            lng = params.get('lng')

            if not (tour_id and checkpoint_code):
                return {'success': False, 'error': 'Missing tour or checkpoint data'}

            tour = request.env['patrol.tour'].sudo().browse(int(tour_id))
            if not tour.exists():
                return {'success': False, 'error': 'Invalid tour'}

            checkpoint = request.env['patrol.checkpoint'].sudo().search([
                ('qr_code', '=', checkpoint_code)
            ], limit=1)

            if not checkpoint:
                return {'success': False, 'error': 'Checkpoint not found'}

            # Create log
            request.env['patrol.log'].sudo().create({
                'tour_id': tour.id,
                'checkpoint_id': checkpoint.id,
                'check_time': datetime.now(),
                'lat': lat,
                'lng': lng,
                'user_id': request.env.user.id,
            })

            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}
