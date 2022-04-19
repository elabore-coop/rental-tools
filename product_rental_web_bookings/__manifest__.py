# -*- coding: utf-8 -*-
{
    "name": "Product Rental Web Bookings",
    "category": "Product",
    "version": "14.0.1.0",
    "summary": "Book products on several rental periods through website",
    "author": "Elabore",
    "website": "https://elabore.coop/",
    "installable": True,
    "application": True,
    "auto_install": False,
    "description": """
=======================
Product Rental Bookings
=======================
This module allows Odoo website visitors to rent products on several periods.

Installation
============
Just install product_rental_bookings, all dependencies will be installed by default.

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
    "depends": ["base", "product_rental_bookings"],
    "data": [
        "views/product_template.xml",
        "views/website_templates.xml",
    ],
    "qweb": [],
}
