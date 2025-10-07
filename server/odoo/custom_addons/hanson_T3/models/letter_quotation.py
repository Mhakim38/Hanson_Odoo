from odoo import models, fields

class LetterQuotation(models.Model):
    _name = "letter.quotation"
    _description = "Letter Quotation"

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('letter.quotation'))
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    quotation_subject = fields.Char(string="Subject")
    date = fields.Date(string="Date", default=fields.Date.today)
    order_line_ids = fields.One2many('letter.quotation.line', 'quotation_id', string="Order Lines")
