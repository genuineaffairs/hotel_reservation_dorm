from openerp import models, fields, api, exceptions

class HotelRoom(models.Model):
	_inherit = 'hotel.room'
	# Extra fields for dorm-rooms
	dormitory = fields.Boolean('Dormitory')
	bed_ids = fields.One2many('hotel.room.bed','room_id')
	dorm_reservation_line_ids = fields.One2many('hotel.room.reservation.line', 'dorm_id', string='Bed Reservation Line')
	
	@api.model
	def create(self,vals):
		# Create beds corresponding to the capacity of the room if it is a dorm
		if vals['dormitory']:
			new_beds = []
			for i in range(vals['capacity']):
				bed_name = "Bed #" + str(i+1)
				bed_vals = {'name': bed_name, 'capacity': 1,}
				new_beds.append((0,0,bed_vals))
			vals.update({'bed_ids': new_beds})

		uom_obj = self.env['product.uom']
		vals.update({'type':'service'})
		uom_rec = uom_obj.search([('name','ilike','Hour(s)')],limit=1)
		if uom_rec:
			vals.update({'uom_id':uom_rec.id,'uom_po_id':uom_rec.id})
		return super(HotelRoom,self).create(vals)
	

class HotelBed(models.Model):
	_name = 'hotel.room.bed'
	
	name = fields.Char('Bed name') 
	room_id = fields.Many2one('hotel.room','bed_ids', ondelete='cascade')
	
	status = fields.Selection([('available', 'Available'),
							('occupied', 'Occupied')],
							'Status', default='available')
	bed_line_ids = fields.One2many('folio.room.line', 'room_id', string='Bed Reservation Line')
	bed_reservation_line_ids = fields.One2many('hotel.room.reservation.line', 'bed_id', string='Bed Reservation Line')
	
	# Checks availability for a bed for a certain time-period
	# Returns False if there are reservations overlaping selected time-period
	# Returns True if there are no other reservations within time-period
	@api.one
	def check_availability(self, check_in, check_out):
		self.env.cr.execute("SELECT * FROM hotel_room_reservation_line WHERE (check_in,check_out) OVERLAPS ( timestamp %s, timestamp %s ) AND bed_id=%s AND state='assigned'", (check_in, check_out, self.id))
		query_result = self.env.cr.fetchall()
		if query_result:
			return False
		else:
			return True
		
class HotelRoomReservationLine(models.Model):
	_inherit = 'hotel.room.reservation.line'
	
	# bed_id lets user make a reservation connected to a bed
	# dorm_id marks which room the reservation is connected to
	bed_id = fields.Many2one(comodel_name='hotel.room.bed', string='Bed id')
	dorm_id = fields.Many2one(comodel_name='hotel.room', string='Dorm room id')
	
class HotelFolio(models.Model):
	_inherit = 'hotel.folio'
	
	@api.constrains('room_lines')
	def folio_room_lines(self):
		folio_rooms = []
		for room in self[0].room_lines:
			if room.product_id.id in folio_rooms:
				raise exceptions.Warning('You cannot take same room twice')
			# Get a handle on the room the reservation regards
			room_obj = self.env['hotel.room'].search([('product_id','=',room.product_id.id)])
			# If the room is a dormitory we will allow to make multiple folio.lines
			if not room_obj.dormitory:
				folio_rooms.append(room.product_id.id)
			
