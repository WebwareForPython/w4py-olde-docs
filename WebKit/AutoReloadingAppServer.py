#!/usr/bin/env python

"""AutoReloadingAppServer

This module defines `AutoReloadingAppServer`, a replacement for `AppServer`
that adds a file-monitoring and restarting to the AppServer. Used mostly like:

    from AutoReloadingAppServer import AutoReloadingAppServer as AppServer

If `UseImportSpy` is set to False in AppServer.config, or FAM support is
not available, this requires regular polling. The interval for the polling
in seconds can be set with `AutoReloadPollInterval` in AppServer.config.

"""

import select
from threading import Thread

from Common import *
from AppServer import AppServer


defaultConfig = {
	'AutoReload': False,
	'AutoReloadPollInterval': 1, # in seconds
	'UseImportSpy': True,
	'UseFAMModules': 'gamin _fam',
}


def fam(modules):
	"""Get FAM object based on the modules specified.

	Currently supported are
	python-gamin (gamin): http://www.gnome.org/~veillard/gamin/
	python-fam (_fam): http://python-fam.sourceforge.net

	"""
	for module in modules:
		try:
			fam = __import__(module)
		except ImportError:
			fam = None
		if not fam:
			continue
		if hasattr(fam, 'GAM_CONNECT') and hasattr(
				fam, 'WatchMonitor') and hasattr(fam, 'GAMChanged'):


			class FAM:
				"""Simple File Alteration Monitor based on python-gamin"""

				def name(self):
					return "python-gamin"

				def __init__(self):
					"""Initialize and start monitoring."""
					self._mon = fam.WatchMonitor()
					self._watchlist = []

				def close(self):
					"""Stop monitoring and close."""
					for filepath in self._watchlist:
						self._mon.stop_watch(filepath)
					del self._mon

				def fd(self):
					"""Get file descriptor for monitor."""
					return self._mon.get_fd()

				def monitorFile(self, filepath):
					"""Monitor one file."""
					self._mon.watch_file(filepath, self.callback)
					self._watchlist.append(filepath)

				def pending(self):
					"""Check whether an event is pending."""
					return self._mon.event_pending()

				def nextFile(self):
					"""Get next file and return whether it has changed."""
					self._mon.handle_one_event()
					return self._changed, self._filepath

				def callback(self, filepath, event):
					"""Callback function for WatchMonitor."""
					self._filepath = filepath
					self._changed = {fam.GAMChanged: 'changed',
						fam.GAMCreated: 'created', fam.GAMMoved: 'moved',
						fam.GAMDeleted: 'deleted'}.get(event)

			break
		elif hasattr(fam, 'FAMConnection') and hasattr(
				fam, 'open') and hasattr(fam, 'Changed'):


			class FAM:
				"""Simple File Alteration Monitor based on python-fam"""

				def name(self):
					return "python-fam"

				def __init__(self):
					"""Initialize and start monitoring."""
					self._fc = fam.open()
					self._requests = []

				def close(self):
					"""Stop monitoring and close."""
					for request in self._requests:
						request.cancelMonitor()
					self._fc.close()
					del self._fc

				def fd(self):
					"""Get file descriptor for monitor."""
					return self._fc

				def monitorFile(self, filepath):
					"""Monitor one file."""
					self._requests.append(self._fc.monitorFile(filepath, None))

				def pending(self):
					"""Check whether an event is pending."""
					return self._fc.pending()

				def nextFile(self):
					"""Get next file and return whether it has changed."""
					event = self._fc.nextEvent()
					# we can also use event.code2str() here,
					# but then we need to filter the events
					changed = {fam.Changed: 'changed',
						fam.Created: 'created', fam.Moved: 'moved',
						fam.Deleted: 'deleted'}.get(event.code)
					return changed, event.filename

			break
	else:
		FAM = None
	if FAM:
		return FAM()


