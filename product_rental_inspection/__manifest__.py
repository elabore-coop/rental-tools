# -*- coding: utf-8 -*-
{
    "name": "Product Rental Inspection",
    "category": "Product",
    "version": "14.0.1.0",
    "summary": "Register inspection process and cost on your rental booking",
    "author": "Elabore",
    "website": "https://elabore.coop/",
    "installable": True,
    "application": False,
    "auto_install": False,
    "description": """
=========================
Product Rental Inspection
=========================
This module allows the registering of inspection process on the rent products.

Installation
============
Just install product_rental_inspection, all dependencies will be installed by default.

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
    "depends": ["product_rental_bookings"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_inspection.xml",
        "views/stock_picking.xml",
        "views/sequence.xml",
        "report/inspection_report.xml",
        "report/inspection_report_template.xml",
        "views/menus.xml",
    ],
    "qweb": [],
}
