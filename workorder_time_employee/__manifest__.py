# -*- coding: utf-8 -*-
{
    'name': "Work Order Time Employee",
    'summary': """
    This module adds duration editable by Manufacturing Manager and adds employee field on time tracking.
""",
    'description': """
This module adds duration editable by Manufacturing Manager and adds employee field on time tracking.
""",

    'author': "Shola Ojo-Bello",
    'version': '0.1',
    'depends': ['mrp','hr'],
    'data': [
        'views/misc_view.xml'
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}