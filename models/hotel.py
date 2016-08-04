from openerp import models, fields, api

class HotelRoom(models.Model):
	_inherit = 'hotel.room'
	
	dormitory = fields.Boolean('Dormitory')
	bed_ids = fields.One2many('hotel.room.bed','room_id')
	nr_beds = fields.Integer('Nr of beds in room', default=1)
	

class HotelBed(models.Model):
	_name = 'hotel.room.bed'
	
	name = fields.Char('Bed name') 
	room_id = fields.Many2one('hotel.room','bed_ids')
	
	status = fields.Selection([('available', 'Available'),
							('occupied', 'Occupied')],
							'Status', default='available')
	capacity = fields.Integer('Capacity', default=1)
	bed_line_ids = fields.One2many('folio.room.line', 'room_id', string='Bed Reservation Line')
	product_id = fields.Many2one('product.product', 'Product_id',
		required=True, delegate=True,
		ondelete='cascade')
		