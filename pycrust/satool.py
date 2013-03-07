# -*- coding: utf-8 -*-
"""
SATool is a CherryPy tool for talking to databases via SQLAlchemy.

Set it up thusly:

    # setup database connection
    from pycrust.saplugin import SAEnginePlugin
    SAEnginePlugin(cherrypy.engine, "sqlite:///database.db").subscribe()
    from pycrust.satool import SATool
    cherrypy.tools.db = SATool()

    ...

    cherrypy.engine.start()
    cherrypy.engine.block()


In your config file, do:

    tools.db.on = True


Then in your handler objects you can do:

    from myproject.model.users import User

    users = cherrypy.request.db.query(User).all()

"""
#
# This file is based on Sylvain Hellegouarch's post:
# http://www.defuze.org/archives/222-integrating-sqlalchemy-into-a-cherrypy-application.html
#
# All credit goes to Sylvain for this.
#
import cherrypy

__all__ = ['SATool']

class SATool(cherrypy.Tool):
    def __init__(self):
        """
        The SA tool is responsible for associating a SA session
        to the SA engine and attaching it to the current request.
        Since we are running in a multithreaded application,
        we use the scoped_session that will create a session
        on a per thread basis so that you don't worry about
        concurrency on the session object itself.

        This tools binds a session to the engine each time
        a requests starts and commits/rollbacks whenever
        the request terminates.
        """
        cherrypy.Tool.__init__(self, 'on_start_resource',
                               self.bind_session,
                               priority=20)

    def _setup(self):
        cherrypy.Tool._setup(self)
        cherrypy.request.hooks.attach('on_end_resource',
                                      self.commit_transaction,
                                      priority=80)

    def bind_session(self):
        """
        Attaches a session to the request's scope by requesting
        the SA plugin to bind a session to the SA engine.
        """
        session = cherrypy.engine.publish('bind-session').pop()
        cherrypy.request.db = session

    def commit_transaction(self):
        """
        Commits the current transaction or rolls back
        if an error occurs. Removes the session handle
        from the request's scope.
        """
        if not hasattr(cherrypy.request, 'db'):
            return
        cherrypy.request.db = None
        cherrypy.engine.publish('commit-session')

