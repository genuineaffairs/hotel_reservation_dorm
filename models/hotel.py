from openerp import models, fields, api

class HotelRoom(models.Model):
	_inherit = 'hotel.room'
	
	dormitory = fields.Boolean('Dormitory')
	bed_ids = fields.One2many('hotel.room.bed','room_id')
	nr_beds = fields.Integer('Nr of beds in room', default=1)

	@api.model
	def create(self,vals):
		# IF THE ROOM IS A DORM, CREATE BEDS
		if self.dormitory:
			print "CREATING BEDS FOR DORM"
			for i in self.capacity:
				print i
				bed_vals = {'room_id': self.id}
				self.beds_ids = self.env['hotel.room.bed'].create(bed_vals)
		uom_obj = self.env['product.uom']
		vals.update({'type':'service'})
		uom_rec = uom_obj.search([('name','ilike','Hour(s)')],limit=1)
		if uom_rec:
			vals.update({'uom_id':uom_rec.id,'uom_po_id':uom_rec.id})
		return super(HotelRoom,self).create(vals)
	

class HotelBed(models.Model):
	_name = 'hotel.room.bed'
	
	name = fields.Char('Bed name') 
	room_id = fields.Many2one('hotel.room','bed_ids')
	
	status = fields.Selection([('available', 'Available'),
							('occupied', 'Occupied')],
							'Status', default='available')
	capacity = fields.Integer('Capacity', default=1)
	bed_line_ids = fields.One2many('folio.room.line', 'room_id', string='Bed Reservation Line')
	bed_reservation_line_ids = fields.One2many('hotel.room.reservation.line', 'bed_id', string='Bed Reserv Line')
	product_id = fields.Many2one('product.product', 'Product_id',
		required=True, delegate=True,
		ondelete='cascade')
		
class HotelRoomReservationLine(models.Model):
	_inherit = 'hotel.room.reservation.line'
	
	bed_id = fields.Many2one(comodel_name='hotel.room.bed', string='Bed id')

class HotelReservationLine(models.Model):
	_inherit = 'hotel_reservation.line'
	
	bed_reserve = fields.Many2many('hotel.room.bed','hotel_reservation_line_bed_rel',
						'hotel_reservation_line_id', 'bed_id')