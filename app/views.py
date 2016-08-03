from app import app, models, db
from flask import render_template, request
import urllib2

from bs4 import BeautifulSoup

@app.route('/')
def index():
    return render_template("addmusic.html")

LAST_SIM_API = "http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist=%s&track=%s&user=sudomakeinstall&api_key=dff0458affbfe429e7a4113afd6cc257&autocorrect=1"
LAST_TRACK_INFO = "http://ws.audioscrobbler.com/2.0/?method=track.getinfo&artist=%s&track=%s&user=sudomakeinstall&api_key=dff0458affbfe429e7a4113afd6cc257&autocorrect=1"


def add_or_create_artist( name, url, mbid ):
    artist = models.Artist.query.filter_by(url=url).first()
    if artist:
        pass
    else:
        artist = models.Artist()
        artist.mbid = mbid
        artist.name = name
        artist.url = url
        db.session.add(artist)
        db.session.commit()
    return artist

@app.route('/show', methods=['GET', 'POST'])
def show():
    ### get track info
    html = urllib2.urlopen(LAST_TRACK_INFO%(request.form["artist"],request.form["track"])).read()
    soup = BeautifulSoup(html, "lxml")
    soup = soup.lfm.track

    url = soup.find('url', recursive=False).text

    tr = models.Track.query.filter_by(url=url).first()
    if tr:
        tr.like = 1
    else:
        #app.logger.warning("adding new track")
        tr = models.Track()
        tr.url = url
        tr.name = soup.find('name', recursive=False).text

        try:
            tr.mbid = soup.find('mbid', recursive=False).text
        except:
            tr.mbid = ""
            app.logger.warning( tr.name + " doesn't have mbid" )

        try:
            tr.duration = soup.find('duration', recursive=False).text
        except:
            tr.duration = ""
            app.logger.warning(tr.name + " doesn't have duration")

        tr.playcount = soup.find('playcount', recursive=False).text
        tr.image = soup.find(size="large").text

        artist_name = soup.artist.find('name', recursive=False).text
        artist_mbid = soup.artist.find('mbid', recursive=False).text
        artist_url = soup.artist.find('url', recursive=False).text

        artist = add_or_create_artist(artist_name, artist_url, artist_mbid)
        tr.artist = artist
        tr.like = 1
        db.session.add(tr)
    db.session.commit()



    ### get similars
    html = urllib2.urlopen(LAST_SIM_API%(request.form["artist"],request.form["track"])).read()
    #app.logger.warning(html)
    soup = BeautifulSoup(html, "lxml")
    tracks = []
    for x in soup.find_all('track'):
        track_name = x.find('name').text
        playcount = x.playcount.text

        try:
            mbid = x.find('mbid', recursive=False).text
        except AttributeError:
            mbid = ""
            app.logger.warning( track_name + " doesn't have mbid" )

        match = x.match.text

        try:
            url = x.find('url', recursive=False).text
        except AttributeError:
            url = ""
            app.logger.warning( track_name + " doesnt have url" )

        try:
            duration = x.duration.text
        except AttributeError:
            app.logger.warning(track_name+" does not have duration")
            duration = 0

        image = x.find(size="large").text
        artist_name = x.artist.find('name').text
        artist_mbid = x.artist.mbid.text
        artist_url = x.artist.url.text

        t = models.Track()
        t.name = track_name
        t.playcount = playcount
        t.mbid = mbid
        t.url = url
        t.duration = duration
        t.image = image

        artist = add_or_create_artist(artist_name,artist_url,artist_mbid)

        t.artist = artist

        db.session.add(t)
        db.session.commit()

        tracks.append(t)
        #app.logger.warning(repr( (track_name, playcount, mbid, match, url, duration, image, artist_name, artist_mbid, artist_url) ))


    return render_template("track.html", name=tr.name,
                           artist=tr.artist.name,
                           tracks = tracks)