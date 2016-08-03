from app import app, models, db
from flask import render_template, request, redirect
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


def add_or_create_track(soup):
    url = soup.find('url', recursive=False).text
    tr = models.Track.query.filter_by(url=url).first()
    if tr:
        return tr
    else:
        # app.logger.warning("adding new track")
        tr = models.Track()
        tr.url = url
        tr.name = soup.find('name', recursive=False).text

        try:
            tr.mbid = soup.find('mbid', recursive=False).text
        except:
            tr.mbid = ""
            app.logger.warning(tr.name + " doesn't have mbid")

        try:
            tr.duration = soup.find('duration', recursive=False).text
        except:
            tr.duration = ""
            app.logger.warning(tr.name + " doesn't have duration")

        tr.playcount = soup.find('playcount', recursive=False).text

        try:
            tr.image = soup.find(size="large").text
        except:
            tr.image = ""
            app.logger.warning(tr.name + " doesn't have image")

        artist_name = soup.artist.find('name', recursive=False).text
        artist_mbid = soup.artist.find('mbid', recursive=False).text
        artist_url = soup.artist.find('url', recursive=False).text

        artist = add_or_create_artist(artist_name, artist_url, artist_mbid)
        tr.artist = artist
        db.session.add(tr)
        db.session.commit()
        return tr


@app.route('/status')
def status():
    tracks = []
    dic = {}
    links = models.TrackLink.query.all()
    for link in links:
        if link.to_id in dic:
            dic[link.to_id][1] = dic[link.to_id][1] + link.match
        else:
            t = models.Track.query.get(link.to_id)
            if t.like == 1 or t.like == -1:
                continue
            dic[link.to_id] = [t, link.match]
    tracks = list(dic.items())
    tracks.sort(key=lambda x:x[1][1], reverse=True)
    for i,x in enumerate(tracks):
        t = x[1][0]
        sims = [models.Track.query.get(link.from_id).name for link in t.back_sims]
        tracks[i][1].append(sims)
    #for track in tracks:
    #    app.logger.warning(repr(track[1]))
    return render_template('status.html',tracks=tracks)


@app.route('/likeSong', methods=['GET', 'POST'])
def likeSong():
    ### get track info
    request_url = LAST_TRACK_INFO%(request.form["artist"],request.form["track"])
    request_url = request_url.replace(" ","%20")
    app.logger.warning(request_url)
    html = urllib2.urlopen(request_url).read()
    soup = BeautifulSoup(html, "lxml")
    soup = soup.lfm.track

    url = soup.find('url', recursive=False).text

    tr = add_or_create_track(soup)
    tr.like = 1
    db.session.add(tr)
    db.session.commit()

    ### get similars
    request_url = LAST_SIM_API%(request.form["artist"],request.form["track"])
    request_url = request_url.replace(" ","%20")
    html = urllib2.urlopen(request_url).read()
    #app.logger.warning(html)
    soup = BeautifulSoup(html, "lxml")
    tracks = []
    for x in soup.find_all('track'):
        t = add_or_create_track(x)

        edge = models.TrackLink()
        edge.from_id = tr.track_id
        edge.to_id = t.track_id
        edge.match = x.match.text
        tr.sims.append(edge)
        t.back_sims.append(edge)

        db.session.add(t)
        db.session.add(tr)
        db.session.commit()

        tracks.append(t)
        #app.logger.warning(repr( (track_name, playcount, mbid, match, url, duration, image, artist_name, artist_mbid, artist_url) ))

    return redirect('/status')