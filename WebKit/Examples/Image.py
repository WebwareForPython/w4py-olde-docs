from WebKit.HTTPContent import HTTPContent
try:
	import gd
except ImportError:
	gd = None
 
class Image(HTTPContent):
	"""
	Dynamic image generation example.
	For more information on generating graphics, see
	http://python.org/topics/web/graphics.html.
	"""
	def defaultAction(self):
		if not gd:
			self.write('''
				Sorry: this page requires the Python GD module.
				See http://python.org/topics/web/graphics.html.
				''')
			return
		image = self.generatePNGImage()
		res = self.response()
		res.setHeader("Content-Type", "image/png")
		res.setHeader("Content-Length", str(len(image)))
		# Uncomment the following to suggest to the client
		# that the result should be saved to a file,
		# rather than displayed in-line:
		# fname = 'foo.png'
		# res.setHeader('Content-Disposition', 'attachment; filename=%s' % fname)
		self.write(image)

	def generatePNGImage(self):
		"""
		Generate and return a PNG image, using "gdmodule".
		"""
		import StringIO
		from math import sin, pi
		X,Y = (200,100)
		im = gd.image((X,Y))
		white = im.colorAllocate((255, 255, 255))
		black = im.colorAllocate((0, 0, 0))
		blue = im.colorAllocate((0, 0, 255))
		im.colorTransparent(white)
		im.string(gd.gdFontLarge, (int(X*.6), 0), "y=sin(x)", black)
		# map co-ordinates: (x=0..2pi,y=-1..1) => (0..X,Y..0)
		def T(x,y):
			return (int((x/(2*pi))*X), int(Y - ((y+1)/2.0)*Y))
		im.line(T(0,0), T(2*pi,0), black)  # x-axis
		im.line(T(0,-1), T(0,1), black)	# y-axis
		points = []
		x = 0
		while x < 2*pi:
			points.append(T(x,sin(x)))
			x += 0.1
		im.lines(points, blue)
		f = StringIO.StringIO()
		im.writePng(f)
		return f.getvalue()
