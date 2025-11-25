/** @odoo-module **/

import { Component, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class TitahDashboard extends Component {
    setup() {
        this.rpc = useService("rpc");

        this.statusCounts = { hijau: 0, kuning: 0, merah: 0 };
        this.responCounts = { selesai: 0, sedang: 0, belum: 0 };

        onMounted(async () => {
            // Get status pelaksanaan
            const pelaksanaanData = await this.rpc("/titah/status_counts");
            if (pelaksanaanData) {
                this.statusCounts = pelaksanaanData;
            }

            // Get status maklum balas
            const responData = await this.rpc("/titah/respon_status_counts");
            if (responData) {
                this.responCounts = responData;
            }

            this.render();
        });
    }

    static template = "titah_sultan.TitahDashboardTemplate";
}

registry.category("actions").add("titah_dashboard", TitahDashboard);
