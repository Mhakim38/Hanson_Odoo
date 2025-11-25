/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { onMounted } from "@odoo/owl";

export class CustomTitahResponListController extends ListController {
    setup() {
        super.setup();
        onMounted(() => {
            this.addCustomBanner();
        });
    }

    async addCustomBanner() {
        const counts = await this.rpc('/titah/respon_status_counts');

        const root = this.el || document.querySelector('.o_content') || document.body;
        if (!root || root.querySelector('.custom-titah-wrapper')) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'custom-titah-wrapper';
        wrapper.style = `
            margin-bottom: 30px;
            text-align: center;
        `;

        // === Logo and Title ===
        const logoContainer = document.createElement('div');
        logoContainer.style = `
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-bottom: 24px;
            padding-top: 10px;
        `;

        const logoImg = document.createElement('img');
        logoImg.src = '/titah_sultan/static/src/img/logo.png';
        logoImg.alt = 'Logo';
        logoImg.style = `
            height: 60px;
            margin-bottom: 8px;
        `;

        const header = document.createElement('h2');
        header.innerText = "Status Maklum Balas Titah";
        header.style = `
            font-size: 20px;
            font-weight: 700;
            margin: 0;
            color: #343a40;
        `;

        logoContainer.appendChild(logoImg);
        logoContainer.appendChild(header);
        wrapper.appendChild(logoContainer);

        // === Status circle row ===
        const circleRow = document.createElement('div');
        circleRow.style = `
            display: flex;
            justify-content: center;
            gap: 48px;
            flex-wrap: wrap;
            margin-bottom: 32px;
        `;

        const respon_statuses = [
            { key: 'selesai', label: 'Selesai', color: '#28a745' },
            { key: 'sedang', label: 'Sedang Diproses', color: '#ffc107' },
            { key: 'belum', label: 'Belum Ada Tindakan', color: '#dc3545' },
        ];

        respon_statuses.forEach(status => {
            const container = document.createElement('div');
            container.style = `
                text-align: center;
                min-width: 100px;
                flex: 1;
                max-width: 150px;
            `;

            const label = document.createElement('div');
            label.innerText = status.label;
            label.style = `
                margin-bottom: 10px;
                font-weight: 600;
                color: #333;
            `;

            const circle = document.createElement('div');
            circle.innerText = counts[status.key] || 0;
            circle.style = `
                width: 90px;
                height: 90px;
                border-radius: 50%;
                border: 4px solid ${status.color};
                color: ${status.color};
                font-size: 26px;
                font-weight: 700;
                display: flex;
                align-items: center;
                justify-content: center;
                background-color: white;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                transition: transform 0.1s ease-in-out;
                margin: 0 auto;
                cursor: pointer;
            `;

            circle.addEventListener('mouseenter', () => {
                circle.style.transform = 'scale(1.05)';
            });
            circle.addEventListener('mouseleave', () => {
                circle.style.transform = 'scale(1)';
            });
            circle.addEventListener('click', () => this.filterByStatus(status.key));

            container.appendChild(label);
            container.appendChild(circle);
            circleRow.appendChild(container);
        });

        wrapper.appendChild(circleRow);

        // === Reset Button (centered) ===
        const resetContainer = document.createElement('div');
        resetContainer.style = `
            display: flex;
            justify-content: center;
        `;

        const resetBtn = document.createElement('div');
        resetBtn.innerText = 'Reset';
        resetBtn.style = `
            padding: 10px 28px;
            background: #6c757d;
            color: white;
            border-radius: 999px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            transition: transform 0.1s ease-in-out;
        `;

        resetBtn.addEventListener('mouseenter', () => {
            resetBtn.style.transform = 'scale(1.05)';
        });
        resetBtn.addEventListener('mouseleave', () => {
            resetBtn.style.transform = 'scale(1)';
        });
        resetBtn.addEventListener('click', () => this.filterByStatus(null));

        resetContainer.appendChild(resetBtn);
        wrapper.appendChild(resetContainer);

        root.prepend(wrapper);
    }

    filterByStatus(status) {
        const domain = status ? [["status_tindakan", "=", status]] : [];
        this.model.load({ domain });
        console.log(`🔍 Filtered: ${status || 'All'}`);
    }

}

registry.category("views").add("titah_respon_list", {
    ...registry.category("views").get("list"),
    Controller: CustomTitahResponListController,
});
