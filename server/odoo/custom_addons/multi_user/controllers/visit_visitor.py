from odoo import http
from odoo.http import request
from datetime import datetime
import json
import re


class EstateVisitController(http.Controller):

    # ============================================================
    # Guard Form Page
    # ============================================================
    @http.route(['/guard/visit'], type='http', auth='user', website=True)
    def visitor_form(self, **kwargs):
        """Guard view: show visitor registration form with all units & visitors"""
        all_units = request.env['estate.unit'].sudo().search([])
        all_visitors = request.env['estate.visitor'].sudo().search([])

        return request.render('multi_user.visitor_form_template', {
            'units': all_units,
            'visitors': all_visitors,
            'error': False,
        })

    # ============================================================
    # AJAX Lookup Visitor by ID Number
    # ============================================================
    @http.route(['/guard/visitor_lookup'], type='http', auth='user', website=True, methods=['GET'])
    def visitor_lookup(self, id_number=None, **kwargs):
        """AJAX lookup visitor info by ID number"""
        if not id_number:
            return request.make_response(
                json.dumps({'error': 'missing_id_number'}),
                headers=[('Content-Type', 'application/json')]
            )

        id_clean = id_number.strip()
        visitor = request.env['estate.visitor'].sudo().search(
            [('id_number', 'ilike', id_clean)], limit=1
        )

        if visitor:
            payload = {'id': visitor.id, 'name': visitor.name}
        else:
            payload = {'id': None, 'name': ''}

        return request.make_response(
            json.dumps(payload),
            headers=[('Content-Type', 'application/json')]
        )

    # ============================================================
    # Guard Submit Visit Form
    # ============================================================
    @http.route(['/guard/visit/submit'], type='http', auth='user', website=True, methods=['POST'])
    def visitor_form_submit(self, **post):
        """Submit visitor registration (by guard)"""
        try:
            id_number = post.get('id_number')
            visitor_id_post = post.get('visitor_id')
            visitor_name = post.get('visitor_name')
            vehicle_no = post.get('vehicle_no')
            unit_id = post.get('unit_id')
            schedule_from = post.get('schedule_from')
            purpose = post.get('purpose')

            # ------------------------
            # Validation
            # ------------------------
            if not unit_id or not schedule_from:
                raise ValueError("Please fill all required fields.")

            try:
                schedule_from_dt = datetime.strptime(schedule_from, "%Y-%m-%dT%H:%M")
            except Exception:
                raise ValueError("Invalid date format for schedule_from.")

            Visitor = request.env['estate.visitor'].sudo()
            visitor = None

            # Priority 1: explicit visitor_id
            if visitor_id_post:
                visitor = Visitor.browse(int(visitor_id_post))

            # Priority 2: lookup by id_number
            if not visitor and id_number:
                visitor = Visitor.search([('id_number', 'ilike', id_number.strip())], limit=1)

            # Create new visitor if not found
            if not visitor:
                if not visitor_name:
                    raise ValueError("Visitor name is required when creating new visitor.")
                visitor_vals = {'name': visitor_name}
                if id_number:
                    visitor_vals['id_number'] = id_number.strip()
                visitor = Visitor.create(visitor_vals)

            # ------------------------
            # Create visitor vehicle (optional)
            # ------------------------
            # Normalize and validate vehicle number before creating
            vehicle_rec = None
            vehicle_raw = (vehicle_no or '')
            vehicle_no_clean = re.sub(r'[^A-Za-z0-9-]+', '', vehicle_raw).upper()
            if vehicle_no_clean in ('N/A', 'NA', 'NONE'):
                vehicle_no_clean = 'NA'
            if vehicle_no_clean:
                if not re.match(r'^[A-Z0-9-]{1,15}$', vehicle_no_clean):
                    raise ValueError("Invalid vehicle number. Use uppercase letters, numbers and hyphens only (max 15 characters).")
                vehicle_rec = request.env['estate.visitor.vehicle'].sudo().create({
                    'visitor_id': visitor.id,
                    'plate_no': vehicle_no_clean,
                })

            # ------------------------
            # Get selected unit
            # ------------------------
            unit = request.env['estate.unit'].sudo().browse(int(unit_id))

            # ------------------------
            # ✅ Auto-assign visitor.host_id ikut unit owner (untuk guard)
            # ------------------------
            if unit and unit.owner_id:
                # Kalau visitor belum ada host, auto-link kepada unit owner
                if not visitor.host_id or visitor.host_id.id != unit.owner_id.id:
                    visitor.sudo().write({'host_id': unit.owner_id.id})

            # ------------------------
            # Create Visit Record
            # ------------------------
            visit_vals = {
                'visitor_id': visitor.id,
                'unit_id': int(unit_id),
                'schedule_from': schedule_from_dt,
                'state': 'scheduled',
                'purpose': purpose or 'visitor',
                'origin': 'adhoc',
                'is_adhoc': True,
                'check_in_mode': 'manual',

                # ✅ Fallback host_id (avoid NULL constraint error)
                'host_id': unit.owner_id.id if unit and unit.owner_id else request.env.user.partner_id.id,
            }

            # If we created a vehicle record, set the visit's Many2one field to it
            if vehicle_rec:
                visit_vals['visitor_vehicle_ids'] = vehicle_rec.id

            visit = request.env['estate.visit'].with_context(from_guard_portal=True).sudo().create(visit_vals)

            # ------------------------
            # Auto check-in the visit (guard action)
            # ------------------------
            # Reuse the visit model's guard check-in action. Keep the same
            # from_guard_portal context so model-level constraints are skipped
            # for the guard flow. Let any exceptions bubble up to the outer
            # handler so the existing error rendering works.
            visit.with_context(from_guard_portal=True).sudo().action_guard_checkin()

            # ------------------------
            # Return Success Page
            # ------------------------
            return request.render('multi_user.visitor_form_thanks', {
                'unit_name': unit.display_name if unit else 'N/A',
                'visitor_name': visitor.name,
                'visit_id': visit.id,
            })

        except Exception as e:
            # Rollback dulu supaya query selepas ni tak error
            request.env.cr.rollback()
            all_units = request.env['estate.unit'].sudo().search([])

            return request.render('multi_user.visitor_form_template', {
                'error': str(e),
                'units': all_units,
            })
