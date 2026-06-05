/** @odoo-module **/
import { Component, useState, mount } from "@odoo/owl";
import rpc from 'web.rpc';
import core from 'web.core';

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
                const result = await rpc.query({
                    route: '/smart_chat/send',
                    params: {
                        message: text,
                        session_id: "default_session"
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

// Montowanie do glownego layoutu po zaladowaniu (ES6 Module)
core.bus.on('web_client_ready', null, () => {
    const root = document.getElementById("smart_chat_root");
    if (root) {
        mount(SmartChatWidget, root);
    }
});
