# -*- coding: utf-8 -*-
{
    "name": "Product Rental Delay Management",
    "category": "Product",
    "version": "14.0.1.0",
    "summary": "Management delays and their costs on your rental booking",
    "author": "Elabore",
    "website": "https://elabore.coop/",
    "installable": True,
    "application": False,
    "auto_install": False,
    "description": """
===============================
Product Rental Delay Management
===============================
This module allows the registering of delay information which impact the total booking cost.

Installation
============
Just install product_rental_delay_management, all dependencies will be installed by default.

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
        "views/stock_picking.xml",
    ],
    "qweb": [],
}
