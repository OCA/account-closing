# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Prepaid module for OpenERP
#    Copyright (C) 2013 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp.osv import orm, fields


class product_template(orm.Model):
    _inherit = 'product.template'

    _columns = {
        'must_have_dates': fields.boolean(
            'Must Have Start and End Dates',
            help="If this option is active, the user will have to enter "
            "a Start Date and an End Date on the invoice lines that have "
            "this product."),
    }
