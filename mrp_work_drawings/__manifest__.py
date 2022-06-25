# -*- coding: utf-8 -*-
{
    'name': "Mrp Workorder Drawings",
    'version': '15.0.0.1',
    'category': 'MRP',
    'summary': 'Allows to add Drawings on MO and Workorder',
    'description': """
    This module allows you to add drawings on MO and workorders.
    """,
    'author': "Shola Ojo-Bello",
    'depends': ['mrp','mrp_workorder'],
    'data': [
        'views/mrp_production_view.xml',
    ],
}
