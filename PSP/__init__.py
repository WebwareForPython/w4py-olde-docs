# PSP
# Webware for Python


from PSPServletFactory import PSPServletFactory


def InstallInWebKit(appServer):
	app = appServer.application()
	app.addServletFactory(PSPServletFactory(app))
	app._Contexts['PSPExamples']='../PSP/Examples'
