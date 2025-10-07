# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrderLetterQuotation(models.Model):
    _inherit = "sale.order"

    dear = fields.Char(string="Dear")
    subject = fields.Char(string="Subject")

    def action_add_default_lines(self):
        """Add default sections and products for Letter Quotation."""
        for order in self:
            if not order.order_line:
                # Customs Clearance Section
                section1 = self.env["sale.order.line"].create({
                    "order_id": order.id,
                    "display_type": "line_section",
                    "name": "Customs Clearance Charges",
                })
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
                    if product:
                        self.env["sale.order.line"].create({
                            "order_id": order.id,
                            "product_id": product.id,
                            "product_uom_qty": 1,
                            "sequence": section1.sequence + 1,
                        })

                # Transportation Section
                section2 = self.env["sale.order.line"].create({
                    "order_id": order.id,
                    "display_type": "line_section",
                    "name": "Transportation Charges",
                })
                products_transport = [
                    "Haulage Charges",
                    "Depot Gate Charges",
                    "Warehouse Charges",
                ]
                for pname in products_transport:
                    product = self.env["product.product"].search([("name", "=", pname)], limit=1)
                    if product:
                        self.env["sale.order.line"].create({
                            "order_id": order.id,
                            "product_id": product.id,
                            "product_uom_qty": 1,
                            "sequence": section2.sequence + 1,
                        })
