# -*- coding: utf-8 -*-
{
    "name": "Product Rental Bookings",
    "category": "Product",
    "version": "14.0.1.0",
    "summary": "Book products on several rental periods ",
    "author": "Elabore",
    "website": "https://elabore.coop/",
    "installable": True,
    "application": True,
    "auto_install": False,
    "description": """
===========================
Product Rental Web Bookings
===========================
This module allows Odoo Internal users to manage product rental stocks and booking calendar

Installation
============
Just install product_rental_web_bookings, all dependencies will be installed by default.

Known issues / Roadmap
======================

Bug Tracker
===========
Bugs are tracked on `GitHub Issues
<https://github.com/elabore-coop/.../issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------
* Elabore: `Icon <https://elabore.coop/web/image/res.company/1/logo?unique=f3db262>`_.

Contributors
------------
* Stéphan Sainléger <https://github.com/stephansainleger>

Funders
-------
The development of this module has been financially supported by:
* Elabore (https://elabore.coop)

Maintainer
----------
This module is maintained by ELABORE.

""",
    "depends": ["base", "account", "website_sale", "hr", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/assets.xml",
        "views/sequence.xml",
        "views/account_invoice_view.xml",
        "views/product_book.xml",
        "views/product_view.xml",
        "views/product_contract.xml",
        "wizard/advance_payment_invoice.xml",
        "views/product_operation.xml",
        "views/product_order.xml",
        "views/product_move.xml",
        "views/res_config_settings_view.xml",
        "views/stock_picking.xml",
        "report/rental_order.xml",
        "report/rental_order_report.xml",
        "report/rental_contract_report.xml",
        "report/rental_contract_recurring.xml",
        "data/data.xml",
        "views/session_config_settings_view.xml",
        "views/menus.xml",
    ],
    "qweb": [
        "static/src/xml/delivery_sign.xml",
        "static/src/xml/product_booking_calender.xml",
    ],
}
