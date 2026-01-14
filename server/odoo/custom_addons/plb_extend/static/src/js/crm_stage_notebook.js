/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

patch(FormRenderer.prototype, {

    onRecordChanged(record) {
        this._super(...arguments);

        if (!record || !record.data) return;

        // tunggu notebook render siap
        setTimeout(() => {
            this._openNotebookByStage(record.data);
        }, 0);
    },

    _openNotebookByStage(data) {
        const notebook = this.el.querySelector(".o_notebook");
        if (!notebook) return;

        let targetTab = null;

        /**
         * ===============================
         * STAGE → TAB MAPPING (IKUT MODEL)
         * ===============================
         */

        // 1️⃣ NEW
        if (data.is_new_stage) {
            targetTab = "tab_new";
        }

        // 2️⃣ QUALIFY
        else if (data.is_qualify_stage) {
            targetTab = "tab_qualify";
        }

        // 3️⃣ PROPOSAL SUBMITTED
        else if (data.is_proposal_submitted_stage) {
            targetTab = "tab_proposal";
        }

        // 4️⃣ CONTRACT FLOW (Shortlisted / Verbal / Contract)
        else if (data.is_contract_stage) {
            targetTab = "tab_contract";
        }

        // 🚫 Renewal / Decline / Loss → TAK auto tukar tab
        else {
            return;
        }

        const tab = notebook.querySelector(`[name="${targetTab}"]`);
        if (tab && !tab.classList.contains("active")) {
            tab.click();
        }
    },
});
