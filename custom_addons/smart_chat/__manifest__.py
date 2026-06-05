{
    "name": "Smart Chat (Agent Swarm)",
    "version": "1.0",
    "category": "Hidden",
    "summary": "OWL Chat Widget and Shadow Mode UI for AI Swarm",
    "depends": ["base", "web"],
    "data": ["views/web_layout_inherit.xml", "views/form_view_inherit.xml"],
    "assets": {
        "web.assets_backend": [
            "smart_chat/static/src/components/chat_widget/chat_widget.js",
            "smart_chat/static/src/components/chat_widget/chat_widget.xml",
            "smart_chat/static/src/components/shadow_banner/shadow_banner.js",
            "smart_chat/static/src/components/shadow_banner/shadow_banner.xml",
        ]
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
