/** @odoo-module **/
import { Component, useState, mount } from "@odoo/owl";

export class SmartChatWidget extends Component {
    setup() {
        this.state = useState({
            isOpen: false,
            messages: []
        });
    }

    toggleChat() {
        this.state.isOpen = !this.state.isOpen;
    }
}

SmartChatWidget.template = "smart_chat.SmartChatWidget";

// Montowanie do glownego layoutu po zaladowaniu
odoo.define('smart_chat.init_widget', function (require) {
    "use strict";
    const core = require('web.core');
    core.bus.on('web_client_ready', null, () => {
        const root = document.getElementById("smart_chat_root");
        if (root) {
            mount(SmartChatWidget, root);
        }
    });
});
