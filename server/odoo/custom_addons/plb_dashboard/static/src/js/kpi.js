/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PLBKPI extends Component {
    setup() {
        // reactive state
        this.state = useState({
            year: String((new Date()).getFullYear()),
            years: [],
            salespersons: [],
            team_summary: [],
            monthly_subtotals_ytd: Array(12).fill(0),
            monthly_subtotals_target: Array(12).fill(0),
            monthly_percentage: Array(12).fill(0),
            company_yearly_target: 0,
            annualized_ytd_gain: 0,
            current_year_realized: 0,
            target_completion: 0,
            loading: true,
        });

        // rpc service for fetching model data
        this.rpc = useService("rpc");

        // Fetch all KPI data on mount
        onMounted(async () => {
            this.computeYearOptions();
            await this.loadKPIData();
        });
    }

    // Build year options from 2000 to current year
    computeYearOptions() {
        const now = new Date();
        const currentYear = now.getFullYear();
        const years = [];
        for (let y = currentYear; y >= 2000; y--) {
            years.push(String(y));
        }
        this.state.years = years;
    }

    async loadKPIData() {
        try {
            this.state.loading = true;

            const year = this.state.year ? Number(this.state.year) : (new Date()).getFullYear();

            // Fetch both team summary and KPI data from controller endpoints
            const [teamSummaryData, kpiData] = await Promise.all([
                this.rpc("/plb/sales_team_summary", { year: year }),
                this.rpc("/plb/kpi_data", { year: year })
            ]);

            // Set team summary data
            if (teamSummaryData) {
                this.state.team_summary = teamSummaryData.team_summary || [];
            }

            // Set KPI data
            if (kpiData) {
                this.state.salespersons = kpiData.salespersons || [];
                this.state.monthly_subtotals_ytd = kpiData.monthly_subtotals_ytd || Array(12).fill(0);
                this.state.monthly_subtotals_target = kpiData.monthly_subtotals_target || Array(12).fill(0);
                this.state.company_yearly_target = kpiData.company_yearly_target || 0;
                this.state.annualized_ytd_gain = kpiData.annualized_ytd_gain || 0;
                this.state.current_year_realized = kpiData.current_year_realized || 0;
                this.state.target_completion = kpiData.target_completion || 0;

                // Calculate monthly percentage (YTD / Target * 100)
                this.state.monthly_percentage = Array(12).fill(0).map((_, idx) => {
                    const target = this.state.monthly_subtotals_target[idx];
                    const ytd = this.state.monthly_subtotals_ytd[idx];
                    if (target && target > 0) {
                        return (ytd / target) * 100;
                    }
                    return 0;
                });
            }

            console.debug('PLB KPI loaded:', {
                year: year,
                salespersons: this.state.salespersons.length,
                teams: this.state.team_summary.length,
            });

        } catch (err) {
            console.error('Failed to load PLB KPI data:', err);
        } finally {
            this.state.loading = false;
        }
    }

    // Set year filter and reload data
    setYear = async (evOrValue) => {
        const value = (evOrValue && evOrValue.target && evOrValue.target.value !== undefined) ? evOrValue.target.value : evOrValue;
        this.state.year = value;
        await this.loadKPIData();
    }

    // Helper: format a numeric value with 2 decimals
    formatNumber(value) {
        if (value === false || value === null || value === undefined || value === '') {
            return '0.00';
        }
        const n = Number(value);
        if (Number.isNaN(n)) {
            return '0.00';
        }
        return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // Helper: format currency
    formatCurrency(value) {
        return this.formatNumber(value);
    }

    static template = xml`
<style>
    /* KPI Dashboard Styling */
    .plb-kpi-container {
        padding: 24px;
        background: #F2F4F7;
        min-height: 100vh;
    }

    /* Unified KPI Header with Company Target */
    .plb-unified-header {
        background: linear-gradient(135deg, #0D47A1 0%, #1565C0 50%, #1976D2 100%);
        padding: 32px 40px;
        border-radius: 20px;
        margin-bottom: 32px;
        box-shadow: 0 8px 32px rgba(13, 71, 161, 0.4);
        position: relative;
        overflow: hidden;
    }

    .plb-unified-header-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 32px;
        flex-wrap: wrap;
        position: relative;
        z-index: 2;
    }

    .plb-header-left {
        display: flex;
        align-items: center;
        gap: 24px;
        flex: 1;
        min-width: 300px;
    }

    .plb-header-icon {
        background: rgba(255, 255, 255, 0.15);
        padding: 16px;
        border-radius: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        border: 2px solid rgba(255, 255, 255, 0.2);
    }

    .plb-header-titles {
        flex: 1;
    }

    .plb-header-main-title {
        font-size: 2rem;
        font-weight: 800;
        color: #FFFFFF;
        margin: 0 0 8px 0;
        letter-spacing: 0.5px;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }

    .plb-header-subtitle {
        font-size: 1rem;
        color: rgba(255, 255, 255, 0.9);
        margin: 0;
        font-weight: 400;
    }

    .plb-header-right {
        display: flex;
        align-items: center;
        gap: 24px;
        flex-wrap: wrap;
    }

    .plb-target-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 16px;
        flex: 1;
    }

    .plb-target-display {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        padding: 16px 24px;
        border-radius: 16px;
        border: 2px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        min-width: 200px;
    }

    .plb-target-label {
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.85);
        font-weight: 600;
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .plb-target-value {
        font-size: 1.75rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: 0.5px;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        line-height: 1.2;
    }

    .plb-year-selector-wrapper {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        padding: 12px 20px;
        border-radius: 16px;
        border: 2px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        display: flex;
        flex-direction: column;
        gap: 8px;
        min-width: 140px;
    }

    .plb-year-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.85);
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .plb-year-select {
        background: rgba(255, 255, 255, 0.95);
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 10px;
        padding: 10px 16px;
        font-size: 1.1rem;
        font-weight: 700;
        color: #0D47A1;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%230D47A1' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 12px center;
        padding-right: 36px;
    }

    .plb-year-select:hover {
        background-color: #FFFFFF;
        border-color: rgba(255, 255, 255, 0.5);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }

    .plb-year-select:focus {
        outline: none;
        border-color: #FFFFFF;
        box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.25);
    }

    /* Decorative elements */
    .plb-header-decoration {
        position: absolute;
        border-radius: 50%;
        opacity: 0.08;
        pointer-events: none;
    }

    .plb-header-decoration-1 {
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(255, 255, 255, 0.3) 0%, transparent 70%);
        top: -200px;
        right: -100px;
        z-index: 1;
    }

    .plb-header-decoration-2 {
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(255, 255, 255, 0.2) 0%, transparent 70%);
        bottom: -150px;
        left: -50px;
        z-index: 1;
    }

    /* Responsive design */
    @media (max-width: 1024px) {
        .plb-unified-header-content {
            flex-direction: column;
            align-items: flex-start;
        }

        .plb-header-right {
            width: 100%;
            justify-content: space-between;
        }

        .plb-target-grid {
            grid-template-columns: 1fr;
            width: 100%;
        }
    }

    @media (max-width: 768px) {
        .plb-unified-header {
            padding: 24px 20px;
        }

        .plb-header-main-title {
            font-size: 1.5rem;
        }

        .plb-header-left {
            flex-direction: column;
            align-items: flex-start;
        }

        .plb-header-right {
            flex-direction: column;
            width: 100%;
        }

        .plb-target-display,
        .plb-year-selector-wrapper {
            width: 100%;
        }

        .plb-target-grid {
            grid-template-columns: 1fr;
        }
    }

    .plb-kpi-card {
        background: #FFFFFF;
        border-radius: 16px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        overflow: hidden;
        border: 1px solid #D0D5DD;
    }

    .plb-kpi-card .card-header {
        background: linear-gradient(135deg, #0D47A1 0%, #1565C0 100%);
        padding: 20px 28px;
        border: none;
    }

    .plb-kpi-card .card-header h4 {
        margin: 0;
        color: #FFFFFF;
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: 0.3px;
    }

    /* Team Summary Table Styles */
    .plb-team-summary-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        background: #FFFFFF;
    }

    .plb-team-summary-table thead th {
        background: #f2f4f7;
        color: #1A1A1A;
        padding: 14px 10px;
        text-align: center;
        font-weight: 700;
        font-size: 12px;
        border: 1px solid #D0D5DD;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        vertical-align: middle;
    }

    .plb-team-summary-table tbody td {
        padding: 12px 10px;
        border: 1px solid #D0D5DD;
        text-align: center;
        color: #1A1A1A;
        vertical-align: middle;
    }

    .plb-team-summary-table tbody tr:hover {
        background-color: #F8F9FA;
    }

    .plb-team-summary-table tbody td.location-cell {
        text-align: left;
        font-weight: 600;
        color: #0D47A1;
    }

    .plb-team-summary-table tbody td.lead-cell {
        text-align: left;
        font-size: 12px;
        color: #4A4A4A;
    }

    .plb-team-summary-table tbody td.ytd-vs-target-cell {
        font-weight: 700;
    }

    .plb-team-summary-table tbody td.ytd-vs-target-cell.bg-success {
        background-color: #d4edda !important;
        color: #155724;
    }

    .plb-team-summary-table tbody td.ytd-vs-target-cell.bg-danger {
        background-color: #f8d7da !important;
        color: #721c24;
    }

    .plb-kpi-card {
        background: #FFFFFF;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
        overflow: hidden;
    }

    .plb-kpi-card .card-header {
        background: #C62828;
        border: none;
        padding: 16px 24px;
    }

    .plb-kpi-card .card-header h4 {
        font-weight: 600;
        letter-spacing: 0.5px;
        color: #FFFFFF;
        margin: 0;
        font-size: 1.25rem;
    }

    .plb-kpi-table-container {
        overflow-x: auto;
        max-height: calc(100vh - 300px);
    }

    .plb-kpi-table {
        margin-bottom: 0;
        border-radius: 0 0 8px 8px;
        width: 100%;
    }

    .plb-kpi-table thead th {
        background: #F2F4F7;
        font-weight: 700;
        color: #1A1A1A;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.5px;
        padding: 12px 8px;
        border: 1px solid #D0D5DD;
        position: sticky;
        top: 0;
        z-index: 10;
        text-align: center;
        vertical-align: middle;
        white-space: nowrap;
    }

    .plb-kpi-table tbody tr:hover {
        background-color: rgba(13, 71, 161, 0.05);
    }

    .plb-kpi-table tbody td {
        padding: 10px 8px;
        vertical-align: middle;
        font-size: 13px;
        color: #1A1A1A;
        border: 1px solid #D0D5DD;
        text-align: right;
    }

    .plb-kpi-table tbody td.salesperson-name {
        text-align: left;
        font-weight: 600;
        background: #F2F4F7;
    }

    .plb-kpi-table tbody td.matrix-label {
        text-align: center;
        font-weight: 500;
        background: #F2F4F7;
        color: #4A4A4A;
        font-size: 12px;
    }

    .plb-kpi-table tbody tr.target-row {
        background-color: rgba(13, 71, 161, 0.05);
    }

    .plb-kpi-table tbody tr.ytd-row {
        background-color: rgba(198, 40, 40, 0.05);
    }

    .plb-kpi-table tfoot tr {
        background: #F2F4F7;
        font-weight: 700;
    }

    .plb-kpi-table tfoot td {
        padding: 12px 8px;
        font-size: 13px;
        color: #1A1A1A;
        border: 1px solid #D0D5DD;
        text-align: right;
    }

    .plb-kpi-table tfoot td.footer-label {
        text-align: left;
        font-weight: 700;
        background: #0D47A1;
        color: #FFFFFF;
    }

    .plb-loading {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 100px 20px;
    }

    .plb-loading p {
        color: #6c757d;
        font-weight: 500;
        margin-top: 16px;
    }

    /* Metrics Summary Section */
    .plb-metrics-summary {
        margin-top: 32px;
        margin-bottom: 32px;
    }

    .plb-metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 24px;
    }

    .plb-metric-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        border: 1px solid #D0D5DD;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .plb-metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    }

    .plb-metric-card.primary {
        border-left: 4px solid #0D47A1;
    }

    .plb-metric-card.success {
        border-left: 4px solid #28a745;
    }

    .plb-metric-card.info {
        border-left: 4px solid #17a2b8;
    }

    .plb-metric-card.warning {
        border-left: 4px solid #C62828;
    }

    .plb-metric-label {
        font-size: 0.875rem;
        color: #4A4A4A;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 12px;
    }

    .plb-metric-value {
        font-size: 2rem;
        font-weight: 800;
        color: #1A1A1A;
        line-height: 1.2;
    }

    .plb-metric-value.highlight-blue {
        color: #0D47A1;
    }

    .plb-metric-value.highlight-green {
        color: #28a745;
    }

    .plb-metric-value.highlight-red {
        color: #C62828;
    }

    .plb-metric-subtitle {
        font-size: 0.75rem;
        color: #4A4A4A;
        margin-top: 8px;
        font-weight: 500;
    }

    @media (max-width: 768px) {
        .plb-metrics-grid {
            grid-template-columns: 1fr;
        }
    }

    /* Smooth transitions */
    * {
        transition: background-color 0.2s ease, border-color 0.2s ease;
    }
</style>

<div class="plb-kpi-container" style="overflow: auto; height: 100%;">
    <!-- Loading state -->
    <t t-if="state.loading">
        <div class="plb-loading">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p>Loading KPI data...</p>
        </div>
    </t>

    <t t-else="">
        <!-- Combined KPI Header with Company Target and Year Selector -->
        <div class="plb-unified-header">
            <div class="plb-unified-header-content">
                <div class="plb-header-left">
                    <div class="plb-header-icon">
                        <svg width="56" height="56" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="rgba(255,255,255,0.25)"/>
                            <path d="M2 17L12 22L22 17" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M2 12L12 17L22 12" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <div class="plb-header-titles">
                        <h1 class="plb-header-main-title">Individual Dashboard</h1>
                        <p class="plb-header-subtitle">Salesperson performance metrics and targets</p>
                    </div>
                </div>
                <div class="plb-header-right">
                    <div class="plb-year-selector-wrapper">
                        <label class="plb-year-label">Year</label>
                        <select class="plb-year-select" t-on-change="ev => this.setYear(ev.target.value)">
                            <t t-foreach="state.years" t-as="yr" t-key="yr">
                                <option t-att-value="yr" t-att-selected="yr === state.year ? 'selected' : undefined"><t t-esc="yr"/></option>
                            </t>
                        </select>
                    </div>
                </div>
            </div>
            <!-- Decorative elements -->
            <div class="plb-header-decoration plb-header-decoration-1"></div>
            <div class="plb-header-decoration plb-header-decoration-2"></div>
        </div>

        <!-- Metrics Summary Section -->
        <div class="plb-metrics-summary">
            <div class="plb-metrics-grid">
                <div class="plb-metric-card primary">
                    <div class="plb-metric-label">Company Yearly Target</div>
                    <div class="plb-metric-value highlight-blue">MYR <t t-esc="formatNumber(state.company_yearly_target)"/> M</div>
                    <div class="plb-metric-subtitle">Overall target for <t t-esc="state.year"/></div>
                </div>
                <div class="plb-metric-card success">
                    <div class="plb-metric-label">Annualized YTD Gain</div>
                    <div class="plb-metric-value highlight-green">MYR <t t-esc="formatNumber(state.annualized_ytd_gain)"/> M</div>
                    <div class="plb-metric-subtitle">Value Per Annum (contract stage)</div>
                </div>
                <div class="plb-metric-card info">
                    <div class="plb-metric-label"><t t-esc="state.year"/> Realized Target</div>
                    <div class="plb-metric-value">MYR <t t-esc="formatNumber(state.current_year_realized)"/> M</div>
                    <div class="plb-metric-subtitle">Forecast Revenue <t t-esc="state.year"/></div>
                </div>
                <div class="plb-metric-card warning">
                    <div class="plb-metric-label">Target Completion</div>
                    <div class="plb-metric-value highlight-red"><t t-esc="formatNumber(state.target_completion)"/>%</div>
                    <div class="plb-metric-subtitle">Annualized YTD / Target</div>
                </div>
            </div>
        </div>

        <!-- Sales Team Summary Table -->
        <div class="plb-kpi-card mb-4">
            <div class="card-header">
                <h4>Sales Team Summary - <t t-esc="state.year"/></h4>
            </div>
            <div class="card-body p-0">
                <div class="plb-kpi-table-container">
                    <table class="table table-bordered plb-team-summary-table">
                        <thead>
                            <tr>
                                <th>Location</th>
                                <th>Commercial Lead</th>
                                <th><t t-esc="state.year"/> YTD</th>
                                <th>To Target</th>
                                <th>Target</th>
                                <th>YTD vs Target</th>
                                <th>Qualify</th>
                                <th>Proposal Submitted</th>
                                <th>Shortlisted</th>
                                <th>Verbal</th>
                                <th>Total Pipeline</th>
                            </tr>
                        </thead>
                        <tbody>
                            <t t-if="state.team_summary.length">
                                <t t-foreach="state.team_summary" t-as="team" t-key="team.location + '_' + team.commercial_lead">
                                    <tr>
                                        <td class="location-cell"><t t-esc="team.location"/></td>
                                        <td class="lead-cell"><t t-esc="team.commercial_lead"/></td>
                                        <td><t t-esc="formatCurrency(team.ytd)"/></td>
                                        <td><t t-esc="formatCurrency(team.to_target)"/></td>
                                        <td><t t-esc="formatCurrency(team.target)"/></td>
                                        <td t-att-class="'ytd-vs-target-cell ' + (team.ytd_vs_target >= 100 ? 'bg-success' : 'bg-danger')">
                                            <t t-esc="formatNumber(team.ytd_vs_target)"/>%
                                        </td>
                                        <td><t t-esc="formatCurrency(team.qualify)"/></td>
                                        <td><t t-esc="formatCurrency(team.proposal)"/></td>
                                        <td><t t-esc="formatCurrency(team.shortlisted)"/></td>
                                        <td><t t-esc="formatCurrency(team.verbal)"/></td>
                                        <td><t t-esc="formatCurrency(team.total_pipeline)"/></td>
                                    </tr>
                                </t>
                            </t>
                            <t t-else="">
                                <tr>
                                    <td colspan="11" class="text-center text-muted" style="padding: 40px;">
                                        No sales team data available for <t t-esc="state.year"/>
                                    </td>
                                </tr>
                            </t>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>


        <!-- KPI Table -->
        <div class="plb-kpi-card mb-5">
            <div class="card-header">
                <h4>Salesperson KPI - <t t-esc="state.year"/></h4>
            </div>
            <div class="card-body p-0">
                <div class="plb-kpi-table-container">
                    <table class="table table-bordered plb-kpi-table">
                        <thead>
                            <tr>
                                <th rowspan="2" style="min-width: 150px;">Salesperson</th>
                                <th rowspan="2" style="min-width: 80px;">Matrix</th>
                                <th colspan="12" class="text-center">Monthly Data</th>
                            </tr>
                            <tr>
                                <th>Jan</th>
                                <th>Feb</th>
                                <th>Mar</th>
                                <th>Apr</th>
                                <th>May</th>
                                <th>Jun</th>
                                <th>Jul</th>
                                <th>Aug</th>
                                <th>Sep</th>
                                <th>Oct</th>
                                <th>Nov</th>
                                <th>Dec</th>
                            </tr>
                        </thead>
                        <tbody>
                            <t t-if="state.salespersons.length">
                                <t t-foreach="state.salespersons" t-as="sp" t-key="sp.id">
                                    <!-- Target Row -->
                                    <tr class="target-row">
                                        <td class="salesperson-name" t-att-rowspan="2"><t t-esc="sp.name"/></td>
                                        <td class="matrix-label">Target</td>
                                        <t t-foreach="sp.monthly_target" t-as="val" t-key="val_index">
                                            <td><t t-esc="formatCurrency(val)"/></td>
                                        </t>
                                    </tr>
                                    <!-- YTD Row -->
                                    <tr class="ytd-row">
                                        <td class="matrix-label">YTD</td>
                                        <t t-foreach="sp.monthly_ytd" t-as="val" t-key="val_index">
                                            <td><t t-esc="formatCurrency(val)"/></td>
                                        </t>
                                    </tr>
                                </t>
                            </t>
                            <t t-else="">
                                <tr>
                                    <td colspan="14" class="text-center text-muted" style="padding: 40px;">
                                        No salesperson data available for <t t-esc="state.year"/>
                                    </td>
                                </tr>
                            </t>
                        </tbody>
                        <tfoot t-if="state.salespersons.length">
                            <!-- Monthly Subtotal Target -->
                            <tr>
                                <td class="footer-label" colspan="2">Monthly Subtotal (Target)</td>
                                <t t-foreach="state.monthly_subtotals_target" t-as="val" t-key="val_index">
                                    <td><t t-esc="formatCurrency(val)"/></td>
                                </t>
                            </tr>
                            <!-- Monthly Subtotal YTD -->
                            <tr>
                                <td class="footer-label" colspan="2">Monthly Subtotal (YTD)</td>
                                <t t-foreach="state.monthly_subtotals_ytd" t-as="val" t-key="val_index">
                                    <td><t t-esc="formatCurrency(val)"/></td>
                                </t>
                            </tr>
                            <!-- Percentage (YTD/Target) -->
                            <tr>
                                <td class="footer-label" colspan="2">Percentage (%)</td>
                                <t t-foreach="state.monthly_percentage" t-as="val" t-key="val_index">
                                    <td><t t-esc="formatNumber(val)"/>%</td>
                                </t>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>
    </t>
</div>
`;
}

// Register the KPI component
registry.category("actions").add("PLB_kpi_tag", PLBKPI);

