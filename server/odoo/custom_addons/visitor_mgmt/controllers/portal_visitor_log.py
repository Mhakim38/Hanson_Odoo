from odoo import http
from odoo.http import request
import re
import base64

class VisitorLogPortal(http.Controller):

    @http.route(['/portal/visitor-log'], type='http', auth="user", website=True)
    def portal_visitor_log(self, **kw):
        """Display the visitor log for the logged-in partner (resident)."""
        partner = request.env.user.partner_id

        # Get visits linked to this partner’s units (owner or resident)
        visits = request.env['estate.visit'].sudo().search([
            '|',
            ('unit_id.owner_id', '=', partner.id),
            ('unit_id.resident_partner_ids', 'in', partner.id)
        ], order='schedule_from desc')

        # Build a mapping of visit.id -> QR data URL to ensure templates can reliably render images
        qr_map = {}
        try:
            for v in visits:
                try:
                    qr_val = v.sudo().qr_image or ''
                    # handle bytes returned as python bytes or data URLs
                    if isinstance(qr_val, bytes):
                        try:
                            qr_str = qr_val.decode('utf-8')
                        except Exception:
                            qr_str = base64.b64encode(qr_val).decode('ascii')
                    else:
                        qr_str = qr_val
                    if isinstance(qr_str, str) and qr_str:
                        # If it's a data: URL, extract payload
                        if qr_str.startswith('data:'):
                            try:
                                _, payload = qr_str.split(',', 1)
                                qr_str = payload
                            except Exception:
                                qr_str = re.sub(r"^data:.*;base64,", '', qr_str)
                        # Remove Python bytes literal markers and whitespace
                        if qr_str.startswith("b'") or qr_str.startswith('b"'):
                            qr_str = qr_str[2:]
                            if qr_str.endswith("'") or qr_str.endswith('"'):
                                qr_str = qr_str[:-1]
                        qr_str = re.sub(r'\s+', '', qr_str)
                        if qr_str:
                            qr_map[v.id] = 'data:image/png;base64,%s' % qr_str
                except Exception:
                    qr_map[v.id] = ''
        except Exception:
            qr_map = {}

        values = {
            'partner': partner,
            'visits': visits,
            'qr_map': qr_map,
        }

        return request.render('visitor_mgmt.portal_visitor_log', values)
