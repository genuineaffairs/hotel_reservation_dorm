from openerp import models, fields, api

class HotelRoom(models.Model):
	_inherit = 'hotel.room'
	
	dormitory = fields.Boolean('Dormitory')
	bed_ids = fields.One2many('hotel.room.bed','room_id')
	

class HotelBed(models.Model):
	_name = 'hotel.room.bed'
	_inherit = 'hotel.room'
	
	name = fields.Char('Bed name') 
	room_id = fields.Many2one('hotel.room','bed_ids')
	