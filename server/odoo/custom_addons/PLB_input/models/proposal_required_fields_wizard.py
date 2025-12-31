from odoo import api, fields, models


class ProposalRequiredFieldsWizard(models.TransientModel):
    _name = 'proposal.required.fields.wizard'
    _description = 'Proposal Required Fields Wizard'

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True)
    target_stage_id = fields.Many2one('crm.stage', string='Target Stage')
    message = fields.Text(string='Message', readonly=True)

    # Required fields from crm.lead
    operating_profit_margin = fields.Float(
        string='Operating Profit Margin (%)',
        digits=(5, 2),
    )
    expected_revenue_annum = fields.Monetary(
        string='Expected Revenue (Annum)',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one('res.currency', string='Currency')

    # Freight forwarding fields (only shown when scope_of_service is freight_forwarding)
    scope_of_service = fields.Selection(related='lead_id.scope_of_service', string='Scope of Service')
    freight_type = fields.Selection([
        ('sfr', 'SFR'),
        ('fcl', 'FCL'),
        ('lcl', 'LCL'),
        ('afr', 'AFR'),
        ('fwd', 'FWD'),
    ], string='Freight Type')
    origin_country_id = fields.Many2one('res.country', string='Origin Country')
    destination_country_id = fields.Many2one('res.country', string='Destination Country')
    port_of_loading_id = fields.Many2one('crm.port', string='Port of Loading')
    port_of_destination_id = fields.Many2one('crm.port', string='Port of Destination')
    product = fields.Char(string='Customer Product')

    # Quotation attachment
    quotation_attachment = fields.Binary(string='Quotation Attachment')
    quotation_attachment_filename = fields.Char(string='Filename')

    # Show freight fields
    show_freight_fields = fields.Boolean(compute='_compute_show_freight_fields')

    @api.depends('scope_of_service')
    def _compute_show_freight_fields(self):
        for rec in self:
            rec.show_freight_fields = rec.scope_of_service == 'freight_forwarding'

    def action_save_and_continue(self):
        """Save the filled fields to the lead and move to the target stage"""
        self.ensure_one()

        vals = {}
        if self.operating_profit_margin:
            vals['operating_profit_margin'] = self.operating_profit_margin
        if self.expected_revenue_annum:
            vals['expected_revenue_annum'] = self.expected_revenue_annum
        if self.quotation_attachment:
            vals['quotation_attachment'] = self.quotation_attachment
            vals['quotation_attachment_filename'] = self.quotation_attachment_filename

        # Freight forwarding fields
        if self.show_freight_fields:
            if self.freight_type:
                vals['freight_type'] = self.freight_type
            if self.origin_country_id:
                vals['origin_country_id'] = self.origin_country_id.id
            if self.destination_country_id:
                vals['destination_country_id'] = self.destination_country_id.id
            if self.port_of_loading_id:
                vals['port_of_loading_id'] = self.port_of_loading_id.id
            if self.port_of_destination_id:
                vals['port_of_destination_id'] = self.port_of_destination_id.id
            if self.product:
                vals['product'] = self.product

        # Add the target stage to move to after filling required fields
        if self.target_stage_id:
            vals['stage_id'] = self.target_stage_id.id

        # Update the lead with the filled values
        # Use skip_proposal_check context to bypass validation temporarily
        if vals:
            self.lead_id.with_context(skip_proposal_check=True).write(vals)

        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Cancel and revert to Qualify stage"""
        self.ensure_one()
        # Find qualify stage and revert
        qualify_stage = self.lead_id._find_qualify_stage(
            team_id=self.lead_id.team_id.id if self.lead_id.team_id else False
        )
        if qualify_stage:
            self.lead_id.with_context(skip_proposal_check=True).write({'stage_id': qualify_stage.id})
        return {'type': 'ir.actions.act_window_close'}

