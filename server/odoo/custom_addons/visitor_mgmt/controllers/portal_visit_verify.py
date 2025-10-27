from odoo import http
from odoo.http import request

class VisitorVerifyController(http.Controller):

    @http.route(['/visitor/verify/<string:token>'], type='http', auth='public', website=True)
    def verify_qr(self, token, **kwargs):
        """Verify visitor QR code and show visit details."""
        visit = request.env['estate.visit'].sudo().search([('qr_token', '=', token)], limit=1)
        if not visit:
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
