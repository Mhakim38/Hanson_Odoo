from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    port_order_line_ids = fields.One2many(
        'sale.order.port.line', 'order_id', string="Port Rates"
    )

class SaleOrderPortLine(models.Model):
    _name = 'sale.order.port.line'
    _description = 'Port Rates Order Line'

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    port = fields.Char("Port")
    validation = fields.Char("Validation")
    export_rate = fields.Float("Export Rates")
    inclusive = fields.Char("Inclusive")
