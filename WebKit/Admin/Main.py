from time import time, localtime, gmtime, asctime
from AdminPage import AdminPage
import os


class Main(AdminPage):

	def title(self):
		return 'Admin'

	def writeContent(self):
		self.writeGeneralInfo()
		self.writeSignature()

	def writeGeneralInfo(self):
		app = self.application()
		curTime = time()
		info = [
			('Webware Version', app.webwareVersion()),
			('WebKit Version',  app.webKitVersion()),
			('Local Time',      asctime(localtime(curTime))),
			('Up Since',        asctime(localtime(app.server().startTime()))),
			('Num Requests',    app.server().numRequests()),
			('Working Dir',     os.getcwd()),
		]

		self.writeln('<table align=center cellspacing=0 cellpadding=0 border=0>')
		for label, value in info:
			self.writeln('<tr> <td> <b>%s:</b> </td> <td>%s</td> </tr>' % (label, value))
		self.writeln('</table>')

	def writeSignature(self):
		app = self.application()
		curTime = time()
		self.writeln('''
<!--
begin-parse
{
	'Version': %s,
	'LocalTime': %s,
	'GlobalTime': %s
}
end-parse
-->''' % (repr(app.webKitVersion()), repr(localtime(curTime)), repr(gmtime(curTime))))
