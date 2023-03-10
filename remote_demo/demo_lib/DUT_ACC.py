import	machine
import	ure
import	ujson
import	micropython

from	nxp_periph	import	FXOS8700
from	demo_lib	import	DUT_base

class DUT_ACC( DUT_base.DUT_base ):
	APPLIED_TO		= FXOS8700
	TABLE_LENGTH	= 10
	SAMPLE_LENGTH	= 60
	GRAPH_HIGH		= 2
	GRAPH_LOW		= -2

	DS_URL		= { "FXOS8700": "https://www.nxp.com/docs/en/data-sheet/FXOS8700CQ.pdf",
					}

	regex_update	= ure.compile( r".*update=(\d+)" )
	regex_settings	= ure.compile( r".*settings" )

	def __init__( self, dev, timer = 0, sampling_interval = 1.0 ):
		super().__init__( dev )
		
		self.read_ref	= self.__read
		self.data		= []
		self.rtc		= machine.RTC()	#	for timestamping on samples
		self.info		= [ "acc", "" ]
		self.symbol		= '🍎'
		
		self.split		= ( { "id": "Chart0", "unit": "g"  }, 
							{ "id": "Chart1", "unit": "nT" }
							)

	def xyz_data( self ):
		d	= {}
		xyz	= self.dev.xyz()
		mag	= self.dev.mag()
		d[ "x" ] = xyz[ 0 ]
		d[ "y" ] = xyz[ 1 ] 
		d[ "z" ] = xyz[ 2 ]
		d[ "mx" ] = mag[ 0 ]
		d[ "my" ] = mag[ 1 ] 
		d[ "mz" ] = mag[ 2 ]
		tm	= self.rtc.now()
		d[ "time"   ]	= "%02d:%02d:%02d" % (tm[3], tm[4], tm[5])

		return d

	def __read( self, _ ):
		self.data	+= [ self.xyz_data() ]

		over	= len( self.data ) - self.SAMPLE_LENGTH
		if  0 < over:
			self.data	= self.data[ over : ]

		# print( "sampled: {}".format( self.data[ -1 ] ) )

	def parse( self, req ):
		if self.dev_name not in req:
			return None

		if "?" not in req:
			return	self.page_setup()
		else:
			#print( req )
			html	= ""	# dummy

			m	= self.regex_update.match( req )
			if m:
				self.__read( 0 )	# argument is dummy
				return self.sending_data( int( m.group( 1 ) ) )

			m	= self.regex_settings.match( req )
			if m:
				return ujson.dumps( settings )

	def sending_data( self, length ):
		return ujson.dumps( self.data[ -length: ] )

	def page_setup( self ):
		self.page_data[ "symbol"    ]	= self.symbol
		self.page_data[ "table_len" ]	= str( self.TABLE_LENGTH )
		self.page_data[ "tables"     ]	= self.get_tables()
		self.page_data[ "info_tab"  ]	= self.get_info_table()

		self.page_data[ "graph_high"]	= str( self.GRAPH_HIGH )
		self.page_data[ "graph_low" ]	= str( self.GRAPH_LOW  )
		self.page_data[ "max_n_data"]	= str( self.SAMPLE_LENGTH )

		self.page_data[ "charts" ]		= self.get_charts()
		self.page_data[ "split" ]		= self.get_splits()

		return self.load_html()

	def get_charts( self ):
		s	= []
		for d in self.split:
			s	+= [ '<div><canvas id="{}"></canvas></div>'.format( d[ "id" ] ) ]

		return "\n".join( s )

	def get_splits( self ):
		s	= [ "[" ]
		for d in self.split:
			s	+= [ ' "{}",'.format( d[ "id" ] ) ]
		s	+= [ " ]" ]
		return "".join( s )

	def get_tables( self ):
		s	= []
		for d in self.split:
			s	+= [ '<div id="reg_table" class="control_panel reg_table log_panel">' ]
			s	+= [ self.get_tab( d[ "id" ], d[ "unit" ] ) ]
			s	+= [ '</div>' ]
		
		return "\n".join( s )
			
	def get_tab( self, id, unit ):
		s	= [ '<table class="table_TEMP"><tr><td class="td_TEMP">time</td><td class="td_TEMP">x [{0}]</td><td class="td_TEMP">y [{0}]</td><td class="td_TEMP">z [{0}]</td></tr>'.format( unit ) ]

		for i in range( self.TABLE_LENGTH ):
			s	+= [ '<tr>' ]
			s	+= [ '<td class="td_TEMP" text_align="center"><input class="input_text_TMP" type="text" id="{}timeField{}" value = "---"></td>'.format( id, i ) ]
			s	+= [ '<td class="td_TEMP"><input class="input_text_TMP" type="text" id="{}xField{}"></td>'.format( id, i ) ]
			s	+= [ '<td class="td_TEMP"><input class="input_text_TMP" type="text" id="{}yField{}"></td>'.format( id, i ) ]
			s	+= [ '<td class="td_TEMP"><input class="input_text_TMP" type="text" id="{}zField{}"></td>'.format( id, i ) ]
			s	+= [ '</tr>' ]

		s	+= [ '</table>' ]

		return "\n".join( s )

	def get_info_table( self ):
		lb	= [ "start time", "last time", "sample count" ]
		s	= [ '<table class="table_TEMP"><tr>' ]

		for i, l in zip( range( len( lb ) ), lb ):
			s	+= [ '<tr><td class="td_TEMP" text_align="center">{}</td><td class="td_TEMP"><input class="input_text_TMP" type="text" id="infoFieldValue{}"></td></tr>'.format( l, i ) ]

		s	+= [ '</table>' ]

		return "\n".join( s )

