from odoo import http, fields
from odoo.http import request

class VisitorVerifyController(http.Controller):

    @http.route(['/visitor/verify/<string:token>'], type='http', auth='public', website=True)
    def verify_qr(self, token, **kwargs):
        """Verify visitor QR code and show visit details."""
        visit = request.env['estate.visit'].sudo().search([('qr_token', '=', token)], limit=1)
        if not visit:
            return request.render('visitor_mgmt.qr_invalid_template')
        # Check expiry: QR valid only until the end of the scheduled day (visit.qr_expiry)
        try:
            now = fields.Datetime.now()
            exp = visit.qr_expiry
            if exp:
                # Normalize to datetime objects if necessary
                try:
                    if isinstance(exp, str):
                        exp_dt = fields.Datetime.from_string(exp)
                    else:
                        exp_dt = exp
                except Exception:
                    exp_dt = exp
                try:
                    if isinstance(now, str):
                        now_dt = fields.Datetime.from_string(now)
                    else:
                        now_dt = now
                except Exception:
                    now_dt = now
                # If current time is after expiry, show invalid page
                if now_dt and exp_dt and now_dt > exp_dt:
                    return request.render('visitor_mgmt.qr_invalid_template')
        except Exception:
            # On any unexpected error, fall back to invalid to be safe
            return request.render('visitor_mgmt.qr_invalid_template')

        return request.render('visitor_mgmt.qr_verify_template', {
            'visit': visit,
        })

    @http.route(['/visitor/info/<string:token>'], type='http', auth='public', website=True)
    def visitor_info(self, token, **kwargs):
        """Show basic visitor information when scanning a visitor-specific QR."""
        visitor = request.env['estate.visitor'].sudo().search([('qr_token', '=', token)], limit=1)
        if not visitor:
            return request.render('visitor_mgmt.qr_invalid_template')
        # If visitor has qr_expiry, ensure it's still valid
        try:
            now = fields.Datetime.now()
            exp = visitor.qr_expiry
            if exp:
                try:
                    exp_dt = fields.Datetime.from_string(exp) if isinstance(exp, str) else exp
                except Exception:
                    exp_dt = exp
                try:
                    now_dt = fields.Datetime.from_string(now) if isinstance(now, str) else now
                except Exception:
                    now_dt = now
                if now_dt and exp_dt and now_dt > exp_dt:
                    return request.render('visitor_mgmt.qr_invalid_template')
        except Exception:
            return request.render('visitor_mgmt.qr_invalid_template')

        return request.render('visitor_mgmt.visitor_info_template', {
            'visitor': visitor,
        })

    @http.route(['/visitor/scan'], type='http', auth='public', website=True)
    def visitor_scan(self, **kwargs):
        """Serve a small scanner page that opens the camera and reads QR codes.
        Uses html5-qrcode (served from CDN) to access the camera in the browser.
        On success, the JS will redirect to the appropriate visitor/verify or visitor/info URL.
        """
        return request.render('visitor_mgmt.visitor_scan_template')

    @http.route(['/visitor/action'], type='http', auth='public', website=True, methods=['POST'])
    def visitor_action(self, **post):
        """Handle form actions from visitor verification page: check_in or check_out.

        Expects POST parameters: visit_id, action_type ('check_in' or 'check_out').
        After performing the action, redirects to /guard/visitors.
        """
        visit_id = post.get('visit_id')
        action_type = post.get('action_type')
        try:
            if not visit_id:
                return request.redirect('/guard/visitors')
            Visit = request.env['estate.visit'].sudo()
            visit = Visit.browse(int(visit_id))
            if not visit.exists():
                return request.redirect('/guard/visitors')

            if action_type == 'check_in':
                # Prefer model action which performs validations
                try:
                    visit.action_guard_checkin()
                except Exception:
                    # fallback: ensure visitor not blacklisted then write
                    if visit.visitor_id.blacklisted:
                        # do nothing, redirect back
                        pass
                    else:
                        try:
                            visit._assign_badge()
                        except Exception:
                            pass
                        visit.write({
                            'state': 'check_in',
                            'check_in_at': fields.Datetime.now(),
                            'check_in_mode': 'qr',
                        })
            elif action_type == 'check_out':
                try:
                    visit.action_guard_checkout()
                except Exception:
                    # fallback: only allow if currently checked in
                    if visit.state == 'check_in':
                        visit.write({
                            'state': 'check_out',
                            'check_out_at': fields.Datetime.now(),
                        })
            # Redirect to guard visitors listing
            return request.redirect('/guard/visitors')
        except Exception:
            # On unexpected errors, still redirect back to guard page
            return request.redirect('/guard/visitors')
