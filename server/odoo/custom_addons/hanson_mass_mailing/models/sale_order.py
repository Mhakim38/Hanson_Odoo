from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    mailing_id = fields.Many2one(
        'mailing.mailing',
        string="Mailing Template",
        help="Select or create an email template for this sale order."
    )

    mail_body = fields.Html(
        related="mailing_id.body_html",
        store=True,
        readonly=False,
        string="Mail Body"
    )
