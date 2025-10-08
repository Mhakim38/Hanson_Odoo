from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    quotation_type = fields.Selection([
        ('base', 'Base Quotation'),
        ('letter', 'Letter Quotation'),
    ], string="Quotation Type", default='base')

    letter_line_ids = fields.One2many(
        'sale.order.letter.line',
        'order_id',
        string='Letter Quotation Lines',
        default=lambda self: self._default_letter_lines()
    )

    subject = fields.Char(string="Subject")

    show_order_line = fields.Boolean(
        compute='_compute_order_line_visibility',
        string='Show Order Line',
        store=False
    )

    @api.depends('quotation_type')
    def _compute_order_line_visibility(self):
        """Control visibility of base order lines."""
        for order in self:
            order.show_order_line = order.quotation_type == 'base'

    @api.model
    def _default_letter_lines(self):
        # Only provide default lines if context says letter quotation
        ctx = self.env.context or {}
        if ctx.get('default_quotation_type') == 'letter':
            return [
                (0, 0, {'display_type': 'line_section', 'name': 'Customs Clearance Charges'}),
                (0, 0, {'name': 'Forwarding Fees'}),
                (0, 0, {'name': 'Customs Examination'}),
                (0, 0, {'name': 'Customs Attendance'}),
                (0, 0, {'name': 'Labour Attendance'}),
                (0, 0, {'name': 'EFT Fees'}),
                (0, 0, {'name': 'Const Recovery Measurements'}),
                (0, 0, {'name': 'Post Storage/SSR Charges/D&D Charges'}),
                (0, 0, {'display_type': 'line_section', 'name': 'Transportation Charges'}),
                (0, 0, {'name': 'Haulage Charges'}),
                (0, 0, {'name': 'Depot Gate Charges'}),
                (0, 0, {'name': 'Warehouse Charges'}),
            ]
        return []

    @api.onchange('quotation_type')
    def _onchange_quotation_type(self):
        if self.quotation_type == 'letter' and not self.letter_line_ids:
            self.letter_line_ids = [
                (0, 0, {'display_type': 'line_section', 'name': 'Customs Clearance Charges'}),
                (0, 0, {'name': 'Forwarding Fees'}),
                (0, 0, {'name': 'Customs Examination'}),
                (0, 0, {'name': 'Customs Attendance'}),
                (0, 0, {'name': 'Labour Attendance'}),
                (0, 0, {'name': 'EFT Fees'}),
                (0, 0, {'name': 'Const Recovery Measurements'}),
                (0, 0, {'name': 'Post Storage/SSR Charges/D&D Charges'}),
                (0, 0, {'display_type': 'line_section', 'name': 'Transportation Charges'}),
                (0, 0, {'name': 'Haulage Charges'}),
                (0, 0, {'name': 'Depot Gate Charges'}),
                (0, 0, {'name': 'Warehouse Charges'}),
            ]

    def create(self, vals):
        # No auto-fill here; handled by default
        return super().create(vals)


class SaleOrderLetterLine(models.Model):
    _name = 'sale.order.letter.line'
    _description = 'Sale Order Letter Line'

    order_id = fields.Many2one(
        'sale.order',
        string='Order Reference',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
    )
    name = fields.Char(
        string='Description',
        required=False
    )
    product_uom_qty = fields.Float(
        string='Quantity',
        default=1.0,
    )
    product_uom = fields.Many2one(
        'uom.uom',
        string='Unit of Measure'
    )
    price_unit = fields.Float(
        string='Unit Price'
    )
    price_subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_amount',
        store=True
    )
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note')
    ], string='Display Type')

    @api.depends('product_uom_qty', 'price_unit')
    def _compute_amount(self):
        for line in self:
            if not line.display_type:
                line.price_subtotal = line.product_uom_qty * line.price_unit
            else:
                line.price_subtotal = 0.0
