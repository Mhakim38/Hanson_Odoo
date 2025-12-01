from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # 1. Contract details
    contract_type = fields.Selection(
        [('long_term', 'Long Term'), ('adhoc', 'Adhoc')],
        string='Contract Period / Frequency',
        default='long_term'
    )
    # Make contract_months editable by user. Server constraint enforces ranges.
    contract_months = fields.Integer(
        string='Contract Months',
        default=12,
    )

    expected_start_date = fields.Date(string='Expected Start Date')
    date_go_live = fields.Date(string='Date Go Live')

    # New: Date Secured (user fills when won)
    date_secured = fields.Date(string='Date Secured')

    # New: allow uploading a single attachment on the lead (stored on the record)
    # This is intentionally a Binary field so we can apply the same 'only when stage is Contract' logic
    attachment_file = fields.Binary(string='Attachment File')
    attachment_filename = fields.Char(string='Attachment Filename')

    # 2. Scope of Service and Freight details
    scope_of_service = fields.Selection([
        ('haulage', 'Haulage'),
        ('freight_forwarding', 'Freight Forwarding'),
        ('warehousing', 'Warehousing'),
        ('depot_yard', 'Depot / Yard'),
        ('distribution', 'Distribution'),
    ], string='Scope of Service')

    freight_type = fields.Selection([
        ('sfr', 'SFR'),
        ('fcl', 'FCL'),
        ('lcl', 'LCL'),
        ('afr', 'AFR'),
        ('fwd', 'FWD'),
    ], string='Freight Type')

    @api.depends('scope_of_service')
    def _compute_show_freight_type(self):
        for rec in self:
            rec.show_freight_type = rec.scope_of_service == 'freight_forwarding'

    show_freight_type = fields.Boolean(compute='_compute_show_freight_type', store=False)

    # 3. Locations
    origin_country_id = fields.Many2one('res.country', string='Origin Country')
    destination_country_id = fields.Many2one('res.country', string='Destination Country')

    port_of_loading_id = fields.Many2one(
        'crm.port',
        string='Port of Loading',
        help='Select the port from your CRM Ports list',
    )
    port_of_destination_id = fields.Many2one(
        'crm.port',
        string='Port of Destination',
        help='Select the port from your CRM Ports list',
    )

    product = fields.Char(
        string='Customer Product',
    )

    # 5. Additional info
    dept_region = fields.Selection([
        ('central', 'Central'),
        ('northern', 'Northern'),
        ('southern', 'Southern'),
    ], string='Dept/Region')

    realized_revenue_fy2025 = fields.Monetary(
        string='Realized Revenue FY2025 (MYR)',
        currency_field='company_currency_id'
    )

    # Hidden per request: category_type is intentionally left on the model (if needed elsewhere)
    category_type = fields.Selection([
        ('1', 'Organic Growth of Current Customer'),
        ('2', 'Cross Selling'),
        ('3', 'Opportunity Sales / New Customers'),
        ('4', 'Al Bukhary New Business'),
    ], string='Category')

    # Currency helper (existing)
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Currency',
        readonly=True
    )

    # New fields requested
    remark = fields.Text(string='Remark')
    # Use tags for multiple emails (many2many), since direct access to stand-alone email records is not allowed.
    tag_ids = fields.Many2many('crm.lead.tag', 'crm_lead_tag_rel', 'lead_id', 'tag_id', string='Other Emails',
                               help='Tag-style free-form email entries (enter multiple).')

    operating_profit_margin = fields.Float(
        string='Operating Profit Margin (%)',
        digits=(5, 2),
    )

    expected_revenue_annum = fields.Monetary(
        string='Expected Revenue (Annum)',
        currency_field='company_currency_id'
    )

    # New helper boolean for views: True when the current stage is the 'contract' stage
    is_contract_stage = fields.Boolean(string='Is Contract Stage', compute='_compute_is_contract_stage')

    @api.depends('stage_id')
    def _compute_is_contract_stage(self):
        for rec in self:
            rec.is_contract_stage = bool(rec.stage_id and (getattr(rec.stage_id, 'name', '') or '').strip().lower() == 'contract')

    # === COMPUTE METHODS ===
    # Note: contract_months is user-editable. Validation is handled by _check_contract_months.

    # Helper to determine if a stage should be treated as 'won'.
    def _is_won_stage(self):
        self.ensure_one()
        if not self.stage_id:
            return False
        # Prefer probability if configured, otherwise fall back to name == 'won' or 'contract'
        prob = getattr(self.stage_id, 'probability', False)
        if prob and prob >= 100:
            return True
        name = (self.stage_id.name or '').strip().lower()
        if name in ('won', 'contract'):
            return True
        return False

    @api.constrains('contract_type', 'contract_months')
    def _check_contract_months(self):
        for rec in self:
            if rec.contract_type == 'adhoc':
                if not (1 <= (rec.contract_months or 0) <= 11):
                    raise ValidationError('Adhoc contracts must have Contract Months between 1 and 11.')
            elif rec.contract_type == 'long_term':
                if (rec.contract_months or 0) < 12:
                    raise ValidationError('Long Term contracts must have Contract Months of at least 12.')

    @api.onchange('contract_type', 'contract_months')
    def _onchange_contract_months(self):
        """Provide an immediate UI warning when contract_months is outside allowed ranges for the selected contract_type."""
        for rec in self:
            if rec.contract_type == 'adhoc':
                if not (1 <= (rec.contract_months or 0) <= 11):
                    return {
                        'warning': {
                            'title': 'Invalid Contract Months',
                            'message': 'Adhoc contracts must have Contract Months between 1 and 11.'
                        }
                    }
            elif rec.contract_type == 'long_term':
                if (rec.contract_months or 0) >=1 and (rec.contract_months or 0) <=11:
                    return {
                        'warning': {
                            'title': 'Invalid Contract Months',
                            'message': 'Long Term contracts must have Contract Months of at least 12.'
                        }
                    }

    @api.constrains('stage_id', 'date_secured')
    def _check_won_requirements(self):
        Attachment = self.env['ir.attachment']
        for rec in self:
            if rec._is_won_stage():
                # date_secured must be set when lead is won
                if not rec.date_secured:
                    raise ValidationError('Please set the Date Secured when the lead is marked as Won.')
                # At least one attachment must be present for this lead
                att_count = Attachment.search_count([
                    ('res_model', '=', 'crm.lead'),
                    ('res_id', '=', rec.id),
                ])
                # Consider either an attached ir.attachment record OR the new binary field as satisfying the requirement
                if att_count == 0 and not rec.attachment_file:
                    raise ValidationError('Please attach at least one document to the lead when marking it as Won.')

    # === Prevent date_secured being set unless stage == 'contract' ===
    def _stage_is_contract(self, stage):
        """Return True if the given stage record or id refers to a 'contract' stage by name."""
        if not stage:
            return False
        if isinstance(stage, int):
            stage = self.env['crm.stage'].browse(stage)
        # safe lower-case compare of name
        name = (getattr(stage, 'name', '') or '').strip().lower()
        return name == 'contract'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # if user provided date_secured, ensure stage in vals is contract (or stage_id in context)
            if 'date_secured' in vals and vals.get('date_secured'):
                stage_id = vals.get('stage_id')
                if not stage_id:
                    # if no stage provided, try to get default stage from team or use False
                    stage_id = vals.get('section_id') and self.env['crm.stage'].search([('team_id', '=', vals.get('section_id'))], limit=1).id
                if not self._stage_is_contract(stage_id):
                    raise ValidationError('Date Secured can only be set when the lead stage is Contract.')
            # if user provided attachment_file, ensure stage in vals is contract as well
            if 'attachment_file' in vals and vals.get('attachment_file'):
                stage_id = vals.get('stage_id')
                if not stage_id:
                    stage_id = vals.get('section_id') and self.env['crm.stage'].search([('team_id', '=', vals.get('section_id'))], limit=1).id
                if not self._stage_is_contract(stage_id):
                    raise ValidationError('Attachment can only be added when the lead stage is Contract.')
        return super(CrmLead, self).create(vals_list)

    def write(self, vals):
        # For each record, check if date_secured is being set/changed while stage is not (or will not be) contract
        for rec in self:
            # Determine resulting stage id after write
            new_stage_id = vals.get('stage_id', False)
            # If stage is not in vals, use existing stage id
            effective_stage = new_stage_id if new_stage_id else rec.stage_id.id
            # If date_secured included in vals, ensure effective stage is contract
            if 'date_secured' in vals:
                # If date_secured is being changed/added but effective stage isn't contract -> block
                if not self._stage_is_contract(effective_stage):
                    raise ValidationError('Date Secured can only be set when the lead stage is Contract.')
            # If attachment_file included in vals, ensure effective stage is contract
            if 'attachment_file' in vals:
                # If attachment is being added/changed but effective stage isn't contract -> block
                if vals.get('attachment_file') and not self._stage_is_contract(effective_stage):
                    raise ValidationError('Attachment can only be added when the lead stage is Contract.')
        return super(CrmLead, self).write(vals)


# New tag model to represent email-like tags (used via many2many_tags on crm.lead)
class CrmLeadTag(models.Model):
    _name = 'crm.lead.tag'
    _description = 'CRM Lead Email Tag'

    name = fields.Char(string='Name', required=True)
    color = fields.Integer(string='Color')
    tag_type = fields.Selection([
        ('crm', 'CRM'),
        ('behavior', 'Behavior'),
    ], string='Tag Type', default='crm', required=True)
