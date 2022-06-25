# -*- coding: utf-8 -*-
{
    'name': "Analytic Account Change",

    'version': '15.0.0.1',
    'category': 'account',
    'summary': 'Adds analytic account on customer and auto select it on invoices',
    'description': """
    """,
    'author': "Shola Ojo-Bello",
    # any module necessary for this one to work correctly
    'depends': ['account','analytic'],

    # always loaded
    'data': [
        'views/partner_analytic.xml',
    ],
}
