from app import app, models, db, lm, forms
from flask import render_template, request, redirect, g, flash, session, url_for
from flask_login import current_user, login_user, login_required, logout_user
import urllib2

from bs4 import BeautifulSoup


@app.route('/')
@login_required
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


@app.before_request
def before_request():
    g.user = current_user

@lm.user_loader
def load_user(id):
    return models.User.query.get(int(id))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated:
        # already logged in
        return redirect('/')
    form = forms.LoginForm()
    if form.validate_on_submit():
        session['remember_me'] = form.remember_me.data
        session['remember_me'] = False
        # successful login
        user = models.User.query.filter_by(email=form.email.data).first()
        if user is None:
            email = form.email.data
            user = models.User(nickname=email.split('@')[0],email = email)
            db.session.add(user)
            db.session.commit()
        remember = False
        if 'remember_me' in session:
            remember = session['remember_me']
            session.pop('remember_me',None)
        login_user(user, remember = remember)
        return redirect('/')
    return render_template('login.html',
                           form=form)


@app.route('/status')
@login_required
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
        sims = [models.Track.query.get(link.from_id).name for link in sorted(t.back_sims,key=lambda x: x.match, reverse = True)]
        tracks[i][1].append(sims)
    #for track in tracks:
    #    app.logger.warning(repr(track[1]))
    return render_template('status.html',tracks=tracks)


@app.route('/updateSong', methods=['GET', 'POST'])
@login_required
def updateSong():
    if request.form['action'] == 'like':
        return likeSong(request.form["artist"], request.form["track"])
    elif request.form['action'] == 'ignore':
        track = models.Track.query.get(int(request.form["track_id"]))
        track.like = -1
        db.session.commit()
        return redirect('/status')

def likeSong(_artist, _track):
    ### get track info
    request_url = LAST_TRACK_INFO%(_artist,_track)
    request_url = request_url.replace(" ","%20")
    app.logger.warning(request_url)
    html = urllib2.urlopen(request_url).read()
    soup = BeautifulSoup(html, "lxml")
    soup = soup.lfm.track

    url = soup.find('url', recursive=False).text

    tr = add_or_create_track(soup)
    tr.like = 1
    db.session.commit()

    ### get similars
    request_url = LAST_SIM_API%(_artist,_track)
    request_url = request_url.replace(" ","%20")
    html = urllib2.urlopen(request_url).read()
    #app.logger.warning(html)
    soup = BeautifulSoup(html, "lxml")
    tracks = []
    for x in soup.find_all('track'):
        t = add_or_create_track(x)
        if models.TrackLink.query.filter_by(from_id=tr.track_id,to_id=t.track_id).first():
            continue

        edge = models.TrackLink()
        edge.from_id = tr.track_id
        edge.to_id = t.track_id
        edge.match = x.match.text
        tr.sims.append(edge)
        t.back_sims.append(edge)

        db.session.commit()
        tracks.append(t)
        #app.logger.warning(repr( (track_name, playcount, mbid, match, url, duration, image, artist_name, artist_mbid, artist_url) ))

    return redirect('/status')