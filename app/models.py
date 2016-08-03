from app import db

# similarities = db.Table('sims',
#                         db.Column('from_id',db.Integer, db.ForeignKey('tracks.track_id')),
#                         db.Column('to_id',db.Integer, db.ForeignKey('tracks.track_id')),
#                         db.Column('match',db.Float)
#                         )

class TrackLink(db.Model):
    __tablename__ = 'tracklinks'
    id = db.Column(db.Integer, primary_key = True)
    from_id = db.Column(db.Integer, db.ForeignKey('tracks.track_id'))
    to_id = db.Column(db.Integer, db.ForeignKey('tracks.track_id'))
    match = db.Column(db.Float)


class Track(db.Model):
    __tablename__ = 'tracks'
    track_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100),index = True)
    playcount = db.Column(db.Integer)
    mbid = db.Column(db.String(100),index = True)
    url = db.Column(db.String(100),unique=True)
    duration = db.Column(db.Integer)
    image = db.Column(db.String(100))
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.artist_id'))
    like = db.Column(db.Integer)

    sims = db.relationship('TrackLink',
                           backref = 'from',
                           primaryjoin = track_id == TrackLink.from_id )

    back_sims = db.relationship('TrackLink',
                                backref = 'to',
                                primaryjoin = track_id == TrackLink.to_id )

    # sims = db.relationship('Track', secondary=similarities,
    #                        primaryjoin=(similarities.c.from_id == track_id),
    #                        secondaryjoin=(similarities.c.to_id == track_id),
    #                        backref=db.backref('back_sim', lazy='dynamic'),
    #                        lazy='dynamic')
    
    def __repr__(self):
        return "<Track %r>"%self.name


class Artist(db.Model):
    __tablename__ = 'artists'
    artist_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), index = True)
    mbid = db.Column(db.String(100),index = True)
    url = db.Column(db.String(100),unique=True)
    tracks = db.relationship('Track', backref='artist', lazy='dynamic')
    
    def __repr__(self):
        return "<Artist %r>"%(self.name)
