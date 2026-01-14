from odoo import api, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # =========================
    # STAGE HELPERS
    # =========================

    is_new_stage = fields.Boolean(compute='_compute_is_new_stage', store=False)
    is_renewal_stage = fields.Boolean(compute='_compute_is_renewal_stage', store=True)
    is_decline_stage = fields.Boolean(compute='_compute_is_decline_stage', store=True)

    @api.depends('stage_id')
    def _compute_is_new_stage(self):
        for rec in self:
            name = (rec.stage_id.name or '').strip().lower()
            rec.is_new_stage = name == 'new'

    @api.depends('stage_id')
    def _compute_is_renewal_stage(self):
        for rec in self:
            name = (rec.stage_id.name or '').lower()
            rec.is_renewal_stage = 'renewal' in name

    @api.depends('stage_id')
    def _compute_is_decline_stage(self):
        for rec in self:
            name = (rec.stage_id.name or '').lower()
            rec.is_decline_stage = name in ('decline', 'declined')

    # =========================
    # PRIORITY (CHANCE)
    # =========================

    priority = fields.Selection(
        [
            ('0', 'Nil'),
            ('1', 'Low'),
            ('2', 'Medium'),
            ('3', 'High'),
        ],
        string='Chance', default='0'
    )

    # =========================
    # BUTTON ACTIONS
    # =========================

    def action_next_stage(self):
        for rec in self:
            if not rec.stage_id:
                raise UserError("Lead has no stage.")

            code = rec._normalize_stage_code(
                rec.stage_id.code or rec.stage_id.name
            )

            if code == 'new':
                rec._validate_qualify_fields()
                rec._move_to_stage('qualify')

            elif code == 'qualify':
                rec._validate_proposal_fields()
                rec._move_to_stage('proposal')

            elif code in ('proposal', 'proposal_submitted'):
                rec._move_to_stage('shortlisted')

            elif code == 'shortlisted':
                rec._move_to_stage('verbal')

            elif code == 'verbal':
                rec._validate_contract_fields()
                rec._move_to_stage('contract')

            elif code in ('contract', 'loss'):
                raise UserError(
                    "Cannot move leads out of Contract or Loss stage.\n"
                    "Once a lead is in Contract or Loss stage, it cannot be moved to another stage.\n"
                    "The data is locked."
                )

            else:
                raise UserError(
                    f"Next Stage is not allowed at stage '{rec.stage_id.name}'."
                )

    def action_to_shortlisted(self):
        self._validate_shortlisted_fields()
        self._ensure_at_stage('proposal')
        self._move_to_stage('shortlisted')

    def action_to_verbal(self):
        self._validate_verbal_fields()
        self._ensure_at_stage('proposal', 'shortlisted')
        self._move_to_stage('verbal')

    def action_to_contract(self):
        self._validate_contract_fields()
        self._ensure_at_stage('proposal', 'shortlisted', 'verbal')
        self._move_to_stage('contract')

    def action_to_loss(self):
        self._move_to_stage('loss')

    # def action_to_renewal(self):
    #     self._validate_renewal_fields()
    #     self._move_to_stage('renewal')
    #
    # def action_to_decline(self):
    #     self._validate_decline_fields()
    #     self._move_to_stage('decline')

    def action_to_renewal(self):
        raise UserError(
            "Renewal is not allowed from Contract stage.\n"
            "Please create a new lead for renewal."
        )

    def action_to_decline(self):
        raise UserError(
            "Decline is not allowed from Contract stage.\n"
            "Please use Loss stage directly."
        )

    # =========================
    # INTERNAL HELPERS
    # =========================

    def _normalize_stage_code(self, value):
        return (value or '').strip().lower().replace(' ', '_')

    def _ensure_at_stage(self, *allowed_codes):
        current = self._normalize_stage_code(
            self.stage_id.code or self.stage_id.name
        )
        if current not in allowed_codes:
            raise UserError(
                f"This action is only allowed from stage(s): "
                f"{', '.join(allowed_codes)}"
            )

    def _move_to_stage(self, code):
        code = self._normalize_stage_code(code)

        stage = self.env['crm.stage'].search([
            '|',
            ('code', '=', code),
            ('name', 'ilike', code.replace('_', ' ')),
            ('team_id', 'in', [self.team_id.id, False])
        ], limit=1)

        if not stage:
            raise UserError(
                f"Stage '{code}' not found. "
                "Please ensure Stage Code or Stage Name is configured."
            )

        self.write({'stage_id': stage.id})

    # =========================
    # MANDATORY VALIDATIONS
    # =========================

    def _validate_new_fields(self):
        missing = []

        if not self.partner_id:
            missing.append("Customer")
        if not self.name:
            missing.append("Initiative/Project Description")

        if missing:
            raise UserError(
                "Please fill mandatory fields before moving to New/Save:\n- " +
                "\n- ".join(missing)
            )

    def _validate_qualify_fields(self):
        missing = []

        if not self.name:
            missing.append("Initiative/Project Description")
        if not self.priority:
            missing.append("Chance")
        if not self.partner_id:
            missing.append("Customer")
        if not self.expected_start_date:
            missing.append("Expected Date Start")
        if not self.scope_of_service:
            missing.append("Scope of Service")
        if not self.product:
            missing.append("Customer Product")
        if not self.dept_region:
            missing.append("Dept/Region")

        if missing:
            raise UserError(
                "Please fill mandatory fields before moving to Qualify:\n- " +
                "\n- ".join(missing)
            )

    def _validate_proposal_fields(self):
        missing = []

        if not (self.expected_revenue):
            missing.append("Value Per Annum")
        if not (self.contract_type):
            missing.append("Contract Period / Frequency")
        if not (self.contract_months):
            missing.append("Number of Months")
        if not (self.origin_country_id):
            missing.append("Origin Country")
        if not (self.destination_country_id):
            missing.append("Destination Country")
        if not (self.port_of_loading_id):
            missing.append("Port of Loading")
        if not (self.port_of_destination_id):
            missing.append("Port of Destination")
        if not (self.remark):
            missing.append("Remarks/Contract Period/Adhoc")
        if not (self.operating_profit_margin):
            missing.append("Operating Profit Margin (%)")
        if not (self.quotation_attachment):
            missing.append("Quotation Attachment")

        if missing:
            raise UserError(
                "Please fill mandatory fields before moving to Proposal Submitted:\n- " +
                "\n- ".join(missing)
            )

    def _validate_shortlisted_fields(self):
        pass

    def _validate_verbal_fields(self):
        pass

    def _validate_contract_fields(self):
        missing = []

        if not (self.date_secured):
            missing.append("Date Secured")
        if not (self.date_go_live):
            missing.append("Date Go Live")
        if not (self.attachment_file):
            missing.append("Contract Attachment")
        if not (self.realized_revenue):
            missing.append("Forecast Revenue for Current Year")
        if not (self.remark):
            missing.append("Remarks/Contract Period/Adhoc")

        if missing:
            raise UserError(
                "Please fill mandatory fields before moving to Contract:\n- " +
                "\n- ".join(missing)
            )

    def _validate_renewal_fields(self):
        missing = []

        if not (self.date_secured):
            missing.append("Date Secured")
        if not (self.date_go_live):
            missing.append("Date Go Live")

        if missing:
            raise UserError(
                "Please fill mandatory fields before moving to Renewal:\n- " +
                "\n- ".join(missing)
            )

    def _validate_decline_fields(self):
        missing = []

        if not (self.date_secured):
            missing.append("Date Secured")

        if missing:
            raise UserError(
                "Please fill mandatory fields before moving to Decline:\n- " +
                "\n- ".join(missing)
            )


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    code = fields.Char(
        string="Stage Code",
        index=True,
        help="Internal stage identifier e.g. new, qualify, proposal, contract"
    )

    @api.constrains('code')
    def _check_stage_code(self):
        for rec in self:
            if rec.code and ' ' in rec.code:
                raise UserError("Stage Code cannot contain spaces.")
