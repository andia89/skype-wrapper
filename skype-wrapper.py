#!/usr/bin/python

from gi.repository import MessagingMenu
from gi.repository import GObject, GLib
from gi.repository import Gio
from gi.repository import Notify
import Skype4Py
import threading
import time
import os
from gettext import lgettext as _
import sys, os, errno, tempfile, unittest, logging
from multiprocessing import Process
import subprocess
import socket
from operator import itemgetter

show_messages = True

status_conv = {'ONLINE':MessagingMenu.Status.AVAILABLE, 'AWAY':MessagingMenu.Status.AWAY, 'DND':MessagingMenu.Status.BUSY, 'INVISIBLE':MessagingMenu.Status.INVISIBLE, 'OFFLINE':MessagingMenu.Status.OFFLINE}
status2_conv = {0:'ONLINE', 1:'AWAY', 2:'DND', 3:'INVISIBLE', 4:'OFFLINE'}


def get_lock(process_name):
    global lock_socket
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_socket.bind('\0' + process_name)
        print 'I got the lock'
        return True
    except socket.error:
        print 'skype-wrapper already running'
        return False


class SkypeIndicator():

    def __init__(self):
        Notify.init(app_name = 'skype-wrapper')
        self.notification = Notify.Notification.new("skype", "skype", 'skype')
        self.missed = []
        self.skype = Skype4Py.Skype()
        self.loadSkype()
        self.mmapp = MessagingMenu.App.new ("skype.desktop")
        self.mmapp.register()
        stat = self.skype.CurrentUserStatus
        self.mmapp.set_status(status_conv[stat])
        
        self.mmapp.connect("activate-source", self.activated)
        self.mmapp.connect('status-changed', self._on_set_status)
        self.counter1 = 0
        self.dicti = {}
        self.dicti_m = {}
        self.control = False
        self.control2 = True
        self.change_status = False
        self.last_sender = ''

    def set_indicator(self):
        t1 = threading.Thread(target=self.check)
        t1.start()
        if not self.control:
            return True
        dicti = {}
        dicti_sent = {}
        sender = []
        last_sender = self.last_sender
        counter = 0
        if self.missed:
            for i, m in enumerate(self.missed):
                if i == 0:
                    sender.append(m.FromDisplayName)
                    dicti["message"+str(counter)] = [(m.Datetime, m.FromDisplayName, m.FromHandle, m.Body)]
                elif m.FromDisplayName not in sender:
                    sender.append(m.FromDisplayName)
                    dicti["message"+str(counter)] = [(m.Datetime, m.FromDisplayName, m.FromHandle, m.Body)]
                else:
                    dicti["message"+str(counter)].append((m.Datetime, m.FromDisplayName, m.FromHandle, m.Body))
                counter = len(sender)-1
            #print self.dicti
            for sen in self.dicti_m:
                if not sen in sender:
                    del self.dicti_m[sen]
            
            for d in dicti:
                message_head = dicti[d][0][1]
                message_body = ''
                sort_d = sorted(dicti[d], key=itemgetter(0))
                print sort_d
                for l,body in enumerate(sort_d):
                    
                    if (l+1) != len(dicti[d]):
                        message_body += body[3]+'\n'
                    else:
                        message_body += body[3]
                #print message_body
                
                try:
                    if self.dicti_m[message_head][0] == message_body:
                            self.dicti_m[message_head] = [message_body, False]
                    else:
                            self.dicti_m[message_head] = [message_body, True]
                except KeyError as e:
                    self.dicti_m[message_head] = [message_body, True]

            if last_sender in self.dicti_m:
                if self.dicti_m[last_sender][1]:
                    self.notification.update(last_sender, self.dicti_m[last_sender][0], 'skype')
                    self.notification.show()
                for sen in self.dicti_m:
                    if self.dicti_m[sen][1]:
                        if sen != last_sender:
                            self.notification = Notify.Notification.new(sen, self.dicti_m[sen][0], 'skype')
                            self.notification.show()
                        self.last_sender = sen
            else:
                for sen in self.dicti_m:
                    #print sen
                    if self.dicti_m[sen][1]:
                        self.notification = Notify.Notification.new(sen, self.dicti_m[sen][0], 'skype')
                        self.notification.show()
                        self.last_sender = sen           
                
                    
            for d in dicti:
                if not self.mmapp.has_source(_(d)):
                    self.mmapp.append_source_with_count (_(d), None, dicti[d][0][1], 0)
                    self.mmapp.set_source_count(_(d), len(dicti[d]))
                    self.counter1 = len(dicti[d])
                    self.mmapp.draw_attention (_(d))
                if self.counter1 != len(dicti[d]):
                    self.mmapp.set_source_count(_(d),len(dicti[d]))
                    self.counter1 = len(dicti[d])
	elif not self.missed:
		for i in range(self.counter1):
			try:
				self.mmapp.remove_source(_('message'+str(i)))
			except:
				pass
        #self.dicti_m = {}
        #self.last_sender = ''
        self.dicti = dicti
        self.control = False
        self.control2 = True
        #print self.dicti_m
        return True
    
    def activated (self, mmapp, source):
        try:
            self.skype.Client.OpenMessageDialog(self.dicti[source][0][2])
        except:
            pass #weird error catched here

    def loadSkype(self):
        counter = 0	
        while True:
            if self.skype.Client.IsRunning:
                break
            if counter==0:
                self.skype.Client.Start()
                counter = 1
                time.sleep(4)

        while True:
            if self.skype.AttachmentStatus == 0:
                break
            try:
                # don't know if its our authorization request but we will wait our turn
                self.skype.Attach(Wait=True)
                time.sleep(4)
            except Exception:
                print Exception

    def changeSkypeStatus(self, status):
        self.change_status = True
        t1 = threading.Thread(target=self.skype.ChangeUserStatus, args=(status,))
        t1.start()

    def checkMessages(self):
        t1 = threading.Thread(target=self.check)
        t1.start()
        return True
        

    def check(self):
        if not self.control2:
            return None
        if self.skype.MissedMessages.Count != 0:
            for msg in self.skype.MissedMessages:
                if msg not in self.missed:
                    self.missed.append(msg) 
        else:
            self.missed = []
        self.control2 = False
        self.control = True

    def checkSkype(self):
	#print self.change_status
        if not self.skype.Client.IsRunning:
            print 'closing everything'
            sys.exit(0)
        elif not self.change_status:
            stat = self.skype.CurrentUserStatus
	    #print stat
            self.mmapp.set_status(status_conv[stat])
            return True
        else:
            return True

    def _on_set_status(self, mmap, status):
        print 'status changed to %s' %status2_conv[status]
        self.changeSkypeStatus(status2_conv[status])
	self.change_status=False
        

    def main(self):
        GLib.timeout_add(500, self.checkSkype)
        GLib.timeout_add(500, self.set_indicator)
        GLib.MainLoop().run()
        return 0

if __name__ == "__main__":  
    lock = get_lock('skype-wrapper')
    if lock:
        s = SkypeIndicator()
        s.main()
    else:
        subprocess.Popen(['/usr/bin/skype'],shell=True)

    