class AutoReloadingAppServer(AppServer):
	"""AppServer AutoReloading.

	This class adds functionality to `AppServer`, to notice changes to
	source files, including servlets, PSPs, templates or changes to the
	Webware source file themselves, and reload the server as necessary
	to pick up the changes.

	The server will also be restarted if a file which Webware *tried*
	to import is modified. This is so that changes to a file containing
	a syntax error (which would have prevented it from being imported)
	will also cause the server to restart.

	"""


	## Init ##

	def __init__(self, path=None):
		"""Activate AutoReloading."""
		AppServer.__init__(self, path)
		self._autoReload = False
		self._shouldRestart = False
		self._famModules = self.setting('UseFAMModules')
		try:
			self._famModules = self._famModules.split()
		except AttributeError:
			pass
		if self.isPersistent():
			if self.setting('AutoReload'):
				self.activateAutoReload()

	def defaultConfig(self):
		"""Return the default configuration."""
		conf = AppServer.defaultConfig(self)
		# Update with AutoReloadingAppServer specific settings
		# as defined in defaultConfig on the module level:
		conf.update(defaultConfig)
		return conf

	def shutDown(self):
		"""Shut down the monitoring thread.

		This is done in addition to the normal shutdown procedure.

		"""
		print 'Stopping AutoReload Monitor...'
		sys.stdout.flush()
		self._running = 1
		self.deactivateAutoReload()
		AppServer.shutDown(self)
		sys.stdout.flush()
		sys.stderr.flush()
		self._running = 0


	## Activation of AutoReload ##

	def activateAutoReload(self):
		"""Start the monitor thread."""
		if self.setting('UseImportSpy'):
			s = self._imp.activateImportSpy()
			print 'ImportSpy activated (using %s).' % s
		if not self._autoReload:
			if self._famModules and self._imp._spy:
				# FAM will be only used when ImportSpy has been activated,
				# since otherwise we need to poll the modules anyway.
				self._pipe = None
				try:
					self._fam = fam(self._famModules)
				except Exception, e:
					print "Error loading FAM:", str(e)
					self._fam = None
				if self._fam:
					print 'FAM not available, fall back to polling.'
			print 'AutoReload Monitor started,',
			if self._fam:
				print 'using %s.' % self._fam.name()
				target = self.fileMonitorThreadLoopFAM
			else:
				self._pollInterval = self.setting('AutoReloadPollInterval')
				print 'polling every %d seconds.' % self._pollInterval
				target = self.fileMonitorThreadLoop
			self._fileMonitorThread = t = Thread(target=target)
			self._autoReload = True
			t.setName('AutoReloadMonitor')
			t.start()

	def deactivateAutoReload(self):
		"""Tell the monitor thread to stop.

		This should be considered as a request, not a demand.

		"""
		self._autoReload = False
		if self._fam and self._pipe:
			# Send a message down the pipe to wake up the monitor thread
			# and tell him to quit.
			self._pipe[1].write('close')
			self._pipe[1].flush()
		try:
			self._fileMonitorThread.join()
		except Exception:
			pass


	## Restart methods ##

	def restartIfNecessary(self):
		"""Check if the app server should be restarted.

		This should be called regularly to see if a restart is required.
		The server can only restart from the main thread, other threads
		can't do the restart. So this polls to see if `shouldRestart`
		has been called.

		"""
		# Tavis Rudd claims: "this method can only be called by
		# the main thread.  If a worker thread calls it, the
		# process will freeze up."
		#
		# I've implemented it so that the ThreadedAppServer's
		# control thread calls this. That thread is _not_ the
		# MainThread (the initial thread created by the Python
		# interpreter), but I've never encountered any problems.
		# Most likely Tavis meant a freeze would occur if a
		# _worker_ called this.
		if self._shouldRestart:
			self.restart()

	def restart(self):
		"""Do the actual restart.

		Call `shouldRestart` from outside the class.

		"""
		sys.stdout.flush()
		sys.stderr.flush()
		# calling execve() is problematic, since the file
		# descriptors don't get closed by the OS.  This can
		# result in leaked database connections.  Instead, we
		# exit with a special return code which is recognized
		# by the AppServer script, which will restart us upon
		# receiving that code.
		sys.exit(3)

	def monitorNewModule(self, filepath, mtime=None):
		"""Add new file to be monitored.

		This is a callback which ImportSpy invokes to notify us of new files
		to monitor. This is only used when we are using FAM.

		"""
		self._fam.monitorFile(os.path.abspath(filepath))


	## Internal methods ##

	def shouldRestart(self):
		"""Tell the main thread to restart the server."""
		if self._fam:
			self._fam.close()
		self._autoReload = False
		self._shouldRestart = True

	def fileMonitorThreadLoop(self):
		"""This the the main loop for the monitoring thread.

		Runs in its own thread, polling the files for changes directly
		(i.e., going through every file that's being used and checking
		its last-modified time, seeing if it's been changed since it
		was initially loaded).

		"""
		while self._autoReload:
			time.sleep(self._pollInterval)
			f = self._imp.updatedFile()
			if f:
				print '*** The file', f, 'has changed.'
				print 'The app server is restarting now...'
				self.shouldRestart()
				return
		print 'Autoreload Monitor stopped.'
		sys.stdout.flush()

	def fileMonitorThreadLoopFAM(self, getmtime=os.path.getmtime):
		"""Monitoring thread loop, but using the FAM library."""
		self._pipe = None
		# For all of the modules which have _already_ been loaded,
		# we check to see if they've already been modified:
		f = self._imp.updatedFile()
		if f:
			print '*** The file', f, 'has changed.'
			print 'The app server is restarting now...'
			self.shouldRestart()
			return
		for f in self._imp.fileList():
			self.monitorNewModule(f)
		self._imp.notifyOfNewFiles(self.monitorNewModule)
		# Create a pipe so that this thread can be notified when the
		# server is shutdown. We use a pipe because it needs to be an object
		# which will wake up the call to 'select':
		r, w = os.pipe()
		self._pipe = r, w = os.fdopen(r, 'r'), os.fdopen(w, 'w')
		fam = self._fam
		fd = fam.fd()
		while self._autoReload:
			try:
				# We block here until a file has been changed, or until
				# we receive word that we should shutdown (via the pipe).
				ri, ro, re = select.select([fd, r], [], [])
			except select.error, er:
				errnumber, strerr = er
				if errnumber == errno.EINTR:
					continue
				else:
					print strerr
					sys.exit(1)
			while fam.pending():
				c, f = fam.nextFile()
				if c and self._imp.fileUpdated(f):
					print '*** The file %s has been %s.' % (f, c)
					print 'The app server is restarting now...'
					self.shouldRestart()
					return
		self._imp.notifyOfNewFiles(None)
		self._pipe = None
		fam.close()
		print 'Autoreload Monitor stopped'
		sys.stdout.flush()
