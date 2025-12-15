/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PLBDashboard extends Component {
    setup() {
        // reactive state
        this.state = useState({
            rows: [],
            customers: [],
            stageCounts: {},
            revenueSummary: {
                total_expected_revenue: 0,
                total_annual_revenue: 0,
                total_realized_revenue: 0,
                lead_count: 0,
            },
            loading: true,
        });

        // rpc service for fetching model data
        this.rpc = useService("rpc");

        // Fetch all dashboard data on mount
        onMounted(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;

            // Fetch dashboard data from controller endpoint (similar to /titah/status_counts)
            const dashboardData = await this.rpc("/plb/dashboard_data");
            if (dashboardData && dashboardData.rows) {
                this.state.rows = dashboardData.rows;
            }

            // Fetch customers
            const customersData = await this.rpc("/plb/customers");
            if (customersData && customersData.customers) {
                this.state.customers = customersData.customers;
            }

            // Fetch stage counts
            const stageCounts = await this.rpc("/plb/stage_counts");
            if (stageCounts) {
                this.state.stageCounts = stageCounts;
            }

            // Fetch revenue summary
            const revenueSummary = await this.rpc("/plb/revenue_summary");
            if (revenueSummary) {
                this.state.revenueSummary = revenueSummary;
            }

            console.debug('PLB Dashboard loaded:', {
                rows: this.state.rows.length,
                customers: this.state.customers.length,
                stageCounts: this.state.stageCounts,
                revenueSummary: this.state.revenueSummary,
            });

        } catch (err) {
            console.error('Failed to load PLB dashboard data:', err);
        } finally {
            this.state.loading = false;
        }
    }
}

PLBDashboard.template = xml/* xml */ `
<div class="container my-4">
    <h3 class="mb-3">PLB Dashboard</h3>

    <!-- Loading state -->
    <t t-if="state.loading">
        <div class="text-center my-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading dashboard data...</p>
        </div>
    </t>

    <t t-else="">
        <!-- Revenue Summary Cards -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card text-center" style="border-left: 4px solid #007bff;">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">Total Leads</h6>
                        <h3 class="card-title"><t t-esc="state.revenueSummary.lead_count"/></h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center" style="border-left: 4px solid #28a745;">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">Expected Revenue</h6>
                        <h3 class="card-title">RM <t t-esc="state.revenueSummary.total_expected_revenue.toLocaleString()"/></h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center" style="border-left: 4px solid #ffc107;">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">Annual Revenue</h6>
                        <h3 class="card-title">RM <t t-esc="state.revenueSummary.total_annual_revenue.toLocaleString()"/></h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center" style="border-left: 4px solid #dc3545;">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">Realized FY2025</h6>
                        <h3 class="card-title">RM <t t-esc="state.revenueSummary.total_realized_revenue.toLocaleString()"/></h3>
                    </div>
                </div>
            </div>
        </div>

        <!-- Stage Counts -->
        <div class="mb-3">
            <h5>Pipeline Stages</h5>
            <t t-if="Object.keys(state.stageCounts).length">
                <div style="display:flex; flex-wrap:wrap; gap:12px;">
                    <t t-foreach="Object.entries(state.stageCounts)" t-as="entry" t-key="entry[0]">
                        <div style="padding:8px 16px; background:#e9ecef; border-radius:20px; font-size:14px;">
                            <strong><t t-esc="entry[0]"/>:</strong> <t t-esc="entry[1]"/>
                        </div>
                    </t>
                </div>
            </t>
            <t t-else="">
                <div class="text-muted">No stage data available.</div>
            </t>
        </div>

        <!-- Customers list fetched from crm.lead.partner_id -->
        <div class="mb-3">
            <h5>Customers (from crm.lead)</h5>
            <t t-if="state.customers &amp;&amp; state.customers.length">
                <div style="display:flex; flex-wrap:wrap; gap:8px;">
                    <t t-foreach="state.customers" t-as="c" t-key="c.id">
                        <div style="padding:6px 10px; background:#f1f3f5; border-radius:12px; font-size:13px;">
                            <t t-esc="c.name"/>
                        </div>
                    </t>
                </div>
            </t>
            <t t-else="">
                <div class="text-muted">No customers found.</div>
            </t>
        </div>

        <!-- Main Data Table -->
        <div class="table-responsive">
            <table class="table table-bordered table-hover table-sm sticky-head">
                <thead class="table-light">
                    <tr>
                        <th rowspan="2">Company</th>
                        <th rowspan="2">Customer</th>
                        <th rowspan="2">Stage</th>
                        <th rowspan="2">Expected Revenue</th>
                        <th rowspan="2">Services</th>
                        <th rowspan="2">Contract Type</th>
                        <th rowspan="2">Contract Months</th>
                        <th rowspan="2">Dept/Region</th>
                        <th rowspan="2">Annual Revenue</th>
                        <th colspan="12" class="text-center">Realized Revenue (Months)</th>
                        <th rowspan="2">Realized FY2025</th>
                        <th rowspan="2">Profit Margin %</th>
                    </tr>
                    <tr>
                        <th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th>
                        <th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th>
                    </tr>
                </thead>
                <tbody>
                    <t t-if="state.rows &amp;&amp; state.rows.length">
                        <tr t-foreach="state.rows" t-as="row" t-key="row.id">
                            <td><t t-esc="row.company"/></td>
                            <td><t t-esc="row.customer"/></td>
                            <td><t t-esc="row.stage"/></td>
                            <td class="text-end"><t t-esc="row.sales.toLocaleString()"/></td>
                            <td><t t-esc="row.services"/></td>
                            <td><t t-esc="row.contractType"/></td>
                            <td class="text-center"><t t-esc="row.contractMonths"/></td>
                            <td><t t-esc="row.deptRegion"/></td>
                            <td class="text-end"><t t-esc="row.annualRevenue.toLocaleString()"/></td>

                            <!-- Loop for monthly revenue -->
                            <t t-foreach="row.monthlyRevenue" t-as="month" t-key="month_index">
                                <td class="text-end"><t t-esc="month.toLocaleString()"/></td>
                            </t>

                            <td class="text-end"><t t-esc="row.realizedRevenue.toLocaleString()"/></td>
                            <td class="text-end"><t t-esc="row.profitMargin"/>%</td>
                        </tr>
                    </t>
                    <t t-else="">
                        <tr>
                            <td colspan="20" class="text-center text-muted">No data available</td>
                        </tr>
                    </t>
                </tbody>
            </table>
        </div>
    </t>
</div>
`;

registry.category("actions").add("PLB_dashboard_tag", PLBDashboard);
