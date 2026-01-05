from odoo import http
from odoo.http import request


class PLBKPIController(http.Controller):

    @http.route('/plb/sales_team_summary', type='json', auth='user')
    def get_sales_team_summary(self, year=None):
        """
        Fetch sales team summary data showing:
        - Location (Sales Team)
        - Commercial Lead (Team members)
        - YTD, Target, To Target, YTD vs Target
        - Pipeline stages (Qualify, Proposal Submitted, Shortlisted, Verbal)
        - Total Pipeline
        """
        from datetime import datetime
        Lead = request.env['crm.lead'].sudo()
        CrmTeam = request.env['crm.team'].sudo()
        Stage = request.env['crm.stage'].sudo()
        TargetKPISettings = request.env['target.kpi.settings'].sudo()

        try:
            if year:
                y = int(year)
            else:
                y = datetime.now().year
        except Exception:
            y = datetime.now().year

        # Get all sales teams
        all_teams = CrmTeam.search([])

        # Get target settings for the year
        settings = TargetKPISettings.search([('year', '=', y)], limit=1)
        employee_targets = {}
        if settings:
            for line in settings.employee_target_ids:
                if line.employee_id and line.employee_id.user_id:
                    user_id = line.employee_id.user_id.id
                    employee_targets[user_id] = line.personal_target or 0

        # Get contract stage IDs for YTD calculation
        contract_stages = Stage.search([('name', 'ilike', 'contract')])
        contract_stage_ids = [s.id for s in contract_stages]

        # Get pipeline stage IDs
        qualify_stages = Stage.search([('name', 'ilike', 'qualify')])
        proposal_stages = Stage.search([('name', 'ilike', 'proposal')])
        shortlisted_stages = Stage.search([('name', 'ilike', 'shortlisted')])
        verbal_stages = Stage.search([('name', 'ilike', 'verbal')])

        qualify_stage_ids = [s.id for s in qualify_stages]
        proposal_stage_ids = [s.id for s in proposal_stages]
        shortlisted_stage_ids = [s.id for s in shortlisted_stages]
        verbal_stage_ids = [s.id for s in verbal_stages]

        # First, build salesperson KPI data to get YTD calculations
        # Get Central Region team for salesperson KPI calculation
        central_team = CrmTeam.search([('name', '=', 'Central Region')], limit=1)
        central_team_member_ids = []

        if central_team:
            central_team_member_ids = central_team.member_ids.ids if central_team.member_ids else []

        # Build salesperson map with YTD calculations (same logic as /plb/kpi_data)
        salesperson_ytd_map = {}

        if central_team and central_team_member_ids:
            for member_user_id in central_team_member_ids:
                user = request.env['res.users'].sudo().browse(member_user_id)
                if not user or not user.exists():
                    continue

                monthly_target_value = employee_targets.get(member_user_id, 0.0) / 12.0

                salesperson_ytd_map[member_user_id] = {
                    'monthly_ytd': [0.0] * 12,
                    'monthly_target': [monthly_target_value] * 12,
                }

        # Fetch contract leads for Central Region to calculate YTD
        # Contract leads are filtered by date_secured (when contract was secured)
        if central_team and contract_stage_ids:
            contract_leads = Lead.search([
                ('team_id', '=', central_team.id),
                ('stage_id', 'in', contract_stage_ids),
            ])

            for lead in contract_leads:
                user_id = None
                if lead.user_id:
                    user_id = lead.user_id.id

                if not user_id or user_id not in salesperson_ytd_map:
                    continue

                sales = lead.expected_revenue or 0
                contract_months = lead.contract_months or 0
                expected_start = lead.expected_start_date
                date_secured = lead.date_secured

                # Only count leads that have date_secured (contract secured date) in the selected year
                # This is consistent with dashboard logic
                if not date_secured:
                    continue

                secured_year = date_secured.year
                if secured_year != y:
                    continue

                # Also check if expected_start_date is in the same year for YTD calculation
                if not expected_start:
                    continue

                start_year = expected_start.year
                start_month = expected_start.month

                # YTD calculation based on expected_start_date within the year
                if start_year != y:
                    continue

                mar = 0.0
                if contract_months and contract_months > 0:
                    mar = float(sales) / float(contract_months)

                if start_month and 1 <= start_month <= 12:
                    for month_idx in range(12):
                        actual_month = month_idx + 1
                        if actual_month >= start_month:
                            months_from_start = actual_month - start_month
                            if months_from_start < contract_months:
                                salesperson_ytd_map[user_id]['monthly_ytd'][month_idx] += mar

        # Now build team summary using the calculated YTD data
        team_summary = []

        for team in all_teams:
            team_member_ids = team.member_ids.ids if team.member_ids else []

            if not team_member_ids:
                continue

            # Process each team member individually
            for member in team.member_ids:
                if not member or not member.id:
                    continue

                member_user_id = member.id
                member_name = member.name or 'Unknown'

                # Get individual yearly target for this member (from employee_targets)
                member_yearly_target = employee_targets.get(member_user_id, 0)

                # Get YTD from salesperson_ytd_map (sum of monthly YTD)
                ytd = 0.0
                if member_user_id in salesperson_ytd_map:
                    ytd = sum(salesperson_ytd_map[member_user_id]['monthly_ytd'])

                # Calculate pipeline stages for this specific member
                # Filter by expected_start_date year (consistent with dashboard logic)
                qualify_revenue = sum(Lead.search([
                    ('team_id', '=', team.id),
                    ('user_id', '=', member_user_id),
                    ('stage_id', 'in', qualify_stage_ids),
                    ('expected_start_date', '>=', f'{y}-01-01'),
                    ('expected_start_date', '<=', f'{y}-12-31'),
                ]).mapped('expected_revenue'))

                proposal_revenue = sum(Lead.search([
                    ('team_id', '=', team.id),
                    ('user_id', '=', member_user_id),
                    ('stage_id', 'in', proposal_stage_ids),
                    ('expected_start_date', '>=', f'{y}-01-01'),
                    ('expected_start_date', '<=', f'{y}-12-31'),
                ]).mapped('expected_revenue'))

                shortlisted_revenue = sum(Lead.search([
                    ('team_id', '=', team.id),
                    ('user_id', '=', member_user_id),
                    ('stage_id', 'in', shortlisted_stage_ids),
                    ('expected_start_date', '>=', f'{y}-01-01'),
                    ('expected_start_date', '<=', f'{y}-12-31'),
                ]).mapped('expected_revenue'))

                verbal_revenue = sum(Lead.search([
                    ('team_id', '=', team.id),
                    ('user_id', '=', member_user_id),
                    ('stage_id', 'in', verbal_stage_ids),
                    ('expected_start_date', '>=', f'{y}-01-01'),
                    ('expected_start_date', '<=', f'{y}-12-31'),
                ]).mapped('expected_revenue'))

                total_pipeline = qualify_revenue + proposal_revenue + shortlisted_revenue + verbal_revenue

                # Calculate To Target and YTD vs Target
                to_target = member_yearly_target - ytd
                ytd_vs_target = (ytd / member_yearly_target * 100) if member_yearly_target > 0 else 0

                team_summary.append({
                    'location': team.name,
                    'commercial_lead': member_name,
                    'ytd': ytd,
                    'target': member_yearly_target,
                    'to_target': to_target,
                    'ytd_vs_target': ytd_vs_target,
                    'qualify': qualify_revenue,
                    'proposal': proposal_revenue,
                    'shortlisted': shortlisted_revenue,
                    'verbal': verbal_revenue,
                    'total_pipeline': total_pipeline,
                })

        return {
            'year': y,
            'team_summary': team_summary,
        }

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

        # Get all salespersons from Central Region team
        # We will show ALL Central Region members, but only calculate YTD from contract stage leads
        Stage = request.env['crm.stage'].sudo()
        CrmTeam = request.env['crm.team'].sudo()

        contract_stages = Stage.search([('name', 'ilike', 'contract')])
        contract_stage_ids = [s.id for s in contract_stages]

        # Get Central Region team
        central_team = CrmTeam.search([('name', '=', 'Central Region')], limit=1)
        central_team_member_ids = []

        if central_team:
            # Get all user IDs who are members of Central Region team
            central_team_member_ids = central_team.member_ids.ids if central_team.member_ids else []

        # Build salesperson map ONLY from Central Region team members
        # Initialize ALL team members first with 0 values
        salesperson_map = {}

        if central_team and central_team_member_ids:
            for member_user_id in central_team_member_ids:
                # Get user name
                user = User.browse(member_user_id)
                if not user or not user.exists():
                    continue

                salesperson_name = user.name if user else 'Unknown'
                monthly_target_value = employee_targets.get(member_user_id, 0.0)

                salesperson_map[member_user_id] = {
                    'id': member_user_id,
                    'name': salesperson_name,
                    'monthly_ytd': [0.0] * 12,
                    'monthly_target': [monthly_target_value] * 12,
                    'realized_revenue': 0.0,
                    'expected_revenue_total': 0.0,
                }

        # Now fetch leads from Central Region team (contract stage only) to calculate YTD
        # Build domain to filter by Central Region team AND contract stage
        domain = []
        if central_team and contract_stage_ids:
            domain.append(('team_id', '=', central_team.id))
            domain.append(('stage_id', 'in', contract_stage_ids))
        else:
            # If team not found, return empty results
            domain = [('id', '=', False)]

        leads = Lead.search_read(
            domain=domain,
            fields=['user_id', 'expected_revenue', 'expected_start_date', 'contract_months', 'realized_revenue', 'stage_id', 'team_id', 'date_secured']
        )

        # Process leads to calculate YTD for team members
        for lead in leads:
            # Extract salesperson (user_id)
            user_id = None
            if lead.get('user_id'):
                if isinstance(lead['user_id'], (list, tuple)):
                    user_id = lead['user_id'][0] if len(lead['user_id']) > 0 else None
                elif isinstance(lead['user_id'], dict):
                    user_id = lead['user_id'].get('id')

            if not user_id:
                continue

            # Only process if this user is a team member
            if user_id not in salesperson_map:
                continue

            # Calculate YTD (Year-to-Date) and Realized Revenue
            # YTD uses expected_revenue (projected/potential revenue)
            sales = lead.get('expected_revenue', 0) or 0
            contract_months = lead.get('contract_months', 0) or 0
            expected_start = lead.get('expected_start_date')
            date_secured = lead.get('date_secured')
            # Realized uses realized_revenue (actual received revenue for current year)
            realized_rev = lead.get('realized_revenue', 0) or 0

            # Filter by date_secured (when contract was secured) - must be in selected year
            # This is consistent with dashboard logic
            if date_secured:
                secured_year = None
                if isinstance(date_secured, str):
                    try:
                        parts = date_secured.split('-')
                        secured_year = int(parts[0])
                    except Exception:
                        pass
                else:
                    try:
                        secured_year = date_secured.year
                    except Exception:
                        pass

                # Skip if date_secured is not in the selected year
                if secured_year != y:
                    continue

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

        # Convert to list and sort by name (salesperson_map now contains ONLY Central Region team members)
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

