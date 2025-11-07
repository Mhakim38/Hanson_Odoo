from odoo import http
from odoo.http import request
from datetime import datetime
import json
import re

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
            purpose = post.get('purpose')

            # Server-side validation: ensure required fields are present
            if not unit_id or not schedule_from:
                raise ValueError("Please fill all required fields (unit and schedule start).")
            # Purpose is required at DB level; enforce it here with a clear error
            if not purpose:
                raise ValueError("Please select visitor type.")

            # Parse schedule_from datetime
            try:
                schedule_from_dt = datetime.strptime(schedule_from, "%Y-%m-%dT%H:%M")
            except Exception:
                raise ValueError("Invalid schedule_from format. Use the date/time picker.")

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
            vehicle_raw = (vehicle_no or '')
            vehicle_no_clean = re.sub(r'[^A-Za-z0-9-]+', '', vehicle_raw).upper()
            if vehicle_no_clean in ('N/A', 'NA', 'NONE'):
                vehicle_no_clean = 'NA'
            vehicle_rec = None
            if vehicle_no_clean:
                if not re.match(r'^[A-Z0-9-]{1,15}$', vehicle_no_clean):
                    raise ValueError("Invalid vehicle number. Use uppercase letters, numbers and hyphens only (max 15 characters).")
                vehicle_rec = request.env['estate.visitor.vehicle'].sudo().create({
                    'visitor_id': visitor.id,
                    'plate_no': vehicle_no_clean,
                })

            # Build visit values without schedule_to
            visit_vals = {
                'visitor_id': visitor.id,
                'unit_id': int(unit_id),
                'schedule_from': schedule_from_dt,
                'state': 'scheduled',
                'host_id': partner.id,
            }
            # Include purpose (visitor type) - required on the model
            if purpose:
                visit_vals['purpose'] = purpose
            # If we created a vehicle record, set the visit's Many2one field to it
            if vehicle_rec:
                visit_vals['visitor_vehicle_ids'] = vehicle_rec.id

            # Create and capture the visit record so we can display details on the thank-you page
            visit = request.env['estate.visit'].sudo().create(visit_vals)

            # Derive display data for the thank-you page
            schedule_display = schedule_from_dt.strftime('%Y-%m-%d %H:%M')
            unit_name = ''
            try:
                unit = request.env['estate.unit'].sudo().browse(int(unit_id))
                unit_name = unit.display_name
            except Exception:
                unit_name = ''

            # Sanitize QR image value (visit.qr_image) to ensure it's a plain base64 string
            qr_image_val = visit.qr_image if visit and getattr(visit, 'qr_image', False) else ''
            if isinstance(qr_image_val, bytes):
                try:
                    qr_image_val = qr_image_val.decode('utf-8')
                except Exception:
                    qr_image_val = ''
            if isinstance(qr_image_val, str):
                # Remove Python bytes literal prefix if present: "b'...'/b\"...\""
                if qr_image_val.startswith("b'") or qr_image_val.startswith('b"'):
                    qr_image_val = qr_image_val[2:]
                    if qr_image_val.endswith("'") or qr_image_val.endswith('"'):
                        qr_image_val = qr_image_val[:-1]
                # Trim surrounding quotes/spaces
                qr_image_val = qr_image_val.strip('\"\' ')

            qr_data_url = ''
            if qr_image_val:
                qr_data_url = 'data:image/png;base64,%s' % qr_image_val

            return request.render('visitor_mgmt.visitor_form_thanks', {
                'host_name': partner.name,
                'schedule_from': schedule_display,
                'visitor_name': visitor.name,
                'unit_name': unit_name,
                'visit_id': visit.id,
                'qr_image': qr_image_val,
                'qr_data_url': qr_data_url,
            })

        except Exception as e:
            # If any DB error occurred, rollback the current cursor to end the failed transaction
            try:
                request.env.cr.rollback()
            except Exception:
                pass
            partner = request.env.user.partner_id
            host_units = partner.estate_unit_ids
            return request.render('visitor_mgmt.visitor_form_template', {
                'error': str(e),
                'units': host_units,
            })
