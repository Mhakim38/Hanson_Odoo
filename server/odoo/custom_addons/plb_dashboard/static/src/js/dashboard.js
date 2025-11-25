/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PLBDashboard extends Component {
    setup() {
        // reactive state
        this.state = useState({
            rows: [
                {
                    company: "ABC Corp",
                    quarter: "Q1",
                    sales: 120000,
                    stage: "Prospecting",
                    count: 5,
                    services: "Consulting",
                    customer: "Customer A",
                    annualRevenue: 480000,
                    monthlyRevenue: [10000, 12000, 15000, 13000, 14000, 16000, 12000, 11000, 13000, 14000, 15000, 16000],
                    stageRevenue: "Won",
                    carryForward: 5000,
                },
                {
                    company: "XYZ Ltd",
                    quarter: "Q2",
                    sales: 90000,
                    stage: "Negotiation",
                    count: 3,
                    services: "Support",
                    customer: "Customer B",
                    annualRevenue: 360000,
                    monthlyRevenue: [8000, 9000, 7000, 8500, 9000, 9500, 10000, 9000, 8500, 8700, 8800, 8900],
                    stageRevenue: "Pending",
                    carryForward: 3000,
                }
            ],
            // will be populated with unique customers from crm.lead (objects: { id, name })
            customers: [],
        });

        // rpc service for fetching model data
        this.rpc = useService("rpc");

        // Fetch customers (partner_id from crm.lead) on mount
        onMounted(async () => {
            try {
                // Request only leads that have a partner set to avoid empty partner values
                const leads = await this.rpc({
                    model: 'crm.lead',
                    method: 'search_read',
                    // args: [domain, fields]
                    args: [[['partner_id', '!=', false]], ['partner_id']],
                    // limit to avoid huge payloads; increase if needed
                    kwargs: { limit: 1000 },
                });

                // Debug: show raw RPC payload so we can see what's returned
                console.debug('plb_dashboard: fetched crm.lead partner_id results:', leads);

                // deduplicate partner entries and build array of {id, name}
                const partnerMap = {};
                for (const rec of leads || []) {
                    const p = rec.partner_id;
                    let pid = null;
                    let pname = '';

                    // handle falsy / missing partner
                    if (!p) {
                        // skip records without partner
                        console.debug('plb_dashboard: skipping lead without partner_id', rec);
                        continue;
                    }

                    // shape: [id, name]
                    if (Array.isArray(p)) {
                        pid = Number(p[0]);
                        pname = p[1] ? String(p[1]) : '';
                    }
                    // shape: { id: ..., name: ... } or {0: id, 1: name}
                    else if (typeof p === 'object' && p !== null) {
                        pid = Number(p.id ?? p[0]);
                        pname = p.name ?? p.display_name ?? p[1] ?? '';
                    }
                    // shape: numeric id or numeric string
                    else if (typeof p === 'number' || (typeof p === 'string' && /^\d+$/.test(p))) {
                        pid = Number(p);
                        pname = '';
                    }

                    if (Number.isFinite(pid) && pid > 0) {
                        if (!partnerMap[pid]) {
                            partnerMap[pid] = { id: pid, name: pname };
                        }
                    } else {
                        console.debug('plb_dashboard: invalid partner id parsed, skipping', p, 'from lead', rec);
                    }
                }
                // convert map to array sorted by name
                const customers = Object.values(partnerMap).sort((a, b) => (a.name || '').localeCompare(b.name || ''));

                // update reactive state
                this.state.customers = customers;
            } catch (err) {
                // keep silent but log to console for debugging
                console.error('Failed to fetch crm.lead partner list:', err);
            }
        });
    }
}

PLBDashboard.template = xml/* xml */ `
<div class="container my-4">
    <h3 class="mb-3">PLB Dashboard — Empty Table (Bootstrap)</h3>

    <!-- Customers list fetched from crm.lead.partner_id -->
    <div class="mb-3">
        <h5>Customers (from crm.lead)</h5>
        <t t-if="state.customers &amp;&amp; state.customers.length">
            <div style="display:flex; flex-wrap:wrap; gap:8px;">
                <t t-foreach="state.customers" t-as="c" t-key="c.id">
                    <div style="padding:6px 10px; background:#f1f3f5; border-radius:12px; font-size:13px;"> <t t-esc="c.name"/> </div>
                </t>
            </div>
        </t>
        <t t-else="">
            <div class="text-muted">No customers found.</div>
        </t>
    </div>

    <div class="table-responsive">
        <table class="table table-bordered table-hover sticky-head">
            <thead class="table-light">
                <tr>
                    <th rowspan="2">Company</th>
                    <th rowspan="2">Quarter</th>
                    <th rowspan="2">Sales</th>
                    <th rowspan="2">Stage</th>
                    <th rowspan="2">No (Count)</th>
                    <th rowspan="2">Services</th>
                    <th rowspan="2">Customer</th>
                    <th rowspan="2">Annualized Revenue</th>
                    <th colspan="12" class="text-center">Realized Revenue (Months)</th>
                    <th rowspan="2">Stage — Realized Revenue (Current Year)</th>
                    <th rowspan="2">Carry Forward (Next Year)</th>
                </tr>
                <tr>
                    <th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th>
                    <th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th>
                </tr>
            </thead>
            <tbody>
                <tr t-foreach="state.rows" t-as="row" t-key="row.company">
                    <td><t t-esc="row.company"/></td>
                    <td><t t-esc="row.quarter"/></td>
                    <td><t t-esc="row.sales"/></td>
                    <td><t t-esc="row.stage"/></td>
                    <td><t t-esc="row.count"/></td>
                    <td><t t-esc="row.services"/></td>
                    <td><t t-esc="row.customer"/></td>
                    <td><t t-esc="row.annualRevenue"/></td>

                    <!-- Loop for monthly revenue -->
                    <t t-foreach="row.monthlyRevenue" t-as="month" t-key="month">
                        <td><t t-esc="month"/></td>
                    </t>

                    <td><t t-esc="row.stageRevenue"/></td>
                    <td><t t-esc="row.carryForward"/></td>
                </tr>
            </tbody>


        </table>
    </div>
</div>
`;

registry.category("actions").add("PLB_dashboard_tag", PLBDashboard);
