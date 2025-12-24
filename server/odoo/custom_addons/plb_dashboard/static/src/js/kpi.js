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
            monthly_subtotals_ytd: Array(12).fill(0),
            monthly_subtotals_target: Array(12).fill(0),
            monthly_percentage: Array(12).fill(0),
            // Gauge meter data
            company_yearly_target: 0,
            total_ytd_revenue: 0,
            total_realized_revenue: 0,
            total_target_revenue: 0,
            ytd_percentage: 0,
            realized_percentage: 0,
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

            // Fetch KPI data from controller endpoint
            const kpiData = await this.rpc("/plb/kpi_data", { year: year });

            if (kpiData) {
                this.state.salespersons = kpiData.salespersons || [];
                this.state.monthly_subtotals_ytd = kpiData.monthly_subtotals_ytd || Array(12).fill(0);
                this.state.monthly_subtotals_target = kpiData.monthly_subtotals_target || Array(12).fill(0);

                // Gauge meter data
                this.state.company_yearly_target = kpiData.company_yearly_target || 0;
                this.state.total_ytd_revenue = kpiData.total_ytd_revenue || 0;
                this.state.total_realized_revenue = kpiData.total_realized_revenue || 0;
                this.state.total_target_revenue = kpiData.total_target_revenue || 0;
                this.state.ytd_percentage = kpiData.ytd_percentage || 0;
                this.state.realized_percentage = kpiData.realized_percentage || 0;

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

    // Helper: get color based on percentage zones
    getGaugeColor(percentage) {
        if (percentage < 50) {
            return '#C62828'; // Red - Fail
        } else if (percentage >= 50 && percentage < 70) {
            return '#F57C00'; // Orange - Entry
        } else if (percentage >= 70 && percentage <= 100) {
            return '#0D47A1'; // Blue - Target (70-100%)
        } else {
            return '#2E7D32'; // Green - Exceeded (>100%)
        }
    }

    // Helper: get status label based on percentage
    getGaugeStatus(percentage) {
        if (percentage < 50) {
            return 'FAIL';
        } else if (percentage >= 50 && percentage < 70) {
            return 'ENTRY';
        } else if (percentage >= 70 && percentage <= 100) {
            return 'TARGET';
        } else {
            return 'EXCEEDED';
        }
    }

    // Helper: generate gauge arc path
    getGaugeArcPath(percentage) {
        // Semi-circle gauge with flat side at Y=100 (bottom)
        // Arc goes from left (180°) to right (0° or 360°)
        // Support up to 120% to show exceeded performance
        const maxPercentage = 120; // Extended to 120% to show exceeded
        const clampedPercentage = Math.min(maxPercentage, Math.max(0, percentage));

        // If percentage is 0, return empty path
        if (clampedPercentage === 0) {
            return '';
        }

        // Convert percentage to angle (180° to 360°, or equivalently 180° to 0°)
        // At 0%: angle = 180° (left side)
        // At 60%: angle = 270° (bottom/center) - maps 50% of 120% range
        // At 100%: angle = 330° (83.33% of arc)
        // At 120%: angle = 360° (0°, right side - full arc)
        const startAngle = 180; // degrees
        const endAngle = 180 + (clampedPercentage / maxPercentage) * 180; // 180° to 360° for 0-120%
        const endAngleRad = (endAngle * Math.PI) / 180;

        const cx = 100; // center x
        const cy = 100; // center y
        const radius = 80;

        const startX = cx - radius; // Start at 180° (left side) = 20
        const startY = cy; // Y = 100
        const endX = cx + radius * Math.cos(endAngleRad);
        const endY = cy + radius * Math.sin(endAngleRad);

        // For half-circle, largeArcFlag should always be 0 (since we never go more than 180°)
        // sweepFlag should be 1 (clockwise)
        return `M ${startX} ${startY} A ${radius} ${radius} 0 0 1 ${endX} ${endY}`;
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

    .plb-target-display {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        padding: 16px 24px;
        border-radius: 16px;
        border: 2px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        min-width: 240px;
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

    /* Smooth transitions */
    * {
        transition: background-color 0.2s ease, border-color 0.2s ease;
    }

    /* Gauge Meter Styling */
    .plb-gauge-container {
        display: flex;
        gap: 24px;
        margin-bottom: 24px;
        flex-wrap: wrap;
    }

    .plb-gauge-card {
        flex: 1;
        min-width: 300px;
        background: #FFFFFF;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
        padding: 20px;
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    .plb-gauge-title {
        font-size: 1rem;
        font-weight: 600;
        color: #1A1A1A;
        margin-bottom: 16px;
        text-align: center;
    }

    .plb-gauge-svg {
        width: 200px;
        height: 130px;
        margin-bottom: 12px;
    }

    .plb-gauge-background {
        fill: none;
        stroke: #E0E0E0;
        stroke-width: 12;
        stroke-linecap: round;
    }

    .plb-gauge-arc {
        fill: none;
        stroke-width: 12;
        stroke-linecap: round;
        transition: stroke 0.3s ease;
    }

    .plb-gauge-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1A1A1A;
        margin-bottom: 4px;
    }

    .plb-gauge-label {
        font-size: 0.85rem;
        color: #4A4A4A;
        margin-bottom: 8px;
    }

    .plb-gauge-status {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        color: #FFFFFF;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .plb-gauge-status.fail {
        background: #C62828;
    }

    .plb-gauge-status.entry {
        background: #F57C00;
    }

    .plb-gauge-status.target {
        background: #0D47A1;
    }

    .plb-gauge-status.exceeded {
        background: #2E7D32;
    }

    .plb-gauge-zones {
        display: flex;
        justify-content: center;
        gap: 12px;
        margin-top: 12px;
        flex-wrap: wrap;
    }

    .plb-gauge-zone {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 0.75rem;
        color: #4A4A4A;
    }

    .plb-gauge-zone-color {
        width: 12px;
        height: 12px;
        border-radius: 2px;
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
                        <h1 class="plb-header-main-title">KPI Dashboard</h1>
                        <p class="plb-header-subtitle">Salesperson performance metrics and targets</p>
                    </div>
                </div>
                <div class="plb-header-right">
                    <div class="plb-target-display">
                        <div class="plb-target-label">Company Yearly Target</div>
                        <div class="plb-target-value">MYR <t t-esc="formatNumber(state.company_yearly_target)"/> Million</div>
                    </div>
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

        <!-- Gauge Meters -->
        <div class="plb-gauge-container">
            <!-- YTD Revenue Target Gauge -->
            <div class="plb-gauge-card">
                <h5 class="plb-gauge-title">YTD Rev Target (MYR mil)</h5>
                <svg class="plb-gauge-svg" viewBox="0 0 200 130">
                    <!-- Background arc (gray) -->
                    <path class="plb-gauge-background" d="M 20 100 A 80 80 0 0 1 180 100"/>

                    <!-- Progress arc (colored based on percentage) -->
                    <path class="plb-gauge-arc"
                          t-att-d="getGaugeArcPath(state.ytd_percentage)"
                          t-att-stroke="getGaugeColor(state.ytd_percentage)"/>


                    <!-- Percentage text -->
                    <text x="100" y="115" text-anchor="middle" font-size="20" font-weight="bold" fill="#1A1A1A">
                        <t t-esc="formatNumber(state.ytd_percentage)"/>%
                    </text>
                </svg>
                <div class="plb-gauge-value">
                    <t t-esc="formatNumber(state.total_ytd_revenue)"/> M
                </div>
                <div class="plb-gauge-label">Expected Revenue (Millions)</div>
                <span class="plb-gauge-status" t-att-class="getGaugeStatus(state.ytd_percentage).toLowerCase()">
                    <t t-esc="getGaugeStatus(state.ytd_percentage)"/>
                </span>
                <div class="plb-gauge-zones">
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #C62828;"></span>
                        <span>Fail</span>
                    </div>
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #F57C00;"></span>
                        <span>Entry</span>
                    </div>
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #0D47A1;"></span>
                        <span>Target</span>
                    </div>
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #2E7D32;"></span>
                        <span>Exceeded</span>
                    </div>
                </div>
            </div>

            <!-- Realized Revenue Target Gauge -->
            <div class="plb-gauge-card">
                <h5 class="plb-gauge-title">Realized Rev Target (MYR mil)</h5>
                <svg class="plb-gauge-svg" viewBox="0 0 200 130">
                    <!-- Background arc (gray) -->
                    <path class="plb-gauge-background" d="M 20 100 A 80 80 0 0 1 180 100"/>

                    <!-- Progress arc (colored based on percentage) -->
                    <path class="plb-gauge-arc"
                          t-att-d="getGaugeArcPath(state.realized_percentage)"
                          t-att-stroke="getGaugeColor(state.realized_percentage)"/>


                    <!-- Percentage text -->
                    <text x="100" y="115" text-anchor="middle" font-size="20" font-weight="bold" fill="#1A1A1A">
                        <t t-esc="formatNumber(state.realized_percentage)"/>%
                    </text>
                </svg>
                <div class="plb-gauge-value">
                    <t t-esc="formatNumber(state.total_realized_revenue)"/> M
                </div>
                <div class="plb-gauge-label">Monthly Subtotal YTD (Millions)</div>
                <span class="plb-gauge-status" t-att-class="getGaugeStatus(state.realized_percentage).toLowerCase()">
                    <t t-esc="getGaugeStatus(state.realized_percentage)"/>
                </span>
                <div class="plb-gauge-zones">
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #C62828;"></span>
                        <span>Fail</span>
                    </div>
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #F57C00;"></span>
                        <span>Entry</span>
                    </div>
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #0D47A1;"></span>
                        <span>Target</span>
                    </div>
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #2E7D32;"></span>
                        <span>Exceeded</span>
                    </div>
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

