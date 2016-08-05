from openerp import models, fields, api

class HotelRoom(models.Model):
	_inherit = 'hotel.room'
	
	dormitory = fields.Boolean('Dormitory')
	bed_ids = fields.One2many('hotel.room.bed','room_id')
	nr_beds = fields.Integer('Nr of beds in room', default=1)

	@api.model
	def create(self,vals):
		# IF THE ROOM IS A DORM, CREATE BEDS
		if vals['dormitory']:
			print "CREATING BEDS FOR DORM"
			new_beds = []
			for i in range(vals['capacity']):
				bed_name = "Bed #" + str(i+1)
				bed_vals = {'name': bed_name, 'capacity': 1,}
				new_beds.append((0,0,bed_vals))
				print new_beds
			vals.update({'bed_ids': new_beds})
		# END OVERRIDE
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
	
	# Checks availability for a bed for a certain time-period
	# Returns False if there are reservations overlaping selected time-period
	# Returns True if there are no other reservations within time-period
	@api.one
	def check_availability(self, check_in, check_out):
		self.env.cr.execute("SELECT * FROM hotel_room_reservation_line WHERE (check_in,check_out) OVERLAPS ( timestamp %s, timestamp %s ) AND bed_id=%s", (check_in, check_out, self.id))
		query_result = self.env.cr.fetchall()
		if query_result:
			return False
		else:
			return True
		
class HotelRoomReservationLine(models.Model):
	_inherit = 'hotel.room.reservation.line'
	
	bed_id = fields.Many2one(comodel_name='hotel.room.bed', string='Bed id')

class HotelReservationLine(models.Model):
	_inherit = 'hotel_reservation.line'
	
	bed_reserve = fields.Many2many('hotel.room.bed','hotel_reservation_line_bed_rel',
						'hotel_reservation_line_id', 'bed_id')