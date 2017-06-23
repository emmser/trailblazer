# -*- coding: utf-8 -*-
import datetime

import alchy
import sqlalchemy as sqa

from . import models

TEMP_STATUSES = ('pending', 'running')


class BaseHandler:

    User = models.User
    Analysis = models.Analysis
    Job = models.Job
    Info = models.Info

    def setup(self):
        self.create_all()
        # add inital metadata record (for web interface)
        new_info = self.Info()
        self.add_commit(new_info)

    def find_analysis(self, family, started_at, status, progress):
        """Find a single analysis."""
        query = self.Analysis.query.filter_by(
            family=family,
            started_at=started_at,
            status=status,
            progress=progress,
        )
        return query.first()

    def analyses(self, *, family=None, query=None, status=None, deleted=None, temp=False):
        """Fetch analyses form the database."""
        analysis_query = self.Analysis.query.order_by(self.Analysis.started_at.desc())
        if family:
            analysis_query = analysis_query.filter_by(family=family)
        elif query:
            analysis_query = analysis_query.filter(sqa.or_(
                self.Analysis.family.like(f"%{query}%"),
                self.Analysis.status.like(f"%{query}%"),
            ))
        if status:
            analysis_query = analysis_query.filter_by(status=status)
        if isinstance(deleted, bool):
            analysis_query = analysis_query.filter_by(is_deleted=deleted)
        if temp:
            analysis_query = analysis_query.filter(self.Analysis.status.in_(TEMP_STATUSES))
        return analysis_query

    def analysis(self, analysis_id: int) -> models.Analysis:
        """Get a single analysis."""
        return self.Analysis.query.get(analysis_id)

    def track_update(self):
        """Update metadata record with new updated date."""
        metadata = self.info()
        metadata.updated_at = datetime.datetime.now()
        self.commit()

    def is_running(self, family: str) -> bool:
        """Check if an analysis is currently running/pending for a family."""
        latest_analysis = self.analyses(family=family).first()
        return latest_analysis and latest_analysis.status in TEMP_STATUSES

    def info(self) -> models.Info:
        """Return metadata entry."""
        return self.Info.query.first()

    def add_pending(self, family: str, email: str=None) -> models.Analysis:
        """Add pending entry for an analysis."""
        started_at = datetime.datetime.now()
        new_log = self.Analysis(family=family, status='pending', started_at=started_at)
        new_log.user = self.user(email) if email else None
        self.add_commit(new_log)
        return new_log

    def add_user(self, name: str, email: str) -> models.User:
        """Add a new user to the database."""
        new_user = self.User(name=name, email=email)
        self.add_commit(new_user)
        return new_user

    def user(self, email: str) -> models.User:
        """Fetch a user from the database."""
        return self.User.query.filter_by(email=email).first()


class Store(alchy.Manager, BaseHandler):

    def __init__(self, uri):
        super(Store, self).__init__(config=dict(SQLALCHEMY_DATABASE_URI=uri), Model=models.Model)
