from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    quotation_type = fields.Selection([
        ('quotation', 'Quotation'),
        ('port_rate', 'Port Rate Quotation'),
        ('letter', 'Letter Quotation'),
    ], string="Quotation Type", default='quotation')

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
            order.show_order_line = order.quotation_type == 'port_rate'

    @api.model
    def _get_letter_item_line(self, name):
        product = self.env['product.product'].search([('name', '=', name)], limit=1)
        if not product:
            # Create the product if it does not exist
            product = self.env['product.product'].create({
                'name': name,
                'type': 'service',
                'sale_ok': True,
                'purchase_ok': False,
            })
        return {'product_id': product.id, 'name': product.name}

    @api.model
    def _default_letter_lines(self):
        ctx = self.env.context or {}
        if ctx.get('default_quotation_type') == 'letter':
            return [
                (0, 0, {'display_type': 'line_section', 'name': 'Customs Clearance Charges'}),
                (0, 0, self._get_letter_item_line('Forwarding Fees')),
                (0, 0, self._get_letter_item_line('Customs Examination')),
                (0, 0, self._get_letter_item_line('Customs Attendance')),
                (0, 0, self._get_letter_item_line('Labour Attendance')),
                (0, 0, self._get_letter_item_line('EFT Fees')),
                (0, 0, self._get_letter_item_line('Const Recovery Measurements')),
                (0, 0, self._get_letter_item_line('Post Storage/SSR Charges/D&D Charges')),
                (0, 0, {'display_type': 'line_section', 'name': 'Transportation Charges'}),
                (0, 0, self._get_letter_item_line('Haulage Charges')),
                (0, 0, self._get_letter_item_line('Depot Gate Charges')),
                (0, 0, self._get_letter_item_line('Warehouse Charges')),
            ]
        return []

    @api.onchange('quotation_type')
    def _onchange_quotation_type(self):
        if self.quotation_type == 'letter' and not self.letter_line_ids:
            self.letter_line_ids = [
                (0, 0, {'display_type': 'line_section', 'name': 'Customs Clearance Charges'}),
                (0, 0, self._get_letter_item_line('Forwarding Fees')),
                (0, 0, self._get_letter_item_line('Customs Examination')),
                (0, 0, self._get_letter_item_line('Customs Attendance')),
                (0, 0, self._get_letter_item_line('Labour Attendance')),
                (0, 0, self._get_letter_item_line('EFT Fees')),
                (0, 0, self._get_letter_item_line('Const Recovery Measurements')),
                (0, 0, self._get_letter_item_line('Post Storage/SSR Charges/D&D Charges')),
                (0, 0, {'display_type': 'line_section', 'name': 'Transportation Charges'}),
                (0, 0, self._get_letter_item_line('Haulage Charges')),
                (0, 0, self._get_letter_item_line('Depot Gate Charges')),
                (0, 0, self._get_letter_item_line('Warehouse Charges')),
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
    tax_id = fields.Many2many(
        'account.tax',
        'sale_order_letter_line_tax_rel',
        'letter_line_id', 'tax_id',
        string='Taxes'
    )

    @api.depends('product_uom_qty', 'price_unit')
    def _compute_amount(self):
        for line in self:
            if not line.display_type:
                line.price_subtotal = line.product_uom_qty * line.price_unit
            else:
                line.price_subtotal = 0.0
