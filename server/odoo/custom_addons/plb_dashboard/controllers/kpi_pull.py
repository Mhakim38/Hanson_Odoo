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

        try:
            if year:
                y = int(year)
            else:
                y = datetime.now().year
        except Exception:
            y = datetime.now().year

        # Get all salespersons (users who have leads assigned)
        leads = Lead.search_read(
            domain=[],
            fields=['user_id', 'expected_revenue', 'expected_start_date', 'contract_months']
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
                salesperson_map[user_id] = {
                    'id': user_id,
                    'name': salesperson_name,
                    'monthly_ytd': [0.0] * 12,
                    'monthly_target': [0.0] * 12,  # Will be set based on business logic
                }

            # Calculate YTD (Year-to-Date realized revenue per month)
            sales = lead.get('expected_revenue', 0) or 0
            contract_months = lead.get('contract_months', 0) or 0
            expected_start = lead.get('expected_start_date')

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

            # Calculate MAR (Monthly Annualized Revenue)
            mar = 0.0
            if contract_months and contract_months > 0:
                try:
                    mar = float(sales) / float(contract_months)
                except Exception:
                    mar = 0.0

            # Add MAR to each month the contract is active within the year
            if start_month and 1 <= start_month <= 12:
                for month_idx in range(12):
                    actual_month = month_idx + 1
                    # Check if this month is within the contract period
                    if actual_month >= start_month:
                        months_from_start = actual_month - start_month
                        if months_from_start < contract_months:
                            salesperson_map[user_id]['monthly_ytd'][month_idx] += mar

        # Convert to list and sort by name
        salesperson_list = sorted(salesperson_map.values(), key=lambda x: x['name'])

        # Calculate monthly subtotals
        monthly_subtotals_ytd = [0.0] * 12
        monthly_subtotals_target = [0.0] * 12

        for sp in salesperson_list:
            for i in range(12):
                monthly_subtotals_ytd[i] += sp['monthly_ytd'][i]
                monthly_subtotals_target[i] += sp['monthly_target'][i]

        # Calculate totals for gauge meters
        total_ytd_revenue = sum(monthly_subtotals_ytd)
        total_target_revenue = sum(monthly_subtotals_target)

        # Calculate percentage for YTD (current month progress)
        current_month = datetime.now().month
        ytd_up_to_current = sum(monthly_subtotals_ytd[:current_month])
        target_up_to_current = sum(monthly_subtotals_target[:current_month])
        ytd_percentage = (ytd_up_to_current / target_up_to_current * 100) if target_up_to_current > 0 else 0

        # For realized revenue target, use full year comparison
        realized_percentage = (total_ytd_revenue / total_target_revenue * 100) if total_target_revenue > 0 else 0

        return {
            'year': y,
            'salespersons': salesperson_list,
            'monthly_subtotals_ytd': monthly_subtotals_ytd,
            'monthly_subtotals_target': monthly_subtotals_target,
            # Gauge data (in millions)
            'total_ytd_revenue': total_ytd_revenue / 1000000,  # Convert to millions
            'total_target_revenue': total_target_revenue / 1000000,  # Convert to millions
            'ytd_percentage': ytd_percentage,
            'realized_percentage': realized_percentage,
        }

