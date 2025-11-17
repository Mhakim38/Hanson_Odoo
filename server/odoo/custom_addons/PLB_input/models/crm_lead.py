from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Do not override the standard activity_ids relation here. The mail.activity
    # model uses a generic res_model/res_id link; overriding activity_ids with
    # an incorrect inverse would break behavior. We rely on the built-in
    # activities mechanism provided by mail.activity and mail.thread.

    # 1. Contract details
    contract_type = fields.Selection(
        [('long_term', 'Long Term'), ('adhoc', 'Adhoc')],
        string='Contract Period / Frequency',
        default='long_term'
    )
    contract_months = fields.Integer(
        string='Contract Months',
        compute='_compute_contract_months',
        inverse='_inverse_contract_months',
        store=True
    )

    expected_start_date = fields.Date(string='Expected Start Date')
    date_go_live = fields.Date(string='Date Go Live')

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

    # ✅ Replace selection with relations to crm.port
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

    product = fields.Selection(
        [
            ('customer_product', "Customer's Product"),
            ('industry', 'Industry'),
        ],
        string='Product',
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

    category_type = fields.Selection([
        ('1', 'Organic Growth of Current Customer'),
        ('2', 'Cross Selling'),
        ('3', 'Opportunity Sales / New Customers'),
        ('4', 'Al Bukhary New Business'),
    ], string='Category')

    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Currency',
        readonly=True
    )

    # === COMPUTE METHODS ===
    @api.depends('contract_type')
    def _compute_contract_months(self):
        for rec in self:
            if rec.contract_type == 'long_term':
                rec.contract_months = 12
            elif not rec.contract_months:
                rec.contract_months = 1

    def _inverse_contract_months(self):
        for rec in self:
            if rec.contract_type == 'long_term':
                rec.contract_months = 12
