from odoo import http
from odoo.http import request
from datetime import datetime
import json
import re
import base64

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
            # qr_image_val may be: base64 str, bytes containing a base64 str, or raw image bytes
            if isinstance(qr_image_val, bytes):
                # Try decoding as text first (common case: bytes of base64 string)
                try:
                    decoded = qr_image_val.decode('utf-8')
                    qr_image_val = decoded
                except Exception:
                    # Otherwise assume it's raw binary image data and base64-encode it
                    try:
                        qr_image_val = base64.b64encode(qr_image_val).decode('ascii')
                    except Exception:
                        qr_image_val = ''
            if isinstance(qr_image_val, str):
                # If it's a data URL, extract the payload
                if qr_image_val.startswith('data:'):
                    try:
                        _, payload = qr_image_val.split(',', 1)
                        qr_image_val = payload
                    except Exception:
                        qr_image_val = ''
                # Remove Python bytes literal marker and whitespace
                if qr_image_val.startswith("b'") or qr_image_val.startswith('b"'):
                    qr_image_val = qr_image_val[2:]
                    if qr_image_val.endswith("'") or qr_image_val.endswith('"'):
                        qr_image_val = qr_image_val[:-1]
                qr_image_val = re.sub(r'\s+', '', qr_image_val)

            qr_data_url = ''
            if qr_image_val:
                qr_data_url = 'data:image/png;base64,%s' % qr_image_val

            # Prepare company logo (res.partner.image_1920) for the template.
            # image_1920 is stored as base64 binary (str) in Odoo; prefer to pass it through unchanged
            # and send a small mime-type hint for the template to build a correct data URL.
            company_logo = ''
            company_logo_mime = 'image/png'
            try:
                # Read images using sudo() to avoid access rights preventing image retrieval
                company_logo_val = ''
                try:
                    partner_rec = None
                    if partner and getattr(partner, 'id', False):
                        partner_rec = request.env['res.partner'].sudo().browse(partner.id)
                    if partner_rec and getattr(partner_rec, 'image_1920', False):
                        company_logo_val = partner_rec.image_1920
                    else:
                        # Try the company partner or company record using sudo
                        comp = request.env.company.sudo()
                        cp = comp.partner_id.sudo() if comp and comp.partner_id else None
                        if cp and getattr(cp, 'image_1920', False):
                            company_logo_val = cp.image_1920
                        elif getattr(comp, 'image_1920', False):
                            company_logo_val = comp.image_1920
                        else:
                            company_logo_val = ''
                except Exception:
                    company_logo_val = ''
                # company_logo_val may be: base64 str, bytes containing base64 str, raw binary bytes, or a data URL
                if isinstance(company_logo_val, bytes):
                    # try decode to text first
                    try:
                        company_logo_val_str = company_logo_val.decode('utf-8')
                        company_logo_val = company_logo_val_str
                    except Exception:
                        # assume raw binary bytes -> base64 encode
                        try:
                            company_logo = base64.b64encode(company_logo_val).decode('ascii')
                        except Exception:
                            company_logo = ''
                            company_logo_mime = 'image/png'
                            company_logo_val = ''
                if isinstance(company_logo_val, str) and company_logo_val:
                    # If value is already a data URL, split it
                    if company_logo_val.startswith('data:'):
                        try:
                            hdr, b64 = company_logo_val.split(',', 1)
                            if ';base64' in hdr:
                                company_logo_mime = hdr.split(':', 1)[1].split(';', 1)[0]
                                company_logo = b64
                            else:
                                company_logo = b64
                                company_logo_mime = 'image/png'
                        except Exception:
                            company_logo = ''
                            company_logo_mime = 'image/png'
                    else:
                        # Might already be base64 string; sanitize whitespace and Python byte markers
                        s = company_logo_val.strip()
                        if s.startswith("b'") or s.startswith('b"'):
                            s = s[2:]
                            if s.endswith("'") or s.endswith('"'):
                                s = s[:-1]
                        s = re.sub(r'\s+', '', s)
                        # quick heuristic: if it looks like base64, use it; else we might have raw binary text -> base64 encode
                        if len(s) > 0 and re.match(r'^[A-Za-z0-9+/=\n\r]+$', s):
                            company_logo = s
                            p = company_logo[:4]
                            if p.startswith('/9j/'):
                                company_logo_mime = 'image/jpeg'
                            elif p.startswith('iVB'):
                                company_logo_mime = 'image/png'
                            else:
                                company_logo_mime = 'image/png'
                        else:
                            # not base64-like; try to base64-encode the utf-8 bytes
                            try:
                                company_logo = base64.b64encode(s.encode('utf-8')).decode('ascii')
                                company_logo_mime = 'image/png'
                            except Exception:
                                company_logo = ''
                                company_logo_mime = 'image/png'
                # final safety: ensure company_logo is compacted
                try:
                    if isinstance(company_logo, str) and company_logo:
                        company_logo = re.sub(r'\s+', '', company_logo.strip())
                except Exception:
                    pass
                # (debug logging removed)
            except Exception:
                company_logo = ''
                company_logo_mime = 'image/png'

            # Prepare vehicle display value (sanitized). Prefer the created vehicle record's plate_no,
            # otherwise fall back to the cleaned string (vehicle_no_clean) or empty string.
            vehicle_display = ''
            try:
                if locals().get('vehicle_rec') and getattr(vehicle_rec, 'plate_no', False):
                    vehicle_display = vehicle_rec.plate_no
                else:
                    # vehicle_no_clean may be defined earlier when sanitizing input
                    vehicle_display = locals().get('vehicle_no_clean', '') or ''
            except Exception:
                vehicle_display = ''

            return request.render('visitor_mgmt.visitor_form_thanks', {
                'host_name': partner.name,
                'schedule_from': schedule_display,
                'visitor_name': visitor.name,
                'unit_name': unit_name,
                'visit_id': visit.id,
                'qr_image': qr_image_val,
                'qr_data_url': qr_data_url,
                'vehicle_no': vehicle_display,
                'company_logo': company_logo,
                'company_logo_mime': company_logo_mime,
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
