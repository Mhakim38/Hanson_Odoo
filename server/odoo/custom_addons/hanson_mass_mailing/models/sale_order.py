from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    mail_body = fields.Html(
        string="Mail Body",
        sanitize=False,
        help="Body of the email for this sale order."
    )

    mailing_id = fields.Many2one(
        'mailing.mailing',
        string="Mailing Template",
        help="Select or create an email template for this sale order."
    )

    @api.onchange('mailing_id')
    def _onchange_mailing_id(self):
        """When a mailing template is selected, update mail_body preview."""
        if self.mailing_id:
            self.mail_body = self.mailing_id.body_html or ''
        else:
            self.mail_body = ''

    @api.model
    def _get_default_email_template(self):
        return self.env.ref('sale.email_template_edi_sale', raise_if_not_found=False)

    def action_quotation_send(self):
        """Override 'Send by Email' to include custom mail body."""
        self.ensure_one()
        template = self._get_default_email_template()

        ctx = {
            'default_model': 'sale.order',
            'default_res_ids': [self.id],  # ✅ Odoo 17 syntax
            'default_use_template': bool(template),
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_paynow",
        }

        if self.mail_body:
            ctx['default_body'] = self.mail_body
            ctx['default_body_html'] = self.mail_body

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'target': 'new',
            'context': ctx,
        }
