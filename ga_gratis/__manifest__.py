{
    "name": "Gratis",
    "summary": """Odoo without charges""",
    "description": """
        Odoo without charges
    """,
    "author": "My Company",
    "website": "http://www.yourcompany.com",
    "category": "hidden",
    "version": "1.0",
    "depends": ["base", "mail"],
    "data": [
        # 'security/ir.model.access.csv',
        "data/views.xml",
        "data/templates.xml",
    ],
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
}
