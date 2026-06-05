/** @odoo-module **/
import { Component, useState, mount } from "@odoo/owl";

export class ShadowBannerWidget extends Component {
    setup() {
        this.state = useState({
            isVisible: false,
            proposalText: ""
        });

        // Nasluchiwanie na eventy od Swarmu
        window.addEventListener('swarm_shadow_mode_trigger', (e) => {
            this.state.isVisible = true;
            this.state.proposalText = e.detail.text;
        });
    }

    confirmAction() {
        // Zwalnia blokade ACTUATION w FSM
        console.log("Confirmed shadow action!");
        this.state.isVisible = false;
        // W realnym uzyciu tutaj nastepuje wywolanie API do Dispatchera zeby dokonczyc transakcje
    }

    rejectAction() {
        // Wymusza rollback w FSM
        console.log("Rejected shadow action!");
        this.state.isVisible = false;
    }
}

ShadowBannerWidget.template = "smart_chat.ShadowBannerWidget";

odoo.define('smart_chat.init_shadow_banner', function (require) {
    "use strict";
    const core = require('web.core');
    core.bus.on('web_client_ready', null, () => {
        const root = document.getElementById("smart_shadow_banner_root");
        if (root) {
            mount(ShadowBannerWidget, root);
        }
    });
});
