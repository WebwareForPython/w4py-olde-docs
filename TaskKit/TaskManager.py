# Based on code from Jonathan Abbey, jonabbey@arlut.utexas.edu
# from the Ganymede Directory Management System
# Python port and enhancements by Tom.Schwaller@linux-community.de

# from Manager import Manager
# from Common import SubclassResponsibilityError

__version__ = '0.1'

from threading import Thread, Event
from time import time, sleep


class Scheduler(Thread):

	
	## Init ##

	def __init__(self):
		Thread.__init__(self)
		self._closeEvent = Event()
		self._notifyEvent = Event()
		self._nextTime = None
		self._scheduled = {}
		self._running = {}
		self._onDemand = {}
		self._isRunning = 0


	## Event Methods ##

	def closeEvent(self):
		return self._closeEvent
		
	def wait(self, seconds=None):
		self._notifyEvent.wait(seconds)
		self._notifyEvent.clear()


	## Value Methods ##
	
	def running(self, name, default=None):
		return self._running.get(name, default)

	def hasRunning(self, name):
		return self._running.has_key(name)
      
	def setRunning(self, handle):      
		self._running[handle.name()] = handle
		
	def delRunning(self, name):
		try:
			handle = self._running[name]
			del self._running[name]
			return handle
		except:
			return None
		
	def scheduled(self, name, default=None):
		return self._scheduled.get(name, default)

	def hasScheduled(self, name):
		return self._scheduled.has_key(name)
      
	def setScheduled(self, handle):      
		self._scheduled[handle.name()] = handle

	def delScheduled(self, name):
		try:
			handle = self._scheduled[name]
			del self._scheduled[name]
			return handle
		except:
			return None
				
	def onDemand(self, name, default=None):
		return self._onDemand.get(name, default)

	def hasOnDemand(self, name):
		return self._onDemand.has_key(name)
      
	def setOnDemand(self, handle):      
		self._onDemand[handle.name()] = handle

	def delOnDemand(self, name):
		try:
			handle = self._onDemand[name]
			del self._onDemand[name]
			return handle
		except:
			return None
			
	def nextTime(self):
		return self._nextTime
		
	def setNextTime(self, time):
		self._nextTime = time
		
	def isRunning(self):
		return self._isRunning

		
	## Adding Tasks ##
	
	def addTimedAction(self, time, task, name):
		handle = self.unregisterTask(name)
		if not handle:
			handle = ScheduleHandle(self, time, 0, task, name)
		else:
			handle.reset(time, 0, task, 1)
		self.scheduleTask(handle)
		
	def addActionOnDemand(self, task, name):
		handle = self.unregisterTask(name)
		if not handle:
			handle = ScheduleHandle(self, time(), 0, task, name)
		else:
			handle.reset(time(), 0, task, 1)	
		self.setOnDemand(handle)
		
	def addDailyAction(self, hour, minute, task, name):
		"""
		Can we make this addCalendarAction?  What if we want to run something once a week?
		We probably don't need that for Webware, but this is a more generally useful module.
		This could be a difficult function, though.  Particularly without mxDateTime.
		"""
		import time
		current = time.localtime(time.time())
		currhour = current[3]
		currmin = current[4]

		#minute_difference
		if minute > currmin:
			minute_difference = minute - currmin
		elif minute < currmin:
			minute_difference = 60 - currmin + minute
		else: #equal
			minute_difference = 0

		#hour_difference
		if hour > currhour:
			hour_difference = hour - currhour
		elif hour < currhour:
			hour_difference = 24 - currhour + hour
		else: #equal
			hour_difference = 0

		delay = (minute_difference + (hour_difference * 60)) * 60

		print "daily task %s scheduled for %s seconds" % (name,delay)

		self.addPeriodicAction(time.time()+delay, 24*60*60, task, name)

		
	def addPeriodicAction(self, start, period, task, name):
		handle = self.unregisterTask(name)
		if not handle:
			handle = ScheduleHandle(self, start, period, task, name)
		else:
			handle.reset(start, period, task, 1)
		self.scheduleTask(handle)
		

	## Task methods ##
					
	def unregisterTask(self, name):
		handle = None
		if self.hasScheduled(name):
			handle = self.delScheduled(name)
		if self.hasOnDemand(name):
			handle = self.delOnDemand(name)
		if handle:
			handle.unregister()
		return handle
	
	def runTaskNow(self, name):
		if self.hasRunning(name):
			return 1
		handle = self.scheduled(name)
		if not handle:
			handle = self.onDemand(name)
		if not handle:
			return 0					
		self.runTask(handle)
		return 1
		
	def demandTask(self, name): pass
	
	def stopTask(self, name):
		handle = self.running(name)
		if not handle: return 0
		handle.stop()
		return 1
	
	def disableTask(self, name):
		handle = self.running(name)
		if not handle:
			handle = self.scheduled(name)
		if not handle:
			return 0
		handle.disable()
		return 1	

	def enableTask(self, name):
		handle = self.running(name)
		if not handle:
			handle = self.scheduled(name)
		if not handle:
			return 0
		handle.enable()
		return 1	
			
	def runTask(self, handle):
		name = handle.name()
		if self.delScheduled(name) or self.delOnDemand(name):
			self.setRunning(handle)
			handle.runTask()

	def scheduleTask(self, handle):
		self.setScheduled(handle)
		if not self.nextTime() or handle.startTime() < self.nextTime():
			self.setNextTime(handle.startTime())
			self.notify()


	## Misc Methods ##
								
	def notifyCompletion(self, handle):
		name = handle.name()
		if self.hasRunning(name):
			self.delRunning(name)
			if handle.startTime() and handle.startTime() > time():
				self.scheduleTask(handle)
			else:
				if handle.reschedule():
					self.scheduleTask(handle)
				elif not handle.startTime():	
					self.setOnDemand(handle)		
					if handle.runAgain():
						self.runTask(handle)
						
	def notify(self):
		self._notifyEvent.set()

	def stop(self):
		self._isRunning = 0
		self.notify()
		self._closeEvent.set()
	
	
	## Main Method ##
									
	def run(self): 
		self._isRunning = 1
		while 1:
			if not self._isRunning:
				return
			if not self.nextTime():
				self.wait()
			else:
				nextTime = self.nextTime()
				currentTime = time()
				if currentTime < nextTime:
					sleepTime = nextTime - currentTime
					self.wait(sleepTime)
				currentTime = time()
				if currentTime >= nextTime:
					toRun = []
					nextRun = None
					for handle in self._scheduled.values():
						startTime = handle.startTime()
						if startTime <= currentTime:
							toRun.append(handle)
						else:
							if not nextRun:
								nextRun = startTime
							elif startTime < nextRun:
								nextRun = startTime
					self.setNextTime(nextRun)
					for handle in toRun:
						self.runTask(handle)
			
					
