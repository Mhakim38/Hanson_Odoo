from odoo import http
from odoo.http import request


class PLBKPIController(http.Controller):

    @http.route('/plb/kpi_data', type='json', auth='user')
    def get_kpi_data(self, year=None):
        """
        Fetch KPI data for all salespersons showing Target and YTD by month.
        Returns structured data with salesperson rows containing target and YTD values for each month.
        """
        from datetime import datetime
        Lead = request.env['crm.lead'].sudo()
        User = request.env['res.users'].sudo()
        HrEmployee = request.env['hr.employee'].sudo()
        EmployeeTargetLine = request.env['employee.target.line'].sudo()
        TargetKPISettings = request.env['target.kpi.settings'].sudo()

        try:
            if year:
                y = int(year)
            else:
                y = datetime.now().year
        except Exception:
            y = datetime.now().year

        # Get company yearly target and employee targets for the specific year
        company_yearly_target = 0
        employee_targets = {}

        settings = TargetKPISettings.search([('year', '=', y)], limit=1)
        if settings:
            company_yearly_target = settings.yearly_target or 0
            # Get employee targets for this year
            for line in settings.employee_target_ids:
                if line.employee_id and line.employee_id.user_id:
                    user_id = line.employee_id.user_id.id
                    # Divide yearly target by 12 for monthly target
                    monthly_target = (line.personal_target or 0) / 12.0
                    employee_targets[user_id] = monthly_target
        else:
            # If no settings for this year, create with auto-populated employees
            settings = request.env['target.kpi.settings'].get_settings_for_year(y)
            company_yearly_target = settings.yearly_target or 0
            # Get employee targets for newly created year
            for line in settings.employee_target_ids:
                if line.employee_id and line.employee_id.user_id:
                    user_id = line.employee_id.user_id.id
                    monthly_target = (line.personal_target or 0) / 12.0
                    employee_targets[user_id] = monthly_target

        # Get all salespersons (users who have leads in contract stage)
        # Filter leads where stage name contains 'contract' (case-insensitive)
        Stage = request.env['crm.stage'].sudo()
        contract_stages = Stage.search([('name', 'ilike', 'contract')])
        contract_stage_ids = [s.id for s in contract_stages]

        leads = Lead.search_read(
            domain=[('stage_id', 'in', contract_stage_ids)] if contract_stage_ids else [('id', '=', False)],
            fields=['user_id', 'expected_revenue', 'expected_start_date', 'contract_months', 'realized_revenue_fy2025', 'stage_id']
        )

        # Build salesperson map: {user_id: {name: ..., monthly_ytd: [0]*12, target: [0]*12}}
        salesperson_map = {}

        for lead in leads:
            # Extract salesperson (user_id)
            user_id = None
            salesperson_name = ''
            if lead.get('user_id'):
                if isinstance(lead['user_id'], (list, tuple)):
                    user_id = lead['user_id'][0] if len(lead['user_id']) > 0 else None
                    salesperson_name = lead['user_id'][1] if len(lead['user_id']) > 1 else ''
                elif isinstance(lead['user_id'], dict):
                    user_id = lead['user_id'].get('id')
                    salesperson_name = lead['user_id'].get('name', '')

            if not user_id:
                continue

            # Initialize salesperson if not exists
            if user_id not in salesperson_map:
                # Get monthly target from employee_targets (yearly target / 12)
                monthly_target_value = employee_targets.get(user_id, 0.0)
                salesperson_map[user_id] = {
                    'id': user_id,
                    'name': salesperson_name,
                    'monthly_ytd': [0.0] * 12,
                    'monthly_target': [monthly_target_value] * 12,  # Same target for all 12 months
                    'realized_revenue': 0.0,  # Track realized revenue separately
                    'expected_revenue_total': 0.0,  # Track total expected revenue (not annualized)
                }

            # Calculate YTD (Year-to-Date) and Realized Revenue
            # YTD uses expected_revenue (projected/potential revenue)
            sales = lead.get('expected_revenue', 0) or 0
            contract_months = lead.get('contract_months', 0) or 0
            expected_start = lead.get('expected_start_date')
            # Realized uses realized_revenue_fy2025 (actual received revenue for current year)
            realized_rev = lead.get('realized_revenue_fy2025', 0) or 0

            # Parse start date
            start_year = None
            start_month = None
            if expected_start:
                if isinstance(expected_start, str):
                    try:
                        parts = expected_start.split('-')
                        start_year = int(parts[0])
                        start_month = int(parts[1])
                    except Exception:
                        start_year = None
                        start_month = None
                else:
                    try:
                        start_year = expected_start.year
                        start_month = expected_start.month
                    except Exception:
                        start_year = None
                        start_month = None

            # Only process leads with expected_start_date in the specified year
            if start_year != y:
                continue

            # Accumulate expected revenue for YTD gauge (total expected revenue, not annualized)
            salesperson_map[user_id]['expected_revenue_total'] += sales

            # Accumulate realized revenue for this lead (actual revenue received in current year)
            salesperson_map[user_id]['realized_revenue'] += realized_rev

            # Calculate MAR (Monthly Annualized Revenue) for YTD projection (table display only)
            # Uses expected_revenue to project potential monthly revenue
            mar = 0.0
            if contract_months and contract_months > 0:
                try:
                    mar = float(sales) / float(contract_months)
                except Exception:
                    mar = 0.0

            # Add MAR to each month the contract is active within the year (for YTD calculation)
            if start_month and 1 <= start_month <= 12:
                for month_idx in range(12):
                    actual_month = month_idx + 1
                    # Check if this month is within the contract period
                    if actual_month >= start_month:
                        months_from_start = actual_month - start_month
                        if months_from_start < contract_months:
                            salesperson_map[user_id]['monthly_ytd'][month_idx] += mar

        # Add employees with targets but no leads yet
        for user_id, monthly_target_value in employee_targets.items():
            if user_id not in salesperson_map:
                # Get user name
                user = User.browse(user_id)
                salesperson_name = user.name if user else 'Unknown'
                salesperson_map[user_id] = {
                    'id': user_id,
                    'name': salesperson_name,
                    'monthly_ytd': [0.0] * 12,
                    'monthly_target': [monthly_target_value] * 12,
                    'realized_revenue': 0.0,
                    'expected_revenue_total': 0.0,
                }

        # Convert to list and sort by name
        salesperson_list = sorted(salesperson_map.values(), key=lambda x: x['name'])

        # Calculate monthly subtotals
        monthly_subtotals_ytd = [0.0] * 12
        monthly_subtotals_target = [0.0] * 12
        total_expected_revenue = 0.0  # Sum of expected_revenue (not annualized)

        for sp in salesperson_list:
            for i in range(12):
                monthly_subtotals_ytd[i] += sp['monthly_ytd'][i]
                monthly_subtotals_target[i] += sp['monthly_target'][i]
            total_expected_revenue += sp.get('expected_revenue_total', 0.0)

        # Calculate totals for gauge meters
        # YTD Revenue: Based on expected_revenue (DIRECT SUM, not annualized)
        total_ytd_revenue = total_expected_revenue  # Use direct sum of expected_revenue

        # Realized Revenue: Based on Monthly Subtotal (YTD) - sum of MAR calculations
        total_realized_revenue = sum(monthly_subtotals_ytd)  # Sum of all monthly YTD (MAR)

        total_target_revenue = sum(monthly_subtotals_target)  # Sum of individual targets (for table display)

        # Use company yearly target for gauge percentages (not individual sum)
        company_target_for_calculation = company_yearly_target if company_yearly_target > 0 else total_target_revenue

        # YTD Rev Target percentage: Uses EXPECTED_REVENUE (direct sum, not annualized)
        # Formula: Expected Revenue (sum of expected_revenue) / Company Yearly Target × 100
        ytd_percentage = (total_ytd_revenue / company_target_for_calculation * 100) if company_target_for_calculation > 0 else 0

        # Realized Rev Target percentage: Uses Monthly Subtotal (YTD) - sum of MAR
        # Formula: Sum of Monthly Subtotal YTD (MAR) / Company Yearly Target × 100
        realized_percentage = (total_realized_revenue / company_target_for_calculation * 100) if company_target_for_calculation > 0 else 0

        return {
            'year': y,
            'salespersons': salesperson_list,
            'monthly_subtotals_ytd': monthly_subtotals_ytd,
            'monthly_subtotals_target': monthly_subtotals_target,
            # Company target
            'company_yearly_target': company_yearly_target / 1000000,  # In millions
            # Gauge data (in millions)
            'total_ytd_revenue': total_ytd_revenue / 1000000,  # Expected Revenue (sum) in millions
            'total_realized_revenue': total_realized_revenue / 1000000,  # Realized revenue in millions
            'total_target_revenue': company_yearly_target / 1000000,  # Use company target for display
            'ytd_percentage': ytd_percentage,
            'realized_percentage': realized_percentage,
        }

