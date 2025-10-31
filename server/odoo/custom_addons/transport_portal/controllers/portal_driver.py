from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
import base64


class PortalDriver(http.Controller):

    @http.route(['/my/drivers'], type='http', auth='user', website=True)
    def portal_my_drivers(self, **kwargs):
        search = kwargs.get('search', '')
        domain = []
        if search:
            domain = ['|', ('name.name', 'ilike', search), ('transporter_id.name', 'ilike', search)]
        drivers = request.env['res.driver'].sudo().search(domain)

        return request.render('transport_portal.portal_my_drivers', {
            'driver_list': drivers,
            'search': search,
        })

    @http.route(['/my/driver', '/my/driver/<int:driver_id>'], type='http', auth='user', website=True)
    def portal_my_driver(self, driver_id=None, **kw):
        Driver = request.env['res.driver'].sudo()
        driver = Driver.browse(driver_id) if driver_id else None
        transporter_list = request.env['res.transporter'].sudo().search([])
        partner_list = request.env['res.partner'].sudo().search([])

        return request.render('transport_portal.portal_my_driver_form', {
            'driver': driver,
            'transporter_list': transporter_list,
            'partner_list': partner_list,
        })

    @http.route(['/my/driver/save'], type='http', auth='user', website=True, methods=['POST'])
    def portal_save_driver(self, **post):
        required_fields = ['name', 'driver_license_no', 'driver_license_expiry', 'driver_ic', 'transporter_id']
        missing = [f for f in required_fields if not post.get(f)]
        if missing:
            error_msg = "Please fill all required fields before submitting."
            transporter_list = request.env['res.transporter'].sudo().search([])
            partner_list = request.env['res.partner'].sudo().search([])
            return request.render('transport_portal.portal_my_driver_form', {
                'error': error_msg,
                'driver': None,
                'transporter_list': transporter_list,
                'partner_list': partner_list,
            })

        vals = {
            'name': int(post.get('name')) if post.get('name') else False,
            'driver_license_no': post.get('driver_license_no'),
            'driver_license_expiry': post.get('driver_license_expiry'),
            'driver_ic': post.get('driver_ic'),
            'active': 'active' in post,
            'transporter_id': int(post.get('transporter_id')) if post.get('transporter_id') else False,
        }
        # Handle uploaded images
        for field_name in ['driver_image', 'driver_license_image', 'driver_ic_image']:
            file = post.get(field_name)
            if file and hasattr(file, 'read'):
                vals[field_name] = base64.b64encode(file.read())
            else:
                # Kalau edit dan tak upload gambar baru, kekalkan gambar lama
                if post.get('driver_id'):
                    old_record = request.env['res.driver'].sudo().browse(int(post['driver_id']))
                    if old_record.exists():
                        vals[field_name] = old_record[field_name]

        # Create or Update
        if post.get('driver_id'):
            driver = request.env['res.driver'].sudo().browse(int(post['driver_id']))
            if driver.exists():
                driver.write(vals)
        else:
            request.env['res.driver'].sudo().create(vals)

        return request.redirect('/my/drivers')