settings	= [
					{
						"type": 'line',
						"data": {
							"labels": [],
							"datasets": [
								{
									"label": 'x',
									"data": [],
									"borderColor": "rgba( 255, 0, 0, 1 )",
									"backgroundColor": "rgba( 0, 0, 0, 0 )"
								},
								{
									"label": 'y',
									"data": [],
									"borderColor": "rgba( 0, 255, 0, 1 )",
									"backgroundColor": "rgba( 0, 0, 0, 0 )"
								},
								{
									"label": 'z',
									"data": [],
									"borderColor": "rgba( 0, 0, 255, 1 )",
									"backgroundColor": "rgba( 0, 0, 0, 0 )"
								},
							],
						},
						"options": {
							"animation": False,
							"title": {
								"display": True,
								"text": '"g" now'
							},
							"scales": {
								"yAxes": [{
									"ticks": {
										"suggestedMax": 2.0,
										"suggestedMin": -2.0,
										"stepSize": 1,
										#callback: function(value, index, values){
										#return  value +  ' g'
										#}
									},
									"scaleLabel": {
										"display": True,
										"labelString": 'gravitational acceleration [g]'
									}
								}],
								"xAxes": [{
									"scaleLabel": {
										"display": True,
										"labelString": 'time'
									}
								}]
							},
						}
					},
					{
						"type": 'line',
						"data": {
							"labels": [],
							"datasets": [
								{
									"label": 'x',
									"data": [],
									"borderColor": "rgba( 255, 0, 0, 1 )",
									"backgroundColor": "rgba( 0, 0, 0, 0 )"
								},
								{
									"label": 'y',
									"data": [],
									"borderColor": "rgba( 0, 255, 0, 1 )",
									"backgroundColor": "rgba( 0, 0, 0, 0 )"
								},
								{
									"label": 'z',
									"data": [],
									"borderColor": "rgba( 0, 0, 255, 1 )",
									"backgroundColor": "rgba( 0, 0, 0, 0 )"
								},
							],
						},
						"options": {
							"animation": False,
							"title": {
								"display": True,
								"text": '"mag" now'
							},
							"scales": {
								"yAxes": [{
									"ticks": {
										#callback: function(value, index, values){
										#return  value +  ' nT'
										#}
									},
									"scaleLabel": {
										"display": True,
										"labelString": 'geomagnetism [nT]'
									}
								}],
								"xAxes": [{
									"scaleLabel": {
										"display": True,
										"labelString": 'time'
									}
								}]
							},
						}
					}
]

print(settings)
