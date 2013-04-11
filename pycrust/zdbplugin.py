# -*- coding: utf-8 -*-

"""ZDB plugin for Cherrypy

At the moment this ONLY supports ZEO.ClientStorage - but you
most likely should be using that anyway.

Set it up thusly:


    # optional on-bind routine to insure
    # tables are set up how you need them
    from BTrees.OOBTree import OOBTree
    def on_database_bind(db):
        for key in ('devices', 'sensors', 'users', 'zones'):
            if not db.has_key(key):
                db[key] = OOBTree()

    # setup database connection
    from pycrust.zdbplugin import ZDBPlugin, ZDBTool
    ZDBPlugin(cherrypy.engine, '/tmp/zeosocket', onbind=on_database_bind).subscribe()
    cherrypy.tools.db = ZDBTool()

    ...

    cherrypy.engine.start()
    cherrypy.engine.block()


In your config file, do:

    tools.db.on = True


Then in your handler objects you can do:

    from myproject.model.users import User

    users = cherrypy.request.db[users].values()

"""

__author__ = 'Michael Stella <pycrust@thismetalsky.org>'

import transaction
import cherrypy

from cherrypy.process import wspbus, plugins
import ZEO.ClientStorage
from ZODB.DB import DB

__all__ = ['ZDBPlugin', 'ZDBTool']

class ZDBPlugin(plugins.SimplePlugin):

    def __init__(self, bus, dbsocket, onbind=None):
        plugins.SimplePlugin.__init__(self, bus)
        self.zdb = self.connection = self.storage = None
        self.dbsocket = dbsocket
        self.onbind = onbind


    def start(self):
        self.bus.log('Starting ZDB connection')
        self.storage = ZEO.ClientStorage.ClientStorage(addr=self.dbsocket)
        self.zdb = DB(self.storage)
        self.connection = self.zdb.open()

        self.bus.subscribe('bind-session', self.bind)
        self.bus.subscribe('commit-session', self.commit)
        self.bus.log('ZDB connected')


    def stop(self):
        self.bus.log('Stopping ZDB connection')

        self.bus.unsubscribe('bind-session', self.bind)
        self.bus.unsubscribe('commit-session', self.commit)

        try:
            if self.connection:
                self.connection.close()
            if self.zdb:
                self.zdb.close()
            if self.storage:
                self.storage.close()
        except: pass

        self.zdb = self.connection = self.storage = None


    def bind(self):
        db = self.connection.root()

        if self.onbind:
            self.onbind(db)

        return db


    def commit(self):
        transaction.commit()


class ZDBTool(cherrypy.Tool):
    """
        The tool is responsible for associating a ZODB session
        to the database engine and attaching it to the current request.
    """

    def __init__(self):
        cherrypy.Tool.__init__(self, 'on_start_resource', self.bind_session, priority=20)

    def _setup(self):
        cherrypy.Tool._setup(self)
        cherrypy.request.hooks.attach('on_end_resource', self.commit_transaction, priority=80)

    def bind_session(self):
        session = cherrypy.engine.publish('bind-session').pop()
        cherrypy.request.db = session

    def commit_transaction(self):
        if not hasattr(cherrypy.request, 'db'):
            return
        cherrypy.request.db = None
        cherrypy.engine.publish('commit-session')


