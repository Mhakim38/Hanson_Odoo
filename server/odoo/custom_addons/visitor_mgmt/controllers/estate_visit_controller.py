from odoo import http
from odoo.http import request
from datetime import datetime
import json

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

    @http.route(['/estate/visitor_lookup'], type='http', auth='user', website=True, methods=['GET'])
    def visitor_lookup(self, id_number=None, **kwargs):
        """Return visitor info (id, name) for a given ID number as JSON.
        Called by the website form via AJAX when the user enters an ID number.
        """
        if not id_number:
            return request.make_response(json.dumps({'error': 'missing_id_number'}), headers=[('Content-Type', 'application/json')])
        id_clean = id_number.strip()
        visitor = request.env['estate.visitor'].sudo().search([('id_number', 'ilike', id_clean)], limit=1)
        if visitor:
            payload = {'id': visitor.id, 'name': visitor.name}
        else:
            payload = {'id': None, 'name': ''}
        return request.make_response(json.dumps(payload), headers=[('Content-Type', 'application/json')])

    @http.route(['/estate/visit/submit'], type='http', auth='user', website=True, methods=['POST'])
    def visitor_form_submit(self, **post):
        """Submit visitor registration with logged-in user as host"""
        try:
            user = request.env.user
            partner = user.partner_id  # Host partner record

            id_number = post.get('id_number')
            visitor_id_post = post.get('visitor_id')
            visitor_name = post.get('visitor_name')
            vehicle_no = post.get('vehicle_no')
            unit_id = post.get('unit_id')
            schedule_from = post.get('schedule_from')
            schedule_to = post.get('schedule_to')
            purpose = post.get('purpose')

            if not unit_id or not schedule_from or not schedule_to:
                raise ValueError("Please fill all required fields.")

            # Parse datetime strings
            schedule_from_dt = datetime.strptime(schedule_from, "%Y-%m-%dT%H:%M")
            schedule_to_dt = datetime.strptime(schedule_to, "%Y-%m-%dT%H:%M")

            Visitor = request.env['estate.visitor'].sudo()
            visitor = None

            # Priority 1: explicit visitor_id submitted (hidden field set by JS)
            if visitor_id_post:
                try:
                    visitor = Visitor.browse(int(visitor_id_post))
                except Exception:
                    visitor = None

            # Priority 2: lookup by id_number (trim and case-insensitive match)
            if not visitor and id_number:
                id_clean = id_number.strip()
                visitor = Visitor.search([('id_number', 'ilike', id_clean)], limit=1)

            # If still not found, create a new visitor record (use name if provided)
            if not visitor:
                if not visitor_name:
                    raise ValueError("Visitor name is required when no existing visitor is found.")
                visitor_vals = {
                    'name': visitor_name,
                    'host_id': partner.id,
                }
                if id_number:
                    visitor_vals['id_number'] = id_number.strip()
                visitor = Visitor.create(visitor_vals)
            else:
                # ensure host is set for lookups created earlier
                if not visitor.host_id:
                    visitor.host_id = partner.id

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

            # Include purpose if provided
            if purpose:
                visit_vals['purpose'] = purpose

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
