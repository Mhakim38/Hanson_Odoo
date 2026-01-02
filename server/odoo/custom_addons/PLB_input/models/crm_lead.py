from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError, AccessError


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

    realized_revenue = fields.Monetary(
        string='Realized Revenue (MYR)',
        currency_field='company_currency_id',
        compute='_compute_realized_revenue',
        store=True,
        readonly=False
    )

    @api.depends('expected_revenue', 'contract_months', 'expected_start_date')
    def _compute_realized_revenue(self):
        """
        Calculate realized revenue based on:
        - MAR (Monthly Annualized Revenue) = Expected Revenue / Contract Months
        - RR = MAR * (12 - Current Month(Expected Start Date) + 1)
        """
        for rec in self:
            realized_revenue = 0.0

            sales = rec.expected_revenue or 0.0
            contract_months = rec.contract_months or 0
            expected_start = rec.expected_start_date

            # Only calculate if we have all required fields
            if not expected_start or not contract_months or contract_months <= 0:
                rec.realized_revenue = 0.0
                continue

            # Parse start month from expected_start_date
            start_month = None
            if isinstance(expected_start, str):
                try:
                    start_month = int(expected_start.split('-')[1])
                except Exception:
                    start_month = None
            else:
                try:
                    start_month = expected_start.month
                except Exception:
                    start_month = None

            # Validate start_month
            if not start_month or start_month < 1 or start_month > 12:
                rec.realized_revenue = 0.0
                continue

            # Calculate MAR (Monthly Annualized Revenue)
            mar = float(sales) / float(contract_months)

            # Calculate RR = MAR * (12 - start_month + 1)
            months_in_year = 12 - start_month + 1
            realized_revenue = mar * months_in_year

            rec.realized_revenue = realized_revenue

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
    # Note: historically this was 'contract'; updated to reflect new business rule:
    # fields that were previously allowed only in the 'Contract' stage are now allowed
    # when the stage name contains 'shortlisted' or 'verbal'. The field name is
    # kept as `is_contract_stage` for compatibility with existing views/modifiers.
    is_contract_stage = fields.Boolean(string='Is Shortlisted/Verbal Stage', compute='_compute_is_contract_stage')

    @api.depends('stage_id')
    def _compute_is_contract_stage(self):
        for rec in self:
            name = (getattr(rec.stage_id, 'name', '') or '').strip().lower()
            rec.is_contract_stage = bool(name and ("shortlisted" in name or "verbal" in name))

    # New helper boolean for views: True when the current stage name contains 'decline'
    is_decline_stage = fields.Boolean(string='Is Decline Stage', compute='_compute_is_decline_stage', store=True)

    @api.depends('stage_id')
    def _compute_is_decline_stage(self):
        for rec in self:
            rec.is_decline_stage = bool(rec.stage_id and ('decline' in (getattr(rec.stage_id, 'name', '') or '').strip().lower()))

    # New helper boolean for views: True when the current stage name contains 'qualify'
    # Used by view modifiers to make certain fields required/editable in the Qualify stage.
    is_qualify_stage = fields.Boolean(string='Is Qualify Stage', compute='_compute_is_qualify_stage', store=True)

    @api.depends('stage_id')
    def _compute_is_qualify_stage(self):
        for rec in self:
            rec.is_qualify_stage = bool(rec.stage_id and ('qualify' in (getattr(rec.stage_id, 'name', '') or '').strip().lower()))

    # New helper boolean for views: True when stage is "Proposal Submitted" or later (for freight forwarding mandatory fields)
    is_proposal_submitted_stage = fields.Boolean(string='Is Proposal Submitted Stage', compute='_compute_is_proposal_submitted_stage', store=True)

    @api.depends('stage_id')
    def _compute_is_proposal_submitted_stage(self):
        """Return True if stage name contains 'proposal' and 'submitted' (case-insensitive)"""
        for rec in self:
            name = (getattr(rec.stage_id, 'name', '') or '').strip().lower()
            rec.is_proposal_submitted_stage = bool(name and 'proposal' in name and 'submitted' in name)

    # New helper boolean for views: True when stage is "Contract" or "Loss" (read-only stage)
    is_readonly_stage = fields.Boolean(string='Is Read-Only Stage', compute='_compute_is_readonly_stage', store=True)

    @api.depends('stage_id')
    def _compute_is_readonly_stage(self):
        """Return True if stage name contains 'contract' or 'loss' (case-insensitive)"""
        for rec in self:
            name = (getattr(rec.stage_id, 'name', '') or '').strip().lower()
            rec.is_readonly_stage = bool(name and ('contract' in name or 'loss' in name))

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
                # if att_count == 0 and not rec.attachment_file:
                #     raise ValidationError('Please attach at least one document to the lead when marking it as Won.')

    # === Prevent date_secured being set unless stage == 'contract' ===
    def _stage_is_contract(self, stage):
        """Return True if the given stage record or id refers to a 'contract' stage by name."""
        # Accept either a record, id, or falsy value. We treat stages whose names
        # contain 'shortlisted' or 'verbal' (case-insensitive) as the stages that
        # allow attachment_file and date_secured.
        if not stage:
            return False
        if isinstance(stage, int):
            stage = self.env['crm.stage'].browse(stage)
        name = (getattr(stage, 'name', '') or '').strip().lower()
        return bool(name and ("shortlisted" in name or "verbal" in name))

    # --- New: fields that must be provided during Qualify before moving to Proposal ---
    # Quotation attachment (separate from attachment_file which is used for "won" flows)
    quotation_attachment = fields.Binary(string='Quotation Attachment')
    quotation_attachment_filename = fields.Char(string='Quotation Attachment Filename')

    # Helper to detect Qualify / Proposal stages by name (case-insensitive contains)
    def _stage_name_contains(self, stage, keyword):
        if not stage:
            return False
        if isinstance(stage, int):
            stage = self.env['crm.stage'].browse(stage)
        name = (getattr(stage, 'name', '') or '').strip().lower()
        return bool(name and keyword in name)

    def _is_proposal_stage(self):
        self.ensure_one()
        return self._stage_name_contains(self.stage_id, 'proposal')

    def _is_qualify_stage(self):
        self.ensure_one()
        return self._stage_name_contains(self.stage_id, 'qualify')

    def _find_qualify_stage(self, team_id=False):
        Stage = self.env['crm.stage']
        domain = [('name', 'ilike', 'qualify')]
        if team_id:
            # prefer team-specific or global (False)
            stage = Stage.search([('name', 'ilike', 'qualify'), ('team_id', 'in', (team_id, False))], limit=1)
            if stage:
                return stage
        return Stage.search(domain, limit=1)

    @api.onchange('stage_id')
    def _onchange_stage_require_qualify_fields(self):
        """When user selects a Proposal stage, ensure required fields (operating_profit_margin,
        expected_revenue_annum and quotation_attachment) have been filled. If not, revert to a Qualify stage
        and show a friendly warning.

        Additionally, when moving to Proposal Submitted stage with Freight Forwarding scope,
        ensure all freight forwarding fields are filled.
        """
        for rec in self:
            if not rec.stage_id:
                continue

            stage_name = (getattr(rec.stage_id, 'name', '') or '').strip().lower()

            # Check for Proposal stage requirements
            if self._stage_name_contains(rec.stage_id, 'proposal'):
                missing = []
                if rec.operating_profit_margin in (False, None):
                    missing.append('Operating Profit Margin')
                if not rec.expected_revenue_annum:
                    missing.append('Expected Revenue (Annum)')
                # Accept either the dedicated quotation_attachment binary OR any existing ir.attachment for this lead
                att_ok = False
                if rec.quotation_attachment:
                    att_ok = True
                else:
                    Attachment = self.env['ir.attachment']
                    if rec.id:
                        count = Attachment.search_count([('res_model', '=', 'crm.lead'), ('res_id', '=', rec.id)])
                        if count:
                            att_ok = True
                if not att_ok:
                    missing.append('Quotation Attachment')

                # Additional check for Proposal Submitted with Freight Forwarding
                if 'proposal' in stage_name and 'submitted' in stage_name:
                    if rec.scope_of_service == 'freight_forwarding':
                        if not rec.freight_type:
                            missing.append('Freight Type')
                        if not rec.origin_country_id:
                            missing.append('Origin Country')
                        if not rec.destination_country_id:
                            missing.append('Destination Country')
                        if not rec.port_of_loading_id:
                            missing.append('Port of Loading')
                        if not rec.port_of_destination_id:
                            missing.append('Port of Destination')
                        if not rec.product:
                            missing.append('Customer Product')

                if missing:
                    # revert to a qualify stage (if possible) and show a warning
                    qualify_stage = self._find_qualify_stage(team_id=(rec.team_id.id if getattr(rec, 'team_id', False) else False))
                    if qualify_stage:
                        rec.stage_id = qualify_stage
                    return {
                        'warning': {
                            'title': 'Missing required information',
                            'message': 'You must fill the following fields before moving to Proposal: %s.\nThe stage has been reverted to Qualify.' % (', '.join(missing))
                        }
                    }

    @api.model_create_multi
    def create(self, vals_list):
        # Validate on create: if user tries to create a record in a Proposal stage, prevent it unless required fields are set
        for vals in vals_list:
            stage_id = vals.get('stage_id')
            if stage_id:
                stage = self.env['crm.stage'].browse(stage_id)
                name = (getattr(stage, 'name', '') or '').strip().lower()
                if 'proposal' in name:
                    missing = []
                    if vals.get('operating_profit_margin') in (None, False):
                        missing.append('Operating Profit Margin')
                    if not vals.get('expected_revenue_annum'):
                        missing.append('Expected Revenue (Annum)')
                    # check attachment either in vals or existing attachments (none on create)
                    if not vals.get('quotation_attachment') and not vals.get('attachment_file'):
                        missing.append('Quotation Attachment')

                    # Additional check for Proposal Submitted with Freight Forwarding
                    if 'proposal' in name and 'submitted' in name:
                        if vals.get('scope_of_service') == 'freight_forwarding':
                            if not vals.get('freight_type'):
                                missing.append('Freight Type')
                            if not vals.get('origin_country_id'):
                                missing.append('Origin Country')
                            if not vals.get('destination_country_id'):
                                missing.append('Destination Country')
                            if not vals.get('port_of_loading_id'):
                                missing.append('Port of Loading')
                            if not vals.get('port_of_destination_id'):
                                missing.append('Port of Destination')
                            if not vals.get('product'):
                                missing.append('Customer Product')

                    if missing:
                        raise ValidationError('Cannot create lead in Proposal stage: missing %s. Please fill them while in Qualify stage.' % (', '.join(missing)))
        return super(CrmLead, self).create(vals_list)

    def write(self, vals):
        # Skip proposal check if context flag is set (used by wizard)
        skip_check = self.env.context.get('skip_proposal_check', False)

        # Check if record is in Contract or Loss stage and prevent editing (except stage_id changes)
        for rec in self:
            if rec.is_readonly_stage:
                # Allow stage changes but prevent other field modifications
                non_stage_keys = [k for k in vals.keys() if k != 'stage_id']
                if non_stage_keys:
                    raise ValidationError('Cannot edit leads in Contract or Loss stage. The data is locked.')

        # For each record, check if user is attempting to move it to a Proposal stage without required fields
        if not skip_check:
            for rec in self:
                # determine effective stage after write
                new_stage_id = vals.get('stage_id', False)
                effective_stage = new_stage_id if new_stage_id else rec.stage_id.id
                if effective_stage:
                    stage = self.env['crm.stage'].browse(effective_stage)
                    name = (getattr(stage, 'name', '') or '').strip().lower()
                    if 'proposal' in name:
                        missing = []
                        # Check operating_profit_margin: if it's being changed in vals, consider that; otherwise use rec
                        opm = vals.get('operating_profit_margin') if 'operating_profit_margin' in vals else rec.operating_profit_margin
                        if opm in (None, False):
                            missing.append('Operating Profit Margin')
                        # expected_revenue_annum
                        exp_rev = vals.get('expected_revenue_annum') if 'expected_revenue_annum' in vals else rec.expected_revenue_annum
                        if not exp_rev:
                            missing.append('Expected Revenue (Annum)')
                        # quotation attachment: check vals, existing dedicated field, or ir.attachment
                        att_ok = False
                        if 'quotation_attachment' in vals and vals.get('quotation_attachment'):
                            att_ok = True
                        elif 'attachment_file' in vals and vals.get('attachment_file'):
                            # allow existing attachment_file too
                            att_ok = True
                        elif rec.quotation_attachment:
                            att_ok = True
                        else:
                            Attachment = self.env['ir.attachment']
                            if rec.id and Attachment.search_count([('res_model', '=', 'crm.lead'), ('res_id', '=', rec.id)]):
                                att_ok = True
                        if not att_ok:
                            missing.append('Quotation Attachment')

                        # Additional check for Proposal Submitted with Freight Forwarding
                        if 'proposal' in name and 'submitted' in name:
                            # Check scope of service (from vals or existing record)
                            scope = vals.get('scope_of_service') if 'scope_of_service' in vals else rec.scope_of_service
                            if scope == 'freight_forwarding':
                                # Check freight_type
                                freight = vals.get('freight_type') if 'freight_type' in vals else rec.freight_type
                                if not freight:
                                    missing.append('Freight Type')
                                # Check origin_country_id
                                origin = vals.get('origin_country_id') if 'origin_country_id' in vals else rec.origin_country_id
                                if not origin:
                                    missing.append('Origin Country')
                                # Check destination_country_id
                                dest = vals.get('destination_country_id') if 'destination_country_id' in vals else rec.destination_country_id
                                if not dest:
                                    missing.append('Destination Country')
                                # Check port_of_loading_id
                                pol = vals.get('port_of_loading_id') if 'port_of_loading_id' in vals else rec.port_of_loading_id
                                if not pol:
                                    missing.append('Port of Loading')
                                # Check port_of_destination_id
                                pod = vals.get('port_of_destination_id') if 'port_of_destination_id' in vals else rec.port_of_destination_id
                                if not pod:
                                    missing.append('Port of Destination')
                                # Check product
                                prod = vals.get('product') if 'product' in vals else rec.product
                                if not prod:
                                    missing.append('Customer Product')

                        if missing:
                            # Revert to qualify stage first
                            qualify_stage = rec._find_qualify_stage(team_id=(rec.team_id.id if rec.team_id else False))
                            if qualify_stage:
                                # Temporarily bypass check to revert stage
                                super(CrmLead, rec.with_context(skip_proposal_check=True)).write({'stage_id': qualify_stage.id})

                            # Show wizard with input fields
                            wizard = self.env['proposal.required.fields.wizard'].create({
                                'lead_id': rec.id,
                                'target_stage_id': effective_stage,
                                'message': 'You must fill the following fields before moving to Proposal: %s.\nThe stage has been reverted to Qualify.' % (', '.join(missing)),
                                'operating_profit_margin': rec.operating_profit_margin,
                                'expected_revenue_annum': rec.expected_revenue_annum,
                                'currency_id': rec.company_currency_id.id,
                                'freight_type': rec.freight_type,
                                'origin_country_id': rec.origin_country_id.id if rec.origin_country_id else False,
                                'destination_country_id': rec.destination_country_id.id if rec.destination_country_id else False,
                                'port_of_loading_id': rec.port_of_loading_id.id if rec.port_of_loading_id else False,
                                'port_of_destination_id': rec.port_of_destination_id.id if rec.port_of_destination_id else False,
                                'product': rec.product,
                            })

                            return {
                                'type': 'ir.actions.act_window',
                                'name': 'Missing Required Information',
                                'res_model': 'proposal.required.fields.wizard',
                                'view_mode': 'form',
                                'res_id': wizard.id,
                                'views': [(self.env.ref('PLB_input.view_proposal_required_fields_wizard_form').id, 'form')],
                                'target': 'new',
                                'context': self.env.context,
                            }

                # Existing checks for date_secured and attachment_file constraints
                # If date_secured included in vals, ensure effective stage is contract
                if 'date_secured' in vals:
                    if not self._stage_is_contract(effective_stage):
                        raise ValidationError('Date Secured can only be set when the lead stage is Shortlisted or Verbal.')
                if 'attachment_file' in vals:
                    if vals.get('attachment_file') and not self._stage_is_contract(effective_stage):
                        raise ValidationError('Attachment can only be added when the lead stage is Shortlisted or Verbal.')

        return super(CrmLead, self).write(vals)

    # New action to move leads to a Decline stage
    def action_decline(self):
        """Move selected leads to the 'Decline' stage.

        For each lead we try to find a crm.stage whose name contains 'decline' (case-insensitive).
        We prefer a stage belonging to the lead's team/section when available, otherwise any matching stage.
        Raises a UserError when no matching stage is found.
        """
        # Security: only allow administrators (Settings) to run this action
        if not self.env.user.has_group('base.group_system'):
            raise AccessError('Only users with Administrator (Settings) access may mark a lead as Decline.')
        Stage = self.env['crm.stage']
        for rec in self:
            # Prefer team/section-specific stage if available
            team_id = False
            if hasattr(rec, 'team_id') and rec.team_id:
                team_id = rec.team_id.id
            elif hasattr(rec, 'section_id') and rec.section_id:
                team_id = rec.section_id.id

            stage = False
            if team_id:
                stage = Stage.search([('name', 'ilike', 'decline'), ('team_id', 'in', (team_id, False))], limit=1)
            if not stage:
                stage = Stage.search([('name', 'ilike', 'decline')], limit=1)
            # Try plural/alternative spelling
            if not stage:
                stage = Stage.search([('name', 'ilike', 'declined')], limit=1)

            if not stage:
                raise UserError("Couldn't find a CRM stage named 'Decline' (or similar). Please create one before using the Decline action.")

            # Move the lead to the decline stage
            rec.write({'stage_id': stage.id})
        # If single record, reopen its form so the client refreshes that record and modifiers re-evaluate.
        if len(self) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'crm.lead',
                'view_mode': 'form',
                'res_id': self.id,
                'views': [(False, 'form')],
                'target': 'current',
            }
        # For multiple records, return a client reload so the UI refreshes generally
        return {'type': 'ir.actions.client', 'tag': 'reload'}


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
