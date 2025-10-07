# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaleOrderLetterQuotation(models.Model):
    _inherit = "sale.order"

    quotation_type = fields.Selection([
        ('standard', 'Standard Quotation'),
        ('letter', 'Letter Quotation'),
    ], string="Quotation Type", default='standard')

    subject = fields.Char(string="Subject")

    # ✅ This is the missing field
    letter_order_line = fields.One2many(
        'sale.order.line', 'order_id',
        string="Letter Quotation Lines",
        domain=[('display_type', '!=', False)],
    )

    @api.onchange('quotation_type')
    def _onchange_quotation_type(self):
        """Auto-load default lines when switching to Letter Quotation."""
        if self.quotation_type == 'letter':
            self.order_line = [(5, 0, 0)]  # clear normal order lines
            order_lines = []

            # Section 1: Customs Clearance
            order_lines.append((0, 0, {
                "display_type": "line_section",
                "name": "Customs Clearance Charges",
            }))

            products_clearance = [
                "Forwarding Fees",
                "Customs Examination (If Any)",
                "Customs Attendance (If Any)",
                "Labour Attendance (If Any)",
                "EFT Fees (If Any)",
                "Const Recovery Measurements (as per port receipt)",
                "Post Storage/SSR Charges/D&D Charges (If Any) as per port receipt",
            ]
            for pname in products_clearance:
                product = self.env["product.product"].search([("name", "=", pname)], limit=1)
                if not product:
                    product = self.env["product.product"].create({
                        "name": pname,
                        "type": "service",
                        "list_price": 0.0,
                    })
                order_lines.append((0, 0, {
                    "product_id": product.id,
                    "product_uom_qty": 1,
                }))

            # Section 2: Transportation
            order_lines.append((0, 0, {
                "display_type": "line_section",
                "name": "Transportation Charges",
            }))

            products_transport = [
                "Haulage Charges",
                "Depot Gate Charges",
                "Warehouse Charges",
            ]
            for pname in products_transport:
                product = self.env["product.product"].search([("name", "=", pname)], limit=1)
                if not product:
                    product = self.env["product.product"].create({
                        "name": pname,
                        "type": "service",
                        "list_price": 0.0,
                    })
                order_lines.append((0, 0, {
                    "product_id": product.id,
                    "product_uom_qty": 1,
                }))

            self.letter_order_line = order_lines
        else:
            self.letter_order_line = [(5, 0, 0)]  # clear letter lines
