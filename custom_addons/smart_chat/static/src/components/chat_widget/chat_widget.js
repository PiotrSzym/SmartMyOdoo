/** @odoo-module **/
import { Component, useState, mount } from "@odoo/owl";
import rpc from 'web.rpc';

export class SmartChatWidget extends Component {
    setup() {
        this.state = useState({
            isOpen: false,
            isLoading: false,
            messages: []
        });
    }

    toggleChat() {
        this.state.isOpen = !this.state.isOpen;
    }

    async onKeydown(ev) {
        if (ev.key === "Enter" && ev.target.value.trim() && !this.state.isLoading) {
            const text = ev.target.value.trim();
            ev.target.value = "";

            this.state.messages.push({
                id: Date.now(),
                text: text,
                sender: "user"
            });

            this.state.isLoading = true;

            try {
                const hashParams = new URLSearchParams(window.location.hash.substring(1));
                const active_model = hashParams.get('model') || "";
                const active_id = parseInt(hashParams.get('id'), 10) || 0;

                const result = await rpc.query({
                    route: '/smart_chat/send',
                    params: {
                        message: text,
                        session_id: "default_session",
                        active_model: active_model,
                        active_id: active_id
                    }
                });

                this.state.messages.push({
                    id: Date.now(),
                    text: result.reply || "Brak odpowiedzi",
                    sender: "agent"
                });
            } catch (error) {
                console.error("Chat error:", error);
                this.state.messages.push({
                    id: Date.now(),
                    text: "Błąd komunikacji z serwerem Odoo.",
                    sender: "agent"
                });
            } finally {
                this.state.isLoading = false;
            }
        }
    }
}

SmartChatWidget.template = "smart_chat.SmartChatWidget";

import { registry } from "@web/core/registry";
// Rejestracja w systray (górny pasek) lub innym odpowiednim miejscu w nowoczesnym Odoo
registry.category("systray").add("smart_chat.SmartChatWidget", { Component: SmartChatWidget });
