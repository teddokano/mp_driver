#	MicroPython HTTP server sample code based on "http_server_simplistic.py".
#	https://github.com/micropython/micropython/blob/master/examples/network/http_server_simplistic.py
#
#	Tedd OKANO / Released under the MIT license
#	22-Oct-2022
#	version	0.1
#
# https://www.sejuku.net/blog/25316
# https://micropython-docs-ja.readthedocs.io/ja/v1.10ja/library/ujson.html
# https://qiita.com/otsukayuhi/items/31ee9a761ce3b978c87a
# https://products.sint.co.jp/topsic/blog/json
# https://rintama.net/%EF%BD%8A%EF%BD%81%EF%BD%96%EF%BD%81%EF%BD%93%EF%BD%83%EF%BD%92%EF%BD%89%EF%BD%90%EF%BD%94%E3%81%A7%E4%BD%9C%E6%88%90%E3%81%97%E3%81%9F%E9%85%8D%E5%88%97%E3%82%92%EF%BD%83%EF%BD%93%EF%BD%96%E3%81%A7/

import	machine
import	ure
import	ujson

from	nxp_periph	import	PCT2075, LM75B
from	nxp_periph	import	temp_sensor_base
import	demo_lib.utils	as utils

class DUT_TEMP():
	APPLIED_TO		= temp_sensor_base
	TABLE_LENGTH	= 10
	SAMPLE_LENGTH	= 10
	GRAPH_HIGH		= 30
	GRAPH_LOW		= 20

	DS_URL		= { "PCT2075": "https://www.nxp.com/docs/en/data-sheet/PCT2075.pdf",
					"LM75B": "https://www.nxp.com/docs/en/data-sheet/LM75B.pdf",
					}

	regex_thresh	= ure.compile( r".*tos=(\d+\.\d+)&thyst=(\d+\.\d+)" )
	regex_heater	= ure.compile( r".*heater=(\d+)" )
	regex_mode		= ure.compile( r".*os_polarity=(\d+)&os_mode=(\d+)" )

	def __init__( self, dev, timer = 0, sampling_interbal = 1.0 ):
		self.interface	= dev.__if
		self.dev		= dev
		self.type		= self.dev.__class__.__name__
		self.address	= dev.__adr
		self.dev_name	= self.type + "_on_I2C(0x%02X)" % (dev.__adr << 1)
		self.data		= { "time": [], "temp": [], "tos": [], "thyst": [], "os": [], "heater": [] }
		self.rtc		= machine.RTC()	#	for timestamping on samples
		self.info		= [ "temp sensor", "" ]
		self.symbol		= '🌡️'

		if self.dev.ping():
			tp	= self.dev.temp
		else:
			tp	= 25	#	default value when device is not responding
			
		self.tos		= int( (tp + 2) * 2 ) / 2
		self.thyst		= int( (tp + 1) * 2 ) / 2

		self.dev.temp_setting( [ self.tos, self.thyst ] )

		self.int_pin	= machine.Pin( "D2", machine.Pin.IN  )
		self.dev.heater	= 0

		if self.dev.live:
			tim0	= machine.Timer( timer )
			tim0.init( period = int( sampling_interbal * 1000.0 ), callback = self.tim_cb )

	def tim_cb( self, tim_obj ):
		tp	= self.dev.temp
		tm	= self.rtc.now()
		self.data[ "time"   ]	+= [ "%02d:%02d:%02d" % (tm[3], tm[4], tm[5]) ]
		self.data[ "temp"   ]	+= [ tp ]
		self.data[ "tos"    ]	+= [ self.tos ]
		self.data[ "thyst"  ]	+= [ self.thyst ]
		self.data[ "os"     ]	+= [ self.GRAPH_HIGH if self.int_pin.value() else self.GRAPH_LOW ]
		self.data[ "heater" ]	+= [ self.GRAPH_HIGH if self.dev.heater      else self.GRAPH_LOW ]

		over	= len( self.data[ "time" ] ) - self.SAMPLE_LENGTH
		if  0 < over:
			self.data[ "time"   ]	= self.data[ "time"   ][ over : ]
			self.data[ "temp"   ]	= self.data[ "temp"   ][ over : ]
			self.data[ "tos"    ]	= self.data[ "tos"    ][ over : ]
			self.data[ "thyst"  ]	= self.data[ "thyst"  ][ over : ]
			self.data[ "os"     ]	= self.data[ "os"     ][ over : ]
			self.data[ "heater" ]	= self.data[ "heater" ][ over : ]

		#print( "sampled: {} @ {}".format( tp, tm ) )

	def parse( self, req ):
		if self.dev_name not in req:
			return None

		if "?" not in req:
			html	= self.page_setup()
		elif "update" in req:
				html	= self.sending_data()
		else:
			print( req )
			html	= 'HTTP/1.0 200 OK\n\n'	# dummy

			m	= self.regex_thresh.match( req )
			if m:
				self.tos	= float( m.group( 1 ) )
				self.thyst	= float( m.group( 2 ) )
				self.dev.temp_setting( [ self.tos, self.thyst ] )
				print( "********** THRESHOLDS {} {} **********".format( self.tos, self.thyst ) )

			m	= self.regex_heater.match( req )
			if m:
				val	= int( m.group( 1 ) )
				self.dev.heater	= val
				print( "********** {} HEATER {} **********".format( self.type, "ON" if val else "OFF" ) )

			m	= self.regex_mode.match( req )
			if m:
				pol	= int( m.group( 1 ) )
				mod	= int( m.group( 2 ) )
				self.dev.bit_operation( "Conf", 0x06, (pol << 2) | (mod << 1) )

				print( "********** CONFIGURATION {} {} **********".format( "Active_HIGH" if pol else "Active_Low", "Interrupt" if mod else "Comparator" ) )

		return html

	def sending_data( self ):
		s	 = [ 'HTTP/1.0 200 OK\n\n' ]
		s	+= [ ujson.dumps( { "data": self.data } ) ]

		return "".join( s )

	def page_setup( self ):
		html	= "HTTP/1.0 200 OK\n\n{% html %}"

		page_data	= {}
		page_data[ "dev_name"  ]	= self.dev_name
		page_data[ "dev_type"  ]	= self.type
		page_data[ "dev_link"  ]	= '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>'.format( self.DS_URL[ self.type ], self.type )
		page_data[ "symbol"    ]	= self.symbol
		page_data[ "dev_info"  ]	= self.dev.info()
		page_data[ "table_len" ]	= str( self.TABLE_LENGTH )
		page_data[ "signature" ]	= utils.page_signature()
		page_data[ "table"     ]	= self.get_table()
		page_data[ "info_tab"  ]	= self.get_info_table()

		page_data[ "graph_high"]	= str( self.GRAPH_HIGH )
		page_data[ "graph_low" ]	= str( self.GRAPH_LOW  )
		page_data[ "tos_init"  ]	= str( self.tos   )
		page_data[ "thyst_init"]	= str( self.thyst )

		#	using list instead of dict because current MicroPython's dict cannot keep key order
		files	= [ [ 	"html", 	"demo_lib/" + self.__class__.__name__	],
					[	"css", 		"demo_lib/general"						],
					[	"js",		"demo_lib/general",
									"demo_lib/" + self.__class__.__name__ 	]
				  ]

		html	= utils.file_loading( html, files )
		
		for key, value in page_data.items():
			html = html.replace('{% ' + key + ' %}', value )
		
		return html

	def get_table( self ):
		s	= [ '<table class="table_TEMP"><tr><td class="td_TEMP">time</td><td class="td_TEMP">temp [˚C]</td></tr>' ]

		for i in range( self.TABLE_LENGTH ):
			s	+= [ '<tr><td class="td_TEMP" text_align="center"><input class="input_text_TMP" type="text" id="timeField{}" value = "---"></td><td class="td_TEMP"><input class="input_text_TMP" type="text" id="tempField{}"></td></tr>'.format( i, i ) ]

		s	+= [ '</table>' ]

		return "\n".join( s )

	def get_info_table( self ):
		lb	= [ "start time", "last time", "sample count" ]
		s	= [ '<table class="table_TEMP"><tr>' ]

		for i, l in zip( range( len( lb ) ), lb ):
			s	+= [ '<tr><td class="td_TEMP" text_align="center">{}</td><td class="td_TEMP"><input class="input_text_TMP" type="text" id="infoFieldValue{}"></td></tr>'.format( l, i ) ]

		s	+= [ '</table>' ]

		return "\n".join( s )
