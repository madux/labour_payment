#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Maduka Sopulu Chris kingston
#
# Created:     20/04/2018
# Copyright:   (c) kingston 2018
# Licence:     <your licence>
#-------------------------------------------------------------------------------
{
    'name': 'Labour Payment',
    'version': '10.0.1.0.0',
    'author': 'Maduka Sopulu',
    'description':"""Labour application is a module that helps organization make labour payments""",
    'category': 'Payments Request',

    'depends': ['account','construction_material','project','branch','construction_rewrite'],
    'data': [
        'views/labour_payment_view.xml',
        'security/security_group.xml',
        'security/ir.model.access.csv',
    ],
    'price': 14.99,
    'currency': 'USD',


    'installable': True,
    'auto_install': False,
}