class ScheduleHandle:
	
	
	## Init ##
	
	def __init__(self, scheduler, start, period, task, name):
		self._scheduler = scheduler
		self._task = task
		self._name = name
		self._thread = None
		self._isRunning = 0
		self._suspend = 0
		self._lastTime = None
		self._startTime = start
		self._registerTime = time()
		self._reregister = 1
		self._rerun = 0
		self._period = abs(period)
		self._stopEvent = Event()

	def reset(self, start, period, task, reregister):
		self._startTime = start
		self._period = abs(period)
		self._task = task
		self._reregister = reregister		
				
	def runTask(self):
		if self._suspend:
			self._scheduler.notifyCompletion(self)
			return
		self._rerurn = 0
		self._thread = Thread(None, self._task._run, self.name(), (self,))
		self._thread.start()
		self._isRunning = 1
		
	def reschedule(self):
		if self._period == 0:
			return 0
		else:
			if self._lastTime - self._startTime > self._period:  #if the time taken to run the task exceeds the period
				self._startTime = self._lastTime + self._period
			else:
				self._startTime = self._startTime + self._period
			return 1
			
	def runAgain(self):
		return self._rerun
	
	def isOnDemand(self):
		return self._period == 1
		
	def runOnCompletion(self):
		self._rerun = 1
	
	def unregister(self):
		self._reregister = 0
		self._rerun = 0
	
	def disable(self):
		self._suspend = 1
		
	def enable(self):
		self._suspend = 0

	def period(self):
		return self._period
		
	def setPeriod(self, period):
		self._period = period
		
	def notifyCompletion(self):
		self._isRunning = 0
		self._lastTime = time()
		self._scheduler.notifyCompletion(self)
		
	def stop(self):
		self._isRunning = 0
		
	def name(self):
		return self._name
	
	def closeEvent(self):
		return self._scheduler.closeEvent()
	
	def startTime(self, newTime=None):
		if newTime:
			self._startTime = newTime
		return self._startTime
					
		
class Task:	
	def run(self, close):
		raise SubclassResponsibilityError

	def handle(self):
		return self._handle

	def proceed(self):
		"""
		Should this task continue running?
		Should be called periodically by long tasks to check if the system wants them to exit.
		returns 1 if its OK to continue, 0 if its time to quit
		"""
		return not( self._close.isSet() or (not self._handle._isRunning))
	
	def _run(self, handle):
		self._name = handle.name()
		self._handle = handle
		self._close = handle.closeEvent()
		self.run(self._close)
		handle.notifyCompletion()
		
	def name(self):
		return self._name
		
				
class SimpleTask(Task):
	def run(self, close):
		if self.proceed():
			print self.name(), time()
			#sleep(4)
##			print "Increasing period"
##			self.handle().setPeriod(self.handle().period()+2)
		else:
			print "Should not proceed"
				
if __name__=='__main__':
	from time import localtime
	scheduler = Scheduler()
	scheduler.start()
	scheduler.addPeriodicAction(time(), 2, SimpleTask(), 'SimpleTask1')
	scheduler.addTimedAction(time()+5, SimpleTask(), 'SimpleTask2')
	scheduler.addActionOnDemand(SimpleTask(), 'SimpleTask3')
	scheduler.addDailyAction(localtime(time())[3], localtime(time())[4]+1, SimpleTask(), "DailyTask")
	sleep(70)
	print "Demanding SimpleTask3"
	scheduler.runTaskNow('SimpleTask3')
	sleep(1)
	print "Calling stop"
	scheduler.stop()
	print "Test Complete"
