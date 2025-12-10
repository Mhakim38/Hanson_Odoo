from odoo import http
from odoo.http import request
from odoo.tools import html_escape


class WebsiteCrmLead(http.Controller):
    @http.route('/plb/enquiry', type='http', auth='public', website=True)
    def enquiry_form(self, **kwargs):
        return request.render('plb_website.template_website_enquiry_form', {})

    @http.route('/plb/enquiry/submit', type='http', auth='public', methods=['POST'], website=True)
    def enquiry_submit(self, **post):
        customer_name = (post.get('customer') or '').strip()
        title = (post.get('title') or '').strip()
        contact_name = (post.get('contact_name') or '').strip()
        phone = (post.get('phone') or '').strip()
        email = (post.get('email_form') or '').strip()
        service = (post.get('service') or '').strip()
        # Don't strip interior newlines; normalize CRLF to LF and strip surrounding whitespace
        raw_message = post.get('message') or ''
        message = raw_message.replace('\r\n', '\n').strip()

        Partner = request.env['res.partner'].sudo()
        partner = None
        if customer_name:
            partner = Partner.search([('name', 'ilike', customer_name), ('is_company', '=', True)], limit=1)
        if not partner and customer_name:
            partner = Partner.create({'name': customer_name, 'is_company': True})

        Lead = request.env['crm.lead'].sudo()
        lead_vals = {
            'name': title or 'Website Enquiry',
            'contact_name': contact_name or False,
            'phone': phone or False,
            'mobile': phone or False,
            'email_from': email or False,
        }
        if partner:
            lead_vals['partner_id'] = partner.id

        # Defensive: only set scope_of_service if it's a valid selection value on the model
        try:
            field = Lead._fields.get('scope_of_service')
            allowed = [v for v, l in (field.selection or [])]
        except Exception:
            allowed = []
        if service and service in allowed:
            lead_vals['scope_of_service'] = service

        # Prepare description with customer message markers; use blank lines to improve readability
        if message:
            desc = '=== Start Customer message ===\n\n' + message + '\n\n=== End Customer message ==='
            lead_vals['description'] = desc

        lead = Lead.create(lead_vals)

        # Post the customer message into the lead chatter as HTML using CSS white-space: pre-wrap
        # so line breaks are preserved without inserting <br/> tags.
        if message:
            escaped = html_escape(message)
            body = (
                '<div style="white-space: pre-wrap; font-family: inherit; font-size: 0.95rem;">'
                '=== Start Customer message ===\n'
                f'{escaped}\n'
                '=== End Customer message ==='
                '</div>'
            )
            try:
                lead.message_post(body=body)
            except Exception:
                # Don't fail the request if message_post encounters an unexpected error
                _ = 0

        return request.render('plb_website.template_website_enquiry_thanks', {'lead': lead})
