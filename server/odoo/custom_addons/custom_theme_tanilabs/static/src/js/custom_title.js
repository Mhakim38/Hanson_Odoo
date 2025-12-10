/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

// Patch the WebClient to change the title
patch(WebClient.prototype, {
    setup() {
        super.setup();
        console.log("Custom title script loaded");
        const titleService = useService("title");
        titleService.setParts({ zopenerp: "Tanilabs" });
    },
});
