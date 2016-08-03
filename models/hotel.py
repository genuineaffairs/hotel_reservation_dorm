from openerp import models, fields, api

class HotelRoom(models.Model):
	_inherit = 'hotel.room'
	
	dormitory = fields.Boolean('Dormitory')

	