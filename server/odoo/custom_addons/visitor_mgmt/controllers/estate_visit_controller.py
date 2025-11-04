from odoo import http
from odoo.http import request
from datetime import datetime

class EstateVisitController(http.Controller):

    @http.route(['/estate/visit'], type='http', auth='user', website=True)
    def visitor_form(self, **kwargs):
        """Show visitor registration form filtered by logged-in user's owned units"""
        user = request.env.user
        partner = user.partner_id

        # Owned units via the new One2many field
        host_units = partner.estate_unit_ids

        return request.render('visitor_mgmt.visitor_form_template', {
            'units': host_units,
        })

    @http.route(['/estate/visit/submit'], type='http', auth='user', website=True, methods=['POST'])
    def visitor_form_submit(self, **post):
        """Submit visitor registration with logged-in user as host"""
        try:
            user = request.env.user
            partner = user.partner_id  # Host partner record

            visitor_name = post.get('visitor_name')
            vehicle_no = post.get('vehicle_no')
            unit_id = post.get('unit_id')
            schedule_from = post.get('schedule_from')
            schedule_to = post.get('schedule_to')

            if not visitor_name or not unit_id or not schedule_from or not schedule_to:
                raise ValueError("Please fill all required fields.")

            # Parse datetime strings
            schedule_from_dt = datetime.strptime(schedule_from, "%Y-%m-%dT%H:%M")
            schedule_to_dt = datetime.strptime(schedule_to, "%Y-%m-%dT%H:%M")

            # Create visitor record and assign host_id so it appears when filtering by host
            visitor_vals = {
                'name': visitor_name,
                'host_id': partner.id,
            }
            visitor = request.env['estate.visitor'].sudo().create(visitor_vals)

            # Optionally create vehicle
            if vehicle_no:
                request.env['estate.visitor.vehicle'].sudo().create({
                    'visitor_id': visitor.id,
                    'plate_no': vehicle_no,
                })

            # Ensure the visit model has a host_id (linking to res.partner)
            visit_vals = {
                'visitor_id': visitor.id,
                'unit_id': int(unit_id),
                'schedule_from': schedule_from_dt,
                'schedule_to': schedule_to_dt,
                'state': 'scheduled',
                'host_id': partner.id,
            }

            request.env['estate.visit'].sudo().create(visit_vals)

            return request.render('visitor_mgmt.visitor_form_thanks', {
                'host_name': partner.name,
            })

        except Exception as e:
            partner = request.env.user.partner_id
            host_units = partner.estate_unit_ids
            return request.render('visitor_mgmt.visitor_form_template', {
                'error': str(e),
                'units': host_units,
            })
