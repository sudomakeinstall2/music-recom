from app import db

class Track(db.Model):
    track_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100),index = True)
    playcount = db.Column(db.Integer)
    mbid = db.Column(db.String(100),index = True)
    url = db.Column(db.String(100))
    duration = db.Column(db.Integer)
    image = db.Column(db.String(100))
    artist_id = db.Column(db.Integer, db.ForeignKey('artist.artist_id'))
    
    def __repr__(self):
        return "<Track %r>"%(self.name)
    
class Artist(db.Model):
    artist_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), index = True)
    mbid = db.Column(db.String(100),index = True)
    url = db.Column(db.String(100))
    tracks = db.relationship('Track', backref='artist', lazy='dynamic')
    
    def __repr__(self):
        return "<Artist %r>"%(self.name)
