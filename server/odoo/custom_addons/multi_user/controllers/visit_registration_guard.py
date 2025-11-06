from odoo import http
from odoo.http import request
from datetime import datetime
import re


class GuardVisitRegistrationController(http.Controller):
    """
    Controller khas untuk guard mendaftar pelawat (manual/ad-hoc).
    Guard boleh pilih mana-mana unit daripada semua unit dalam sistem.
    """

    # ------------------------------------------------------------
    # 1️⃣ Papar borang pendaftaran pelawat (Guard)
    # ------------------------------------------------------------
    @http.route(['/guard/visit/register'], type='http', auth='user', website=True)
    def guard_visit_form(self, **kwargs):
        """
        Papar borang daftar pelawat baru.
        Guard boleh pilih mana-mana unit.
        """
        all_units = request.env['estate.unit'].sudo().search([])
        purposes = [
            ('visitor', 'Visitor'),
            ('pickup', 'Pickup'),
            ('contractor/service provider', 'Contractor / Service Provider'),
        ]

        return request.render('multi_user.guard_visit_registration', {
            'all_units': all_units,
            'purposes': purposes,
            'form_values': kwargs,
        })

    # ------------------------------------------------------------
    # 2️⃣ Proses submit borang pendaftaran
    # ------------------------------------------------------------
    @http.route(['/guard/visit/register/submit'], type='http', auth='user', website=True, methods=['POST'])
    def guard_visit_submit(self, **post):
        """
        Proses input borang & cipta rekod visit baru.
        """
        try:
            user = request.env.user
            visitor_name = post.get('visitor_name')
            vehicle_no = post.get('vehicle_no')
            unit_id = post.get('unit_id')
            purpose = post.get('purpose')
            schedule_from = post.get('schedule_from')
            schedule_to = post.get('schedule_to')

            # 🧾 Validation
            if not visitor_name or not unit_id or not purpose or not schedule_from or not schedule_to:
                raise ValueError("Please fill in all required fields before submitting.")

            # Convert datetime string ke objek datetime
            schedule_from_dt = datetime.strptime(schedule_from, "%Y-%m-%dT%H:%M")
            schedule_to_dt = datetime.strptime(schedule_to, "%Y-%m-%dT%H:%M")

            if schedule_to_dt < schedule_from_dt:
                raise ValueError("End time cannot be earlier than start time.")

            # Pastikan unit sah
            unit = request.env['estate.unit'].sudo().browse(int(unit_id))
            if not unit.exists():
                raise ValueError("Selected unit not found.")

            # Cari host (owner unit)
            host = unit.owner_id if hasattr(unit, 'owner_id') else False

            # Buat visitor
            visitor_vals = {'name': visitor_name.strip()}
            visitor = request.env['estate.visitor'].sudo().create(visitor_vals)

            # Buat vehicle (jika isi)
            # Normalize and validate vehicle number before creating
            vehicle = None
            vehicle_raw = (vehicle_no or '')
            vehicle_no_clean = re.sub(r'[^A-Za-z0-9-]+', '', vehicle_raw).upper()
            if vehicle_no_clean in ('N/A', 'NA', 'NONE'):
                vehicle_no_clean = 'NA'
            if vehicle_no_clean:
                if not re.match(r'^[A-Z0-9-]{1,15}$', vehicle_no_clean):
                    raise ValueError("Invalid vehicle number. Use uppercase letters, numbers and hyphens only (max 15 characters).")
                vehicle = request.env['estate.visitor.vehicle'].sudo().create({
                    'visitor_id': visitor.id,
                    'plate_no': vehicle_no_clean,
                })

            # Buat rekod visit
            visit_vals = {
                'visitor_id': visitor.id,
                # Link created vehicle record to visit (if any)
                'visitor_vehicle_ids': vehicle.id if vehicle else False,
                'unit_id': unit.id,
                'host_id': host.id if host else False,
                'purpose': purpose,
                'schedule_from': schedule_from_dt,
                'schedule_to': schedule_to_dt,
                'origin': 'adhoc',
                'is_adhoc': True,
                'state': 'scheduled',
                # Optional tracking siapa guard yang daftar
                'check_in_mode': 'manual',
            }

            request.env['estate.visit'].sudo().create(visit_vals)

            # ✅ Papar page success
            return request.render('multi_user.guard_visit_success', {
                'visitor_name': visitor_name,
                'unit_name': unit.display_name,
                'schedule_from': schedule_from_dt,
                'schedule_to': schedule_to_dt,
            })

        except Exception as e:
            # ❌ Papar semula borang dengan error
            all_units = request.env['estate.unit'].sudo().search([])
            purposes = [
                ('visitor', 'Visitor'),
                ('pickup', 'Pickup'),
                ('contractor/service provider', 'Contractor / Service Provider'),
            ]

            return request.render('multi_user.guard_visit_registration', {
                'error': str(e),
                'all_units': all_units,
                'purposes': purposes,
                'form_values': post,
            })
