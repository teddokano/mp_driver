from machine	import	Pin, I2C, SPI
from utime 		import	sleep

from nxp_periph.interface	import	Interface, I2C_target, SPI_target

def	main():

	bridge_demo	= True
#	bridge_demo	= False

	if bridge_demo:
		i2c		= I2C( 0, 400 * 1000 )
		eeprom	= AT25010_Br( i2c, 1, int = Pin( "D2", Pin.IN, Pin.PULL_UP ) )
	else:
		spi		= SPI( 1, SPI_target.FREQ, sck = Pin( 10 ), mosi = Pin( 11 ), miso = Pin( 12 ) )
		eeprom	= AT25010( spi, Pin( 13, Pin.OUT ) )

	print( "instance of '{}' class had been made".format( eeprom.__class__.__name__ ) )

	###
	###	Operation (EEPROM write and read)
	###

	EEPROM_ADDRESS	= 0
	DATA_LENGTH		= 8

	while True:
		data	= [ x for x in range( DATA_LENGTH ) ]
		eeprom.write_data( EEPROM_ADDRESS, data )
		eeprom.wait_write_complete()
		print( eeprom.read_data( EEPROM_ADDRESS, DATA_LENGTH ) )
		sleep( 5 )

DEFAULT_ADDRESS	= 0x28

class SC18IS606( I2C_target ):

	FuncID_SPI_read_and_write		= 0x00
	FuncID_Configure_SPI_Interface	= 0xF0
	FuncID_Clear_Interrupt			= 0xF1
	FuncID_Idle_mode				= 0xF2
	FuncID_GPIO_Write				= 0xF3
	FuncID_GPIO_Read				= 0xF4
	FuncID_GPIO_Enable				= 0xF5
	FuncID_GPIO_Configuration		= 0xF6
	FuncID_Read_Version				= 0xFE

	def __init__( self, i2c, csn, address = DEFAULT_ADDRESS, int = None ):
		super().__init__( i2c, address )
		self.__int	= int
		self.__csn	= csn
		self.__flag	= False
		
		self.__clear_int()

		self.__int.irq( trigger = Pin.IRQ_FALLING, handler = self.__callback )

	def __callback( self, pin ):	#	interrupt handler
		self.__flag	= True

	def __wait_tsfr_done( self, read_wait = False ):
		while self.__flag	== False:
			pass
	
		self.__flag	= False
		
		if read_wait == False:
			self.__clear_int()

	def __clear_int( self ):
		self.command( [ SC18IS606.FuncID_Clear_Interrupt ] )
	
	def command( self, data ):
		super().send( data )

	def send( self, data ):
		self.command( [ SC18IS606.FuncID_SPI_read_and_write | 0x01 << self.__csn ] + data )
		self.__wait_tsfr_done()
		
	def receive( self, data ):
		self.command( [ SC18IS606.FuncID_SPI_read_and_write | 0x01 << self.__csn ] + data )
		self.__wait_tsfr_done( read_wait = True )
		return super().receive( len( data ) )


class AT25010_operation():

	instruction_WRITE	= 0x02
	instruction_READ	= 0x03
	instruction_RDSR	= 0x05	#	read status register
	instruction_WREN	= 0x06	#	write enable
	RDSR_nRDY			= 0x01	#	nRDY bit in RDSR

	def wait_write_complete( self ):
		while self.read_status_register()[ 0 ] & AT25010.RDSR_nRDY:
			pass

	def	read_status_register( self ):
		return self.read( [ AT25010.instruction_RDSR ] + [ 0 ] )[ 1: ]

	def write( self, tsfr ):
		self.send( tsfr )
		
	def read( self, tsfr ):
		return self.receive( tsfr )
	
	def write_data( self, adr, data ):
		self.write( [ AT25010.instruction_WREN ] )
		self.write( [ AT25010.instruction_WRITE, adr ] + data )
	
	def read_data( self, adr, length ):
		return self.read( [ AT25010.instruction_READ, adr ] + [ 0 ] * length )[ 2: ]
		

class AT25010( AT25010_operation, SPI_target ):
	
	def __init__( self, spi, cs ):
		super().__init__( spi, cs )


class AT25010_Br( AT25010_operation, SC18IS606 ):
	
	def __init__( self, i2c, csn, address = DEFAULT_ADDRESS, int = None ):
		super().__init__( i2c, csn, address = address, int = int )

if __name__ == "__main__":
	main()
